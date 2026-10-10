import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '../../../prototype/node_modules/@playwright/test/index.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const output = path.resolve(root, 'review/home-news-independent/browser/all-popups');
const origin = process.env.Y3GYM_HOME_NEWS_ORIGIN;
assert(origin && new URL(origin).hostname === 'localhost' && !['8767', '8768'].includes(new URL(origin).port));
const expected = JSON.parse(process.env.Y3GYM_INDEPENDENT_POPUP_MANIFEST);
assert.equal(expected.length, 6);
await fs.mkdir(output, { recursive: true });
const report = { status: 'RUNNING', expectedRegistrationOrder: expected, checks: [], errors: [] };
const browser = await chromium.launch();
const record = (name, detail) => report.checks.push({ name, detail, result: 'PASS' });
try {
  for (const mobile of [false, true]) {
    const context = await browser.newContext({ viewport: mobile ? { width: 375, height: 812 } : { width: 1440, height: 900 } });
    context.on('page', page => page.on('pageerror', error => report.errors.push(error.message)));
    await context.addInitScript(() => {
      window.independentAttempts = [];
      window.independentReady = [];
      const original = window.open.bind(window);
      window.open = (...args) => { window.independentAttempts.push(args[0]); return original(...args); };
      window.addEventListener('message', event => {
        if (event.origin === location.origin && event.data?.type === 'y3gym-popup-ready') window.independentReady.push(event.data.id);
      });
    });
    const page = await context.newPage();
    await page.goto(origin + '/?branch=second');
    const payload = JSON.parse(await page.locator('#home-popup-data').textContent());
    assert.deepEqual(payload.map(item => ({ id: Number(item.postId), title: item.title })), expected);
    assert(!payload.some(item => item.title.includes('비공개')));
    const expectedHomeIds = expected.slice(1).reverse().map(item => item.id);
    if (!mobile) {
      await page.waitForFunction(ids => independentAttempts.length === ids.length && ids.every(id => independentReady.includes(id)), expected.map(p => 'post-' + p.id));
      const attempted = await page.evaluate(() => independentAttempts);
      assert.deepEqual(attempted.map(url => new URL(url, origin).pathname), expected.map(p => '/popups/' + p.id + '/'));
      assert.equal(context.pages().filter(p => new URL(p.url()).pathname.startsWith('/popups/')).length, 6);
      record('PC 홈 5건과 별개로 등록순 팝업 6건 자동 열기·ready', attempted);
    } else {
      const shown = [];
      for (const item of expected) {
        const title = page.locator('dialog[open] #mobile-popup-title');
        await title.filter({ hasText: item.title }).waitFor();
        assert.equal(await title.textContent(), item.title);
        shown.push(item.id);
        if (shown.length === 1) await page.screenshot({ path: path.join(output, 'mobile-oldest-outside-home.png') });
        await page.locator('[data-mobile-close-popup]').click();
      }
      await page.locator('dialog.mobile-popup').waitFor({ state: 'detached' });
      assert.equal(await page.evaluate(() => independentAttempts.length), 0);
      record('모바일 홈에서 빠진 가장 오래된 글 포함 등록순 팝업 6건 순차 표시·닫기', shown);
    }
    const actualHomeIds = await page.locator('#news .news-title-link').evaluateAll(links => links.map(a => Number(new URL(a.href).pathname.split('/').filter(Boolean).at(-1))));
    assert.deepEqual(actualHomeIds, expectedHomeIds);
    assert(!actualHomeIds.includes(expected[0].id));
    await context.close();
  }
  assert.deepEqual(report.errors, []);
  report.status = 'PASS';
  console.log(JSON.stringify(report));
} catch (error) {
  report.status = 'FAIL';
  report.failure = error.stack;
  process.exitCode = 1;
  console.error(error);
} finally {
  await fs.writeFile(path.join(output, 'checks.json'), JSON.stringify(report, null, 2), { flag: 'wx' });
  await browser.close();
}
