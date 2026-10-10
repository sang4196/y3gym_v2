import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { chromium } from '../../../prototype/node_modules/@playwright/test/index.mjs';

const output = new URL('./live-sections-final/', import.meta.url);
await fs.mkdir(output, { recursive: false });
const browser = await chromium.launch();
const report = { status: 'RUNNING', readOnly: true, checks: [], errors: [] };
try {
  for (const width of [1440, 375]) {
    const context = await browser.newContext({ viewport: { width, height: 812 } });
    const page = await context.newPage();
    page.on('pageerror', error => report.errors.push(error.message));
    for (const key of ['main', 'second']) {
      await page.goto(`http://localhost:8768/branches/?branch=${key}`);
      const panel = page.locator(`#branch-${key}:not([hidden])`);
      await panel.waitFor();
      await page.evaluate(async () => {
        await document.fonts.ready;
        await Promise.all([...document.images].map(image => {
          image.loading = 'eager';
          return image.decode().catch(() => {});
        }));
      });
      const card = panel.locator('[data-trainer-id]');
      assert.equal(await card.count(), 1);
      const frame = await card.locator('.profile-image-frame').boundingBox();
      assert(Math.abs(frame.width / frame.height - 0.8) < 0.005);
      const measurement = await card.evaluate(element => ({
        name: element.querySelector('h4').textContent,
        font: getComputedStyle(element).fontFamily,
        intro: element.querySelector('[data-trainer-intro]')?.textContent,
        optional: element.querySelectorAll('[data-trainer-position], [data-trainer-biography]').length,
        viewport: innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
      }));
      assert.equal(measurement.optional, 0);
      assert(measurement.scrollWidth <= width + 1);
      assert(measurement.font.includes('Pretendard'));
      await panel.locator('[data-branch-section="trainers"]').screenshot({ path: new URL(`${key}-${width}-section.png`, output).pathname });
      const last = card.locator('.trainer-copy > :last-child');
      await last.evaluate(element => element.scrollIntoView({ block: 'center' }));
      const textBox = await last.boundingBox();
      const bar = await page.locator('.mobile-contact-bar').boundingBox();
      if (width === 375 && bar) assert(textBox.y + textBox.height <= bar.y + 1);
      const href = await card.locator('a[href^="#contact-"]').getAttribute('href');
      assert.equal(href, `#contact-${key}`);
      await card.locator('a[href^="#contact-"]').click();
      assert(new URL(page.url()).hash === `#contact-${key}`);
      const heading = await panel.locator(`#contact-${key}`).innerText();
      assert(heading.includes(key === 'main' ? '본점' : '예시점'));
      report.checks.push({ width, key, result: 'PASS', measurement, photoRatio: frame.width / frame.height, contactHref: href, lastTextAfterScroll: textBox, mobileContactBar: bar });
    }
    await context.close();
  }
  assert.equal(report.errors.length, 0);
  report.status = 'PASS';
} catch (error) {
  report.status = 'FAIL';
  report.failure = error.stack;
  process.exitCode = 1;
} finally {
  await browser.close();
  await fs.writeFile(new URL('checks.json', output), JSON.stringify(report, null, 2) + '\n', { flag: 'wx' });
}
console.log(JSON.stringify({ status: report.status, checks: report.checks.length, failure: report.failure }));
