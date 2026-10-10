import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '../../prototype/node_modules/@playwright/test/index.mjs';

// Read-only against the existing CMS examples. Use a real headed browser and
// viewport:null: an emulated/headless viewport cannot validate resizeTo.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const output = path.resolve(root, process.env.Y3GYM_POPUP_REVIEW_DIR || 'review/popup-sizing');
const origin = 'http://localhost:8768';
await fs.mkdir(output, { recursive: true });
const report = { run: new Date().toISOString(), status: 'RUNNING', headed: true,
  checks: [], errors: [], screenshots: [], windows: [] };
const browser = await chromium.launch({ headless: false, args: ['--window-size=1440,900'] });
const check = (name, detail) => {
  report.checks.push({ name, detail, result: 'PASS' });
  console.log(`PASS ${name}`);
};
const watch = context => context.on('page', page => {
  page.on('pageerror', error => report.errors.push({ url: page.url(), error: error.message }));
});
async function capture(page, name) {
  await page.screenshot({ path: path.join(output, name) });
  report.screenshots.push(name);
}
async function metrics(page) {
  const session = await page.context().newCDPSession(page);
  const { targetInfo } = await session.send('Target.getTargetInfo');
  const native = await session.send('Browser.getWindowForTarget', { targetId: targetInfo.targetId });
  await session.detach();
  const dom = await page.evaluate(() => ({
    inner: { width: innerWidth, height: innerHeight },
    outer: { width: outerWidth, height: outerHeight },
    available: { width: screen.availWidth, height: screen.availHeight },
    frame: document.querySelector('.popup-document').getBoundingClientRect().toJSON(),
    controls: document.querySelector('.popup-controls').getBoundingClientRect().toJSON(),
    overflowX: document.documentElement.scrollWidth > innerWidth,
    scrollHeight: document.documentElement.scrollHeight,
  }));
  return { url: page.url(), native, ...dom };
}
async function fitted(page, { width = 480, capped = false } = {}) {
  await page.waitForFunction(async ({ width, capped }) => {
    const { popupWorkArea } = await import('/static/news/popup-sizing.js');
    // The opener's monitor is also used when a new native window initially
    // reports the default monitor. These tests only override screen dimensions.
    const area = popupWorkArea();
    const frame = document.querySelector('.popup-document');
    if (!frame || document.fonts.status !== 'loaded' ||
      [...document.images].some(image => !image.complete)) return false;
    const height = Math.min(Math.ceil(frame.getBoundingClientRect().height),
      area.height - area.marginY * 2 - Math.max(0, outerHeight - innerHeight));
    return Math.abs(innerWidth - width) <= 1 && Math.abs(innerHeight - height) <= 1 &&
      (!capped || outerHeight <= area.height - area.marginY * 2 + 1);
  }, { width, capped }, { polling: 120, timeout: 12000 });
  const result = await metrics(page);
  assert(!result.overflowX, JSON.stringify(result));
  assert(Math.abs(result.native.bounds.width - result.outer.width) <= 1);
  assert(Math.abs(result.native.bounds.height - result.outer.height) <= 1);
  if (!capped) {
    assert(result.controls.bottom <= result.inner.height);
    assert(Math.abs(result.inner.height - result.frame.height) <= 1);
    assert(result.inner.height - result.controls.bottom <= 14);
  }
  report.windows.push(result);
  return result;
}
async function batch(context, url = `${origin}/?branch=second`) {
  watch(context);
  await context.addInitScript(() => {
    window.reviewSizingOpens = [];
    const original = window.open.bind(window);
    window.open = (...args) => { window.reviewSizingOpens.push(args[0]); return original(...args); };
  });
  const home = await context.newPage();
  const popups = [];
  home.on('popup', page => popups.push(page));
  await home.goto(url);
  const payload = JSON.parse(await home.locator('#home-popup-data').textContent());
  assert(payload.length >= 2, 'At least two currently eligible CMS examples required.');
  await home.waitForFunction(ids => ids.every(id =>
    sessionStorage.getItem(`y3gym.prototype.shown:${id}`) === '1'), payload.map(item => item.id));
  for (let attempt = 0; popups.length < payload.length && attempt < 50; attempt++) await home.waitForTimeout(100);
  assert.equal(popups.length, payload.length);
  await Promise.all(popups.map(page => page.waitForLoadState()));
  const expected = payload.map(item => item.url);
  assert.deepEqual(popups.map(page => new URL(page.url()).pathname).sort(), [...expected].sort());
  // Browser popup events can arrive out of order; the policy concerns the
  // synchronous window.open calls, not asynchronous native creation events.
  assert.deepEqual((await home.evaluate(() => reviewSizingOpens))
    .map(url => new URL(url, origin).pathname), expected);
  popups.sort((a, b) => expected.indexOf(new URL(a.url()).pathname) - expected.indexOf(new URL(b.url()).pathname));
  return { home, popups, payload };
}
async function fixture(context, { image = false, long = false, broken = false } = {}) {
  await context.route(/\/popups\/\d+\/(?:\?.*)?$/, async route => {
    const response = await route.fetch();
    let html = await response.text();
    if (long) {
      html = html.replace(/(<h1 data-popup-title>)[\s\S]*?(<\/h1>)/,
        `$1${'긴 제목과 시설 이용 안내를 확인합니다. '.repeat(18).slice(0, 200)}$2`)
        .replace(/(<p data-popup-description>)[\s\S]*?(<\/p>)/,
          `$1${'검수용 긴 설명입니다. 실제 영업 정보가 아닙니다. '.repeat(45).slice(0, 300)}$2`);
    }
    if (image) html = html.replace('<p data-popup-description>',
      '<div class="popup-image-frame" data-popup-image-frame><img src="/static/prototype/assets/images/gym-strength.png" alt="검수용 시설 사진" data-popup-image><span data-popup-image-fallback hidden>사진을 불러오지 못했습니다.</span></div><p data-popup-description>');
    await route.fulfill({ response, body: html });
  });
  await context.route('**/gym-strength.png', async route => {
    if (broken) await route.abort();
    else { await new Promise(resolve => setTimeout(resolve, 650)); await route.continue(); }
  });
}

try {
  // Check every unfocused window before bringing any forward for screenshots.
  for (const run of [1, 2]) {
    const context = await browser.newContext({ viewport: null });
    const { home, popups } = await batch(context,
      run === 1 ? `${origin}/?branch=second` : 'http://localhost:8767/?branch=second');
    const sizes = await Promise.all(popups.map(page => fitted(page)));
    assert(sizes.every(size => size.inner.width === 480));
    if (run === 1) for (let i = 0; i < popups.length; i++) await capture(popups[i], `popup-${i + 1}.png`);
    await home.reload();
    await home.waitForTimeout(400);
    assert.equal(context.pages().length, popups.length + 1);
    assert.equal(await home.locator('[data-popup-recovery] a:visible').count(), 0);
    if (run === 1) {
      await popups[0].locator('[data-popup-post]').click();
      await popups[0].waitForURL('**/news/**');
      assert.equal(new URL(popups[0].url()).searchParams.get('branch'), 'second');
      await popups[1].locator('[data-hide-today]').check();
      const id = await popups[1].locator('#popup-data').textContent().then(JSON.parse).then(data => data.id);
      await popups[1].locator('[data-close-popup]').click();
      await home.waitForFunction(id => Number(localStorage.getItem(`y3gym.prototype.hide:${id}`)) > Date.now(), id);
    }
    check(`실제 별도 창 전체 폭·내용 높이·하단 여백·중복 방지 ${run}회`, sizes.map(size => size.native.bounds));
    await context.close();
  }

  const delayed = await browser.newContext({ viewport: null });
  await fixture(delayed, { image: true });
  await delayed.route('**/*.woff2', async route => {
    await new Promise(resolve => setTimeout(resolve, 450)); await route.continue();
  });
  const withImages = await batch(delayed);
  await Promise.all(withImages.popups.map(page => fitted(page)));
  const imageSize = await withImages.popups[0].locator('[data-popup-image-frame]').boundingBox();
  assert(Math.abs(imageSize.width / imageSize.height - 1.6) < 0.01);
  await capture(withImages.popups[0], 'popup-image-delayed.png');
  check('글꼴·사진 지연 로딩 뒤 모든 창 재측정·16:10 사진', imageSize);
  await delayed.close();

  const broken = await browser.newContext({ viewport: null });
  await fixture(broken, { image: true, broken: true });
  const failedImages = await batch(broken);
  await Promise.all(failedImages.popups.map(page => fitted(page)));
  assert(await failedImages.popups[0].locator('[data-popup-image-fallback]').isVisible());
  await capture(failedImages.popups[0], 'popup-image-fallback.png');
  check('사진 실패 대체 안내와 창 크기', failedImages.popups.length);
  await broken.close();

  const stale = await browser.newContext({ viewport: null });
  await stale.addInitScript(() => {
    if (!opener) return;
    const width = Object.getOwnPropertyDescriptor(window, 'outerWidth');
    const height = Object.getOwnPropertyDescriptor(window, 'outerHeight');
    Object.defineProperty(window, 'outerWidth', { configurable: true,
      get: () => performance.now() < 1400 ? 1920 : width.get.call(window) });
    Object.defineProperty(window, 'outerHeight', { configurable: true,
      get: () => performance.now() < 1400 ? 1080 : height.get.call(window) });
  });
  const staleBatch = await batch(stale);
  // Compare CDP bounds only after the deliberately fake outer getters expire.
  await Promise.all(staleBatch.popups.map(page => page.waitForFunction(
    () => performance.now() >= 1500, null, { polling: 100 })));
  await Promise.all(staleBatch.popups.map(page => fitted(page)));
  await staleBatch.home.waitForTimeout(4500);
  const resizePage = staleBatch.popups.at(-1);
  const session = await stale.newCDPSession(resizePage);
  const { targetInfo } = await session.send('Target.getTargetInfo');
  const { windowId } = await session.send('Browser.getWindowForTarget', { targetId: targetInfo.targetId });
  await session.send('Browser.setWindowBounds', { windowId, bounds: { width: 620, height: 650 } });
  await resizePage.waitForTimeout(500);
  assert.equal((await metrics(resizePage)).native.bounds.width, 620);
  check('처음 1.4초 잘못된 outer 크기 복구·자동 조절 종료 후 사용자 크기 변경 유지', staleBatch.popups.length);
  await stale.close();

  const small = await browser.newContext({ viewport: null });
  await small.addInitScript(() => {
    Object.defineProperty(screen, 'availWidth', { get: () => 440 });
    Object.defineProperty(screen, 'availHeight', { get: () => 600 });
  });
  await fixture(small, { image: true, long: true });
  const longBatch = await batch(small);
  await Promise.all(longBatch.popups.map(page => fitted(page, { width: 344, capped: true })));
  const longPage = longBatch.popups[0];
  await capture(longPage, 'popup-long-first.png');
  await longPage.locator('[data-close-popup]').scrollIntoViewIfNeeded();
  const closeBounds = await longPage.locator('[data-close-popup]').boundingBox();
  assert(closeBounds.y >= 0 && closeBounds.y + closeBounds.height <= await longPage.evaluate(() => innerHeight));
  await capture(longPage, 'popup-long-bottom.png');
  check('긴 제목·본문·사진 및 440×600 작업 영역: 48px 가장자리 여백·창 크기 제한·가로 넘침 없음·닫기까지 스크롤', closeBounds);
  await small.close();

  const restricted = await browser.newContext({ viewport: null });
  await restricted.addInitScript(() => {
    window.reviewResizeCalls = 0;
    window.resizeTo = () => { window.reviewResizeCalls++; };
  });
  const denied = await batch(restricted);
  await denied.home.waitForTimeout(5000);
  for (const page of denied.popups) {
    const size = await metrics(page);
    assert(size.frame.height < 450 && size.controls.bottom < 440);
    assert(!size.overflowX);
    const calls = await page.evaluate(() => reviewResizeCalls);
    assert(calls > 0 && calls <= 12);
  }
  await capture(denied.popups[0], 'popup-resize-restricted.png');
  check('크기 변경 제한/새 탭 대체: 본문·닫기 밀착·무한 조절 없음', denied.popups.length);
  await restricted.close();

  const blocked = await browser.newContext({ viewport: null });
  await blocked.addInitScript(() => {
    const original = window.open.bind(window);
    window.open = (...args) => navigator.userActivation.isActive ? original(...args) : null;
  });
  watch(blocked);
  const recovery = await blocked.newPage();
  await recovery.goto(`${origin}/?branch=second`);
  await recovery.locator('[data-popup-recovery] a').first().waitFor();
  const [manual] = await Promise.all([recovery.waitForEvent('popup'),
    recovery.locator('[data-popup-recovery] a').first().click()]);
  const manualId = JSON.parse(await manual.locator('#popup-data').textContent()).id;
  await recovery.waitForFunction(id => sessionStorage.getItem(`y3gym.prototype.shown:${id}`) === '1', manualId);
  await fitted(manual);
  await capture(manual, 'popup-manual.png');
  check('자동 차단 후 실제 수동 창도 같은 폭·내용 높이', manual.url());
  await blocked.close();

  for (const height of [812, 568]) {
    const context = await browser.newContext({ viewport: { width: 375, height } });
    watch(context);
    const page = await context.newPage();
    let windows = 0;
    page.on('popup', () => windows++);
    await page.goto(`${origin}/?branch=second`);
    const payload = JSON.parse(await page.locator('#home-popup-data').textContent());
    for (let i = 0; i < payload.length; i++) {
      await page.locator('dialog[open] #mobile-popup-title').filter({ hasText: payload[i].title }).waitFor();
      const close = await page.locator('[data-mobile-close-popup]').boundingBox();
      assert(close.y >= 0 && close.y + close.height <= height);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      if (!i) await capture(page, `popup-mobile-${height}.png`);
      await page.locator('[data-mobile-close-popup]').click();
    }
    assert.equal(windows, 0);
    // close() removes [open] synchronously, but its close event restores the
    // page and removes the dialog later. Wait for that actual completion.
    await page.locator('dialog.mobile-popup').waitFor({ state: 'detached' });
    await page.locator('.mobile-contact-bar').waitFor({ state: 'visible' });
    check(`375×${height} 모바일 순차 레이어·닫기·하단 문의 바 복원`, payload.length);
    await context.close();
  }
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
