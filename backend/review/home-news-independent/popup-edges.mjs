import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '../../../prototype/node_modules/@playwright/test/index.mjs';

// Read-only checks against currently eligible CMS examples. Run review-popups
// first if its review period has expired. No admin credentials or DB writes.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const output = path.resolve(root, process.env.Y3GYM_HOME_NEWS_REVIEW_DIR || 'review/home-news-independent/browser', 'popup-edges');
await fs.mkdir(output, { recursive: true });
const report = { run: new Date().toISOString(), status: 'RUNNING', checks: [], errors: [], screenshots: [] };
const browser = await chromium.launch();
const origin = process.env.Y3GYM_HOME_NEWS_ORIGIN;
assert(origin && new URL(origin).hostname === 'localhost' && !['8767', '8768'].includes(new URL(origin).port), 'Isolated test server required.');
const check = (name, detail) => {
  report.checks.push({ name, detail, result: 'PASS' });
  console.log(`PASS ${name}`);
};
const watch = page => page.on('pageerror', error => report.errors.push(error.message));
const capture = async (page, name) => {
  await page.screenshot({ path: path.join(output, name) });
  report.screenshots.push(name);
};
try {
  const mobile = await browser.newContext({ viewport: { width: 375, height: 568 } });
  const page = await mobile.newPage();
  watch(page);
  const windows = [];
  page.on('popup', popup => windows.push(popup));
  await page.goto(`${origin}/?branch=second`);
  const payload = JSON.parse(await page.locator('#home-popup-data').textContent());
  assert(payload.length >= 2, 'Currently eligible examples required; run review-popups first.');
  for (let index = 0; index < payload.length; index++) {
    await page.locator('dialog[open] #mobile-popup-title').filter({ hasText: payload[index].title }).waitFor();
    await page.locator('[data-mobile-close-popup]').waitFor();
    const bounds = await page.locator('[data-mobile-close-popup]').boundingBox();
    assert(bounds.y >= 0 && bounds.y + bounds.height <= 568);
    if (!index) {
      await page.locator('[data-mobile-close-popup]').focus();
      await page.keyboard.press('Tab');
      assert(await page.locator('[data-mobile-popup-post]').evaluate(element => element === document.activeElement));
      await page.keyboard.press('Shift+Tab');
      assert(await page.locator('[data-mobile-close-popup]').evaluate(element => element === document.activeElement));
      await capture(page, 'popup-mobile-short.png');
    }
    await page.keyboard.press('Escape');
  }
  await page.locator('dialog.mobile-popup').waitFor({ state: 'detached' });
  assert(!(await page.locator('html').getAttribute('class') || '').includes('mobile-popup-open'));
  await page.locator('.mobile-contact-bar').waitFor({ state: 'visible' });
  assert.equal(windows.length, 0);
  check('짧은 모바일 화면 닫기 가시성·Tab 포커스 순환·Escape 순차 닫기·문의 바 복원', payload.length);

  const resized = await mobile.newPage();
  watch(resized);
  resized.on('popup', popup => windows.push(popup));
  await resized.goto(`${origin}/`);
  await resized.locator('dialog[open]').waitFor();
  await resized.setViewportSize({ width: 1440, height: 900 });
  await resized.locator('dialog[open]').waitFor({ state: 'detached' });
  await resized.waitForFunction(() => !document.documentElement.classList.contains('mobile-popup-open'));
  assert(!(await resized.locator('html').getAttribute('class') || '').includes('mobile-popup-open'));
  await resized.setViewportSize({ width: 375, height: 568 });
  assert.equal(await resized.locator('dialog[open]').count(), 0);
  await resized.reload();
  await resized.locator('dialog[open]').waitFor();
  assert.equal(windows.length, 0);
  check('모바일→PC 전환 시 잠금 해제·크기 변경만으로 재노출 없음·새로고침 시 재노출', 'same tab');
  await mobile.close();

  const denied = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const fallback = await denied.newPage();
  watch(fallback);
  await fallback.addInitScript(() => Object.defineProperty(window, 'sessionStorage', { get() { throw new Error('review storage denied'); } }));
  const automatic = [];
  fallback.on('popup', page => automatic.push(page));
  await fallback.goto(`${origin}/?branch=second`);
  for (let attempt = 0; automatic.length < payload.length && attempt < 50; attempt++) await fallback.waitForTimeout(100);
  assert.equal(automatic.length, payload.length);
  for (const popup of automatic) {
    await popup.locator('[data-popup-content]').waitFor();
    assert.equal(new URL(popup.url()).searchParams.get('branch'), 'second');
  }
  assert.equal(await fallback.locator('[data-popup-recovery] a:visible').count(), 0);
  await capture(fallback, 'home-session-storage-unavailable.png');
  check('세션 저장소 제한도 자동 노출을 막지 않음·실제 창 전체 연결', payload.length);
  await denied.close();
  assert.deepEqual(report.errors, []);
  report.status = 'PASS';
} catch (error) {
  report.status = 'FAIL';
  report.failure = error.stack || error.message;
  process.exitCode = 1;
} finally {
  await browser.close();
  await fs.writeFile(path.join(output, 'edge-checks.json'), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ status: report.status, checks: report.checks.length, failure: report.failure }));
}
