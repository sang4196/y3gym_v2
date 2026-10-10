import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '../../prototype/node_modules/@playwright/test/index.mjs';

// Read existing public examples only. Native geometry requires a headed
// Chromium with viewport:null; CDP bounds are checked against screenX/Y.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const output = path.resolve(root, process.env.Y3GYM_POPUP_REVIEW_DIR || 'review/popup-position');
const origin = 'http://localhost:8768';
await fs.mkdir(output, { recursive: true });
const report = { run: new Date().toISOString(), status: 'RUNNING', headed: true,
  checks: [], errors: [], batches: [], screenshots: [] };
const browser = await chromium.launch({ headless: false, args: ['--window-size=1440,900'] });
const check = (name, detail) => {
  report.checks.push({ name, detail, result: 'PASS' });
  console.log(`PASS ${name}`);
};
async function context() {
  const context = await browser.newContext({ viewport: null });
  context.on('page', page => page.on('pageerror', error => report.errors.push(error.message)));
  await context.addInitScript(() => {
    window.reviewOpens = [];
    window.reviewReady = [];
    const original = window.open.bind(window);
    window.open = (...args) => {
      window.reviewOpens.push({ url: args[0], features: args[2] });
      return original(...args);
    };
    window.addEventListener('message', event => {
      if (event.origin === location.origin && event.data?.type === 'y3gym-popup-ready') window.reviewReady.push(event.data.id);
      if (event.origin === location.origin && event.source === opener &&
          event.data?.type === 'y3gym-popup-placement') window.reviewPlacement = event.data.placement;
    });
  });
  return context;
}
async function batch(context) {
  const home = await context.newPage();
  const popups = [];
  home.on('popup', page => popups.push(page));
  await home.goto(`${origin}/?branch=second`);
  const payload = JSON.parse(await home.locator('#home-popup-data').textContent());
  assert(payload.length >= 2, 'At least two eligible public CMS examples are required.');
  await home.waitForFunction(ids => ids.every(id =>
    reviewReady.includes(id)), payload.map(item => item.id));
  for (let i = 0; i < 40 && popups.length < payload.length; i++) await home.waitForTimeout(100);
  assert.equal(popups.length, payload.length);
  const expected = payload.map(item => item.url);
  assert.deepEqual(popups.map(page => new URL(page.url()).pathname).sort(), [...expected].sort());
  assert.deepEqual((await home.evaluate(() => reviewOpens)).map(item => new URL(item.url).pathname), expected);
  popups.sort((a, b) => expected.indexOf(new URL(a.url()).pathname) - expected.indexOf(new URL(b.url()).pathname));
  return { home, popups, payload };
}
async function bounds(page) {
  const session = await page.context().newCDPSession(page);
  const { targetInfo } = await session.send('Target.getTargetInfo');
  const { bounds } = await session.send('Browser.getWindowForTarget', { targetId: targetInfo.targetId });
  await session.detach();
  return bounds;
}
async function measure(page, { positioned = true, capped = false } = {}) {
  await page.waitForFunction(async ({ positioned, capped }) => {
    const { popupPosition, popupWorkArea } = await import('/static/news/popup-sizing.js');
    if (!window.reviewPlacement || document.fonts.status !== 'loaded' ||
        [...document.images].some(image => !image.complete)) return false;
    const area = popupWorkArea();
    const frame = document.querySelector('.popup-document').getBoundingClientRect();
    const chromeWidth = outerWidth - innerWidth, chromeHeight = outerHeight - innerHeight;
    const width = Math.min(480, area.width - area.marginX * 2 - chromeWidth);
    const height = Math.min(Math.ceil(frame.height), area.height - area.marginY * 2 - chromeHeight);
    const target = popupPosition(reviewPlacement, outerWidth, outerHeight);
    return Math.abs(innerWidth - width) <= 1 && Math.abs(innerHeight - height) <= 1 &&
      (!positioned || (Math.abs(screenX - target.left) <= 1 && Math.abs(screenY - target.top) <= 1)) &&
      (!capped || outerHeight <= area.height - area.marginY * 2 + 1);
  }, { positioned, capped }, { polling: 120, timeout: 12000 });
  // Native resize/move acknowledgements can trail the JS geometry by a frame.
  // Let the sizer's second stable sample finish before comparing CDP bounds.
  await page.waitForTimeout(300);
  const dom = await page.evaluate(async () => {
    const { popupWorkArea, popupPosition } = await import('/static/news/popup-sizing.js');
    return { area: popupWorkArea(), initialArea: popupWorkArea(reviewPlacement.display), anchor: reviewPlacement,
      target: popupPosition(reviewPlacement, outerWidth, outerHeight),
      outer: { left: screenX, top: screenY, width: outerWidth, height: outerHeight },
      inner: { width: innerWidth, height: innerHeight },
      overflowX: document.documentElement.scrollWidth > innerWidth,
      controls: document.querySelector('.popup-controls').getBoundingClientRect().toJSON() };
  });
  const native = await bounds(page);
  for (const key of ['left', 'top', 'width', 'height']) assert(Math.abs(native[key] - dom.outer[key]) <= 1,
    JSON.stringify({ key, native, dom }));
  const { area } = dom;
  if (positioned) {
    assert(native.left >= area.left + area.marginX - 1);
    assert(native.top >= area.top + area.marginY - 1);
    assert(native.left + native.width <= area.left + area.width - area.marginX + 1);
    assert(native.top + native.height <= area.top + area.height - area.marginY + 1);
    assert(Math.abs(native.left + native.width / 2 - area.left - area.width / 2) <= 181, JSON.stringify({ native, dom }));
    assert(Math.abs(native.top + native.height / 2 - area.top - area.height / 2) <= 101, JSON.stringify({ native, dom }));
  }
  assert(!dom.overflowX);
  if (!capped) assert(dom.controls.bottom <= dom.inner.height);
  return { url: page.url(), native, ...dom };
}
async function record(batch, name, options) {
  const windows = await Promise.all(batch.popups.map(page => measure(page, options)));
  const opens = await batch.home.evaluate(() => reviewOpens);
  assert.equal(new Set(opens.map(item => item.features.match(/left=([^,]+),top=([^,]+)/)?.[0])).size, opens.length);
  if (!options?.capped) assert.equal(new Set(windows.map(item => `${item.native.left},${item.native.top}`)).size, windows.length);
  // Inspect the actual initial feature values, before child sizing/moving.
  for (const item of opens) {
    const values = Object.fromEntries(item.features.split(',').map(part => part.split('=')));
    const area = windows[0].initialArea;
    assert(+values.left >= area.left + area.marginX - 1);
    assert(+values.top >= area.top + area.marginY - 1);
    assert(+values.left + +values.width + 16 <= area.left + area.width - area.marginX + 1,
      JSON.stringify({ values, area, opens }));
    assert(+values.top + +values.height + 88 <= area.top + area.height - area.marginY + 1,
      JSON.stringify({ values, area }));
  }
  report.batches.push({ name, opens, windows });
  return windows;
}
async function capture(page, name) {
  await page.screenshot({ path: path.join(output, name) });
  report.screenshots.push(name);
}
async function closePopups(batch) {
  for (const page of batch.popups) {
    const closed = page.waitForEvent('close');
    await page.locator('[data-close-popup]').click().catch(error => { if (!page.isClosed()) throw error; });
    await closed;
  }
}

try {
  const pc = await context();
  const first = await batch(pc);
  const normal = await record(first, 'real-screen-normal');
  for (let i = 0; i < first.popups.length; i++) await capture(first.popups[i], `popup-${i + 1}.png`);
  check('실제 복수 창 초기 좌표·중앙 랜덤 분산·최종 좌표·48px 가장자리 여백', normal.map(item => item.native));

  await first.home.reload();
  await first.home.waitForFunction(ids => ids.every(id => reviewReady.includes(id)), first.payload.map(item => item.id));
  await Promise.all(first.popups.map(page => measure(page)));
  assert.equal(pc.pages().length, first.popups.length + 1);
  await closePopups(first);
  first.popups.length = 0;
  await first.home.reload();
  await first.home.waitForFunction(ids => reviewOpens.length === ids.length && ids.every(id => reviewReady.includes(id)), first.payload.map(item => item.id));
  for (let i = 0; i < 40 && first.popups.length < first.payload.length; i++) await first.home.waitForTimeout(100);
  const reopened = await record(first, 'ordinary-close-and-reload');
  assert.notDeepEqual(reopened.map(item => item.native), normal.map(item => item.native));
  assert.equal(await first.home.evaluate(() => Object.keys(localStorage).filter(key => key.startsWith('y3gym.prototype.hide:')).length), 0);
  check('열린 창 재사용·일반 닫기 후 새로고침 전체 재노출·새 랜덤 위치', first.popups.length);
  await first.home.waitForTimeout(1800);
  const userMoved = first.popups[0];
  const session = await pc.newCDPSession(userMoved);
  const { targetInfo } = await session.send('Target.getTargetInfo');
  const { windowId } = await session.send('Browser.getWindowForTarget', { targetId: targetInfo.targetId });
  await session.send('Browser.setWindowBounds', { windowId, bounds: { left: 250, top: 120, width: 620, height: 650 } });
  await userMoved.waitForTimeout(300);
  const userBounds = await bounds(userMoved);
  await userMoved.waitForTimeout(600);
  assert.equal(userBounds.width, 620);
  assert.equal(userBounds.height, 650);
  assert.deepEqual(await bounds(userMoved), userBounds);
  check('초기 보정 종료 후 사용자가 이동·크기 변경한 창을 다시 끌어오지 않음', await bounds(userMoved));
  await pc.close();

  const images = await context();
  await images.route(/\/popups\/\d+\/(?:\?.*)?$/, async route => {
    const response = await route.fetch();
    const html = (await response.text()).replace('<p data-popup-description>',
      '<div class="popup-image-frame" data-popup-image-frame><img src="/static/prototype/assets/images/gym-strength.png" alt="검수용 임시 사진" data-popup-image><span data-popup-image-fallback hidden>사진을 불러오지 못했습니다.</span></div><p data-popup-description>');
    await route.fulfill({ response, body: html });
  });
  await images.route('**/gym-strength.png', async route => {
    await new Promise(resolve => setTimeout(resolve, 900)); await route.continue();
  });
  const photos = await batch(images);
  const photoBounds = await record(photos, 'delayed-photo');
  await capture(photos.popups[0], 'popup-photo.png');
  check('사진 지연 후 높이가 커져도 같은 랜덤 기준점으로 중앙·가장자리 보정', photoBounds.map(item => item.native));
  await images.close();

  const fixedRandom = await context();
  await fixedRandom.addInitScript(() => { Math.random = () => 0.5; });
  const fixed = await batch(fixedRandom);
  const separated = await record(fixed, 'fixed-random-stress');
  const nine = await fixed.home.evaluate(async () => {
    const { createPopupPlacementPlanner } = await import('/static/news/popup-sizing.js');
    const next = createPopupPlacementPlanner();
    return Array.from({ length: 9 }, () => next());
  });
  assert.equal(new Set(nine.map(item => `${item.x},${item.y}`)).size, 9);
  check('같은 난수값에서도 4개 실제 창 분산·첫 9개 중앙 구역 중복 선택 없음', { actual: separated.map(item => item.anchor), nine });
  await fixedRandom.close();

  const blocked = await context();
  await blocked.addInitScript(() => {
    const original = window.open.bind(window);
    window.open = (...args) => navigator.userActivation.isActive ? original(...args) : null;
  });
  const home = await blocked.newPage();
  await home.goto(`${origin}/?branch=second`);
  const [manual] = await Promise.all([home.waitForEvent('popup'), home.locator('[data-popup-recovery] a').first().click()]);
  await home.waitForFunction(() => reviewReady.length === 1);
  const manualBounds = await measure(manual);
  report.batches.push({ name: 'manual-after-block', windows: [manualBounds] });
  check('자동 차단 후 수동으로 연 창도 중앙 랜덤·실제 안전 좌표', manualBounds.native);
  await blocked.close();

  const restricted = await context();
  await restricted.addInitScript(() => {
    window.reviewMoves = 0;
    window.moveTo = () => { window.reviewMoves++; };
  });
  const denied = await batch(restricted);
  await Promise.all(denied.popups.map(page => measure(page, { positioned: false })));
  await denied.home.waitForTimeout(2000);
  for (const page of denied.popups) {
    const calls = await page.evaluate(() => reviewMoves);
    assert(calls > 0 && calls <= 12);
    const before = calls;
    await page.waitForTimeout(200);
    assert.equal(await page.evaluate(() => reviewMoves), before);
  }
  const restrictedOpens = await denied.home.evaluate(() => reviewOpens);
  assert(restrictedOpens.every(item => /left=-?\d+,top=-?\d+/.test(item.features)));
  check('moveTo 제한: 시작 좌표 요청·본문 크기·닫기 유지·무한 이동 없음 (실제 위치 강제 불가)', denied.popups.length);

  const math = await denied.home.evaluate(async () => {
    const { popupPosition, popupWorkArea } = await import('/static/news/popup-sizing.js');
    return [
      { availLeft: -1920, availTop: 80, availWidth: 1920, availHeight: 1000 },
      { availLeft: 1920, availTop: -900, availWidth: 1440, availHeight: 900 },
      { availLeft: 0, availTop: 0, availWidth: 440, availHeight: 600 },
    ].map(display => {
      const area = popupWorkArea(display);
      const width = Math.min(480, area.width - area.marginX * 2);
      const height = Math.min(800, area.height - area.marginY * 2);
      return { area, width, height, positions: [{ x: -1, y: -1 }, { x: 1, y: 1 }]
        .map(anchor => popupPosition(anchor, width, height, display)) };
    });
  });
  for (const { area, width, height, positions } of math) for (const position of positions) {
    assert(position.left >= area.left + area.marginX - 1);
    assert(position.top >= area.top + area.marginY - 1);
    assert(position.left + width <= area.left + area.width - area.marginX + 1);
    assert(position.top + height <= area.top + area.height - area.marginY + 1);
  }
  check('음수·다른 모니터 원점과 작은 작업 영역 좌표 계산 (합성 입력, 실제 다중 모니터 아님)', math);
  await restricted.close();
  assert.deepEqual(report.errors, []);
  report.status = 'PASS';
} catch (error) {
  report.status = 'FAIL';
  report.failure = error.stack || error.message;
  process.exitCode = 1;
} finally {
  await browser.close();
  await fs.writeFile(path.join(output, 'checks.json'), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ status: report.status, checks: report.checks.length, failure: report.failure }));
}
