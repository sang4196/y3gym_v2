import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { chromium } from '../../../prototype/node_modules/@playwright/test/index.mjs';

const origin = process.env.Y3GYM_INDEPENDENT_ORIGIN;
assert(origin && new URL(origin).hostname === 'localhost' && !['8767', '8768'].includes(new URL(origin).port));
const output = new URL('./long-biography/', import.meta.url);
await fs.mkdir(output, { recursive: false });
const report = { status: 'RUNNING', isolatedTestDatabase: true, checks: [] };
const browser = await chromium.launch();
try {
  for (const width of [1440, 900, 375]) {
    const context = await browser.newContext({ viewport: { width, height: 812 } });
    const page = await context.newPage();
    await page.goto(origin + '/branches/?branch=main');
    await page.evaluate(async () => {
      await document.fonts.ready;
      await Promise.all([...document.images].map(image => { image.loading = 'eager'; return image.decode().catch(() => {}); }));
    });
    const grid = page.locator('#branch-main .trainer-grid');
    const card = grid.locator(`[data-trainer-id="${process.env.Y3GYM_INDEPENDENT_TRAINER}"]`);
    const columns = await grid.evaluate(element => getComputedStyle(element).gridTemplateColumns.split(' ').length);
    assert.equal(columns, width === 375 ? 1 : 2);
    assert.equal(await card.locator('li').count(), 12);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    const image = await card.locator('.profile-image-frame').boundingBox();
    assert(Math.abs(image.width / image.height - 0.8) < 0.005);
    const last = card.locator('li').last();
    await last.evaluate(element => element.scrollIntoView({ block: 'center' }));
    const lastBox = await last.boundingBox();
    const bar = await page.locator('.mobile-contact-bar').boundingBox();
    if (width === 375) {
      assert(lastBox.y >= 64);
      assert(lastBox.y + lastBox.height <= bar.y + 1);
      await page.screenshot({ path: new URL('last-biography-mobile-viewport.png', output).pathname });
    }
    const contact = card.locator('a[href="#contact-main"]');
    await contact.evaluate(element => element.scrollIntoView({ block: 'center' }));
    const contactBox = await contact.boundingBox();
    if (width === 375) {
      assert(contactBox.y + contactBox.height <= bar.y + 1);
      await page.screenshot({ path: new URL('profile-inquiry-mobile-viewport.png', output).pathname });
    }
    report.checks.push({ width, result: 'PASS', columns, photoRatio: image.width / image.height, lastBiography: lastBox, contact: contactBox, mobileBar: bar });
    await context.close();
  }
  report.status = 'PASS';
} catch (error) {
  report.status = 'FAIL'; report.failure = error.stack; process.exitCode = 1;
} finally {
  await browser.close();
  await fs.writeFile(new URL('checks.json', output), JSON.stringify(report, null, 2) + '\n', { flag: 'wx' });
}
console.log(JSON.stringify(report));
