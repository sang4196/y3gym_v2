import assert from 'node:assert/strict';
import { chromium } from '../../prototype/node_modules/@playwright/test/index.mjs';

const origin = process.env.Y3GYM_QA_ORIGIN;
const post = process.env.Y3GYM_PRESENTATION_POST;
const browser = await chromium.launch({ headless: true });
const checks = [];
const forbidden = /시각 검토용|로컬 CMS|임시 자료|테스트 자료|실제 서비스는 연결하지 않습니다/;
try {
  for (const width of [1440, 375]) {
    const context = await browser.newContext({ viewport: { width, height: 1000 } });
    const page = await context.newPage();
    let dialogs = 0;
    page.on('dialog', async dialog => { dialogs++; await dialog.dismiss(); });
    const opened = width === 1440 ? context.waitForEvent('page') : null;
    await page.goto(origin + '/');
    if (width === 1440) {
      const popup = await opened;
      await popup.waitForLoadState();
      assert(!forbidden.test(await popup.locator('body').innerText()));
      assert.equal(await popup.locator('[data-popup-image]').getAttribute('alt'), '이용 안내');
      assert(new URL(await popup.locator('[data-popup-post]').getAttribute('href'), origin).pathname === `/news/${post}/`);
      await popup.locator('[data-close-popup]').click();
    } else {
      await page.locator('.mobile-popup[open]').waitFor();
      assert(!forbidden.test(await page.locator('.mobile-popup').innerText()));
      assert.equal(await page.locator('[data-mobile-popup-image]').getAttribute('alt'), '이용 안내');
      await page.locator('[data-mobile-close-popup]').click();
      await page.locator('.menu-toggle').click();
      assert.equal(await page.locator('.menu-toggle').getAttribute('aria-expanded'), 'true');
      await page.locator('.menu-toggle').click();
    }
    assert(!forbidden.test(await page.locator('body').innerText()));
    await page.locator('.hero-actions .button').first().click();
    await page.waitForURL(url => url.pathname === '/branches/' && url.hash === '#contact-main');
    assert.equal(dialogs, 0);
    assert.equal(await page.locator('[href^="tel:"]').count(), 1);
    assert.equal(await page.locator('[href="https://pf.kakao.com/_fixture/chat"]').count(), 1);
    await page.locator('#tab-second').click();
    assert.equal(await page.locator('#tab-second').getAttribute('aria-selected'), 'true');
    assert(await page.locator('[data-footer-branch="second"]').isVisible());
    assert(!(await page.locator('[data-footer-branch="main"]').isVisible()));
    assert(!(await page.locator('.mobile-contact-bar').isVisible()));
    assert(!forbidden.test(await page.locator('body').innerText()));
    await page.goto(origin + `/news/${post}/`);
    assert(!forbidden.test(await page.locator('body').innerText()));
    assert((await page.locator('.site-footer').innerText()).includes('Copyright ©'));
    checks.push({ width, nativeInquiry: true, branchSwitch: true, popup: true, footer: true });
    await context.close();
  }
  console.log(JSON.stringify({ status: 'PASS', checks }));
} finally {
  await browser.close();
}
