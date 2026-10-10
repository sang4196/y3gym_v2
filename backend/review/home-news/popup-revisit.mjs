import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '../../../prototype/node_modules/@playwright/test/index.mjs';

// Read-only CMS review. All hide records live in isolated browser contexts.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const output = path.resolve(root, process.env.Y3GYM_HOME_NEWS_REVIEW_DIR || 'review/home-news/browser', 'popup-revisit');
const origin = process.env.Y3GYM_HOME_NEWS_ORIGIN;
assert(origin && new URL(origin).hostname === 'localhost' && !['8767', '8768'].includes(new URL(origin).port), 'Isolated test server required.');
await fs.mkdir(output, { recursive: true });
const report = { run: new Date().toISOString(), status: 'RUNNING', checks: [], errors: [] };
const browser = await chromium.launch();
const check = (name, detail) => {
  report.checks.push({ name, detail, result: 'PASS' });
  console.log(`PASS ${name}`);
};
async function context(mobile = false) {
  const context = await browser.newContext({ viewport: mobile ? { width: 375, height: 812 } : { width: 1440, height: 900 } });
  context.on('page', page => page.on('pageerror', error => report.errors.push(error.message)));
  await context.addInitScript(() => {
    window.reviewDocument = `${Date.now()}-${Math.random()}`;
    window.reviewAttempts = [];
    window.reviewReady = [];
    const original = window.open.bind(window);
    window.open = (...args) => { window.reviewAttempts.push(args[0]); return original(...args); };
    window.addEventListener('message', event => {
      if (event.origin === location.origin && event.data?.type === 'y3gym-popup-ready') window.reviewReady.push(event.data.id);
    });
    // Existing tabs can retain the previous implementation's flags. They must
    // not suppress any eligible popup under the new explicit-hide policy.
    try { sessionStorage.setItem('y3gym.prototype.cms-auto-batch', '1'); }
    catch { /* Initial opaque about:blank popup documents have no storage. */ }
  });
  return context;
}
async function payload(page) {
  const data = JSON.parse(await page.locator('#home-popup-data').textContent());
  assert(data.length >= 2, 'Two currently eligible CMS examples are required.');
  return data;
}
async function desktopReady(page, ids) {
  await page.waitForFunction(ids => window.reviewAttempts?.length === ids.length &&
    ids.every(id => window.reviewReady?.includes(id)), ids, { polling: 100 });
  const urls = await page.evaluate(() => reviewAttempts);
  const data = await payload(page);
  assert.deepEqual(urls.map(url => new URL(url, locationOrigin).pathname),
    data.filter(item => ids.includes(item.id)).map(item => item.url));
}
const locationOrigin = origin;
async function closeWindows(context, hideId = null) {
  for (const popup of context.pages().filter(page => new URL(page.url()).pathname.startsWith('/popups/'))) {
    await popup.locator('[data-close-popup]').waitFor();
    const data = JSON.parse(await popup.locator('#popup-data').textContent());
    if (data.id === hideId) await popup.locator('[data-hide-today]').check();
    const closed = popup.waitForEvent('close');
    // window.close() can destroy the target before Playwright acknowledges the
    // click. Accept that outcome only if this exact popup really closed.
    await popup.locator('[data-close-popup]').click().catch(error => {
      if (!popup.isClosed()) throw error;
    });
    await closed;
  }
}
async function mobileClose(page, data, hideId = null) {
  for (const popup of data) {
    await page.locator('dialog[open] #mobile-popup-title').filter({ hasText: popup.title }).waitFor();
    if (popup.id === hideId) await page.locator('[data-mobile-hide-today]').check();
    await page.locator('[data-mobile-close-popup]').click();
  }
  await page.locator('dialog.mobile-popup').waitFor({ state: 'detached' });
  await page.locator('.mobile-contact-bar').waitFor({ state: 'visible' });
  assert.equal(await page.evaluate(() => reviewAttempts.length), 0);
}
async function midnight(page, id) {
  const value = await page.evaluate(id => Number(localStorage.getItem(`y3gym.prototype.hide:${id}`)), id);
  const next = (Math.floor((Date.now() + 9 * 3600000) / 86400000) + 1) * 86400000 - 9 * 3600000;
  assert.equal(value, next);
  return new Date(value).toISOString();
}

try {
  const pc = await context();
  const home = await pc.newPage();
  await home.goto(`${origin}/?branch=second`);
  const data = await payload(home);
  const ids = data.map(item => item.id);
  assert.equal(await home.evaluate(() => sessionStorage.getItem('y3gym.prototype.cms-auto-batch')), '1');
  await desktopReady(home, ids);
  await closeWindows(pc);
  assert.equal(await home.evaluate(() => Object.keys(localStorage).filter(key => key.startsWith('y3gym.prototype.hide:')).length), 0);
  await home.reload();
  await desktopReady(home, ids);
  check('PC 일반 닫기 후 같은 탭 새로고침 전체 재노출·과거 탭 플래그 무시·등록 순서', ids);

  const oldWindows = pc.pages().filter(page => page !== home);
  await home.reload();
  await desktopReady(home, ids);
  assert.equal(pc.pages().length, oldWindows.length + 1);
  assert(oldWindows.every(page => pc.pages().includes(page)));
  check('열린 상태에서 새로고침: 글별 기존 창 재사용·중복 창 없음', oldWindows.length);
  await closeWindows(pc);

  await home.getByRole('link', { name: '소식', exact: true }).first().click();
  await home.waitForURL('**/news/**');
  await home.goto(`${origin}/?branch=second`);
  await desktopReady(home, ids);
  await closeWindows(pc);
  const previous = await home.evaluate(() => reviewDocument);
  await home.goto(`${origin}/news/?branch=second`);
  await home.goBack();
  await home.waitForFunction(previous => window.reviewDocument !== previous, previous, { polling: 100 });
  await desktopReady(home, ids);
  check('소식 이동 후 홈 재방문·브라우저 뒤로가기 재노출', ids);
  await closeWindows(pc);

  const beforeRestore = await home.evaluate(() => reviewDocument);
  await home.evaluate(() => dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true })));
  await home.waitForFunction(previous => window.reviewDocument && window.reviewDocument !== previous,
    beforeRestore, { polling: 100 });
  await desktopReady(home, ids);
  check('캐시 복원 pageshow 분기: 서버 재조회 후 재노출', 'persisted event injected; actual OS BFCache not asserted');
  await closeWindows(pc, ids[0]);
  const hiddenUntil = await midnight(home, ids[0]);
  await home.reload();
  await desktopReady(home, ids.slice(1));
  await closeWindows(pc);
  await home.goto(`${origin}/news/`);
  await home.goto(`${origin}/?branch=second`);
  await desktopReady(home, ids.slice(1));
  await closeWindows(pc);
  const newTab = await pc.newPage();
  await newTab.goto(`${origin}/`);
  await desktopReady(newTab, ids.slice(1));
  await closeWindows(pc);
  check('PC 오늘 숨김: 선택한 글만 새로고침·재방문·새 탭에서 제외·한국 시간 다음 날 00시', { id: ids[0], hiddenUntil });
  await home.evaluate(id => localStorage.setItem(`y3gym.prototype.hide:${id}`, String(Date.now() - 1)), ids[0]);
  await home.reload();
  await desktopReady(home, ids);
  await closeWindows(pc);
  check('숨김 기록 만료 후 전체 다시 노출', ids);
  await pc.close();

  const mobile = await context(true);
  const page = await mobile.newPage();
  await page.goto(`${origin}/?branch=second`);
  const mobileData = await payload(page);
  await mobileClose(page, mobileData);
  await page.reload();
  await page.locator('dialog[open]').waitFor();
  await page.screenshot({ path: path.join(output, 'mobile-reloaded.png') });
  await mobileClose(page, mobileData);
  await page.goto(`${origin}/news/`);
  await page.goto(`${origin}/?branch=second`);
  await mobileClose(page, mobileData, mobileData[0].id);
  const mobileHiddenUntil = await midnight(page, mobileData[0].id);
  await page.reload();
  await mobileClose(page, mobileData.slice(1));
  check('모바일 일반 닫기 후 새로고침·재방문 순차 재노출, 오늘 숨김은 선택 글만 제외', { count: mobileData.length, hiddenUntil: mobileHiddenUntil });
  await mobile.close();

  const blocked = await context();
  const fallback = await blocked.newPage();
  await fallback.addInitScript(() => {
    window.reviewOriginalOpen = window.open;
    window.open = (...args) => { window.reviewAttempts.push(args[0]); return null; };
  });
  for (let visit = 0; visit < 2; visit++) {
    if (!visit) await fallback.goto(`${origin}/?branch=second`);
    else await fallback.reload();
    await fallback.locator('[data-popup-recovery] a').first().waitFor();
    assert.equal(await fallback.locator('[data-popup-recovery] a').count(), ids.length);
    assert.equal(await fallback.evaluate(() => reviewAttempts.length), ids.length);
  }
  await fallback.evaluate(() => { window.open = window.reviewOriginalOpen; });
  const [manual] = await Promise.all([fallback.waitForEvent('popup'),
    fallback.locator('[data-popup-recovery] a').first().click()]);
  await manual.locator('[data-popup-content]').waitFor();
  assert.equal(new URL(manual.url()).searchParams.get('branch'), 'second');
  check('자동 차단도 새로고침 시 재시도·글별 수동 복구 유지', ids.length);
  await blocked.close();

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
