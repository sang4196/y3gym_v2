import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '../../../prototype/node_modules/@playwright/test/index.mjs';

const output = path.join(path.dirname(fileURLToPath(import.meta.url)), 'live-sections');
await fs.mkdir(output);
const browser = await chromium.launch();
const report = { status: 'RUNNING', origin: 'http://localhost:8768', httpReadOnly: true, captures: [], errors: [] };
try {
  for (const width of [1440, 375]) {
    const context = await browser.newContext({ viewport: { width, height: 900 } });
    const page = await context.newPage();
    page.on('pageerror', error => report.errors.push(error.message));
    for (const key of ['main', 'second']) {
      await page.goto(report.origin + '/branches/?branch=' + key);
      const section = page.locator(`#branch-${key}:not([hidden]) [data-branch-section="trainers"]`);
      await section.waitFor();
      await page.evaluate(async () => {
        await document.fonts.ready;
        await Promise.all([...document.images].map(image => { image.loading = 'eager'; return image.decode().catch(() => {}); }));
      });
      assert.equal(await section.locator('[data-trainer-id]').count(), 1);
      const filename = `${key}-${width}-section.png`;
      await section.screenshot({ path: path.join(output, filename) });
      report.captures.push({ filename, width, branch: key, box: await section.boundingBox(), name: await section.locator('h4').innerText() });
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
  await fs.writeFile(path.join(output, 'captures.json'), JSON.stringify(report, null, 2) + '\n');
  await browser.close();
}
console.log(report.status, report.captures.length, 'read-only section captures');
