import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { chromium } from '../../../prototype/node_modules/@playwright/test/index.mjs';

// Supplemental read-only measurements; no administrator login or DB writes.
const output = new URL('./', import.meta.url);
const browser = await chromium.launch();
const context = await browser.newContext({ reducedMotion: 'reduce' });
await context.addInitScript(() => { window.open = () => null; });
const page = await context.newPage();
const report = { run: new Date().toISOString(), origin: 'http://localhost:8768', readOnly: true, status: 'RUNNING', checks: [], errors: [] };
page.on('pageerror', error => report.errors.push(error.message));
try {
  for (const [width, height, expected] of [[1440, 900, 3], [900, 1000, 2], [375, 812, 1]]) {
    await page.setViewportSize({ width, height });
    for (const route of ['/', '/branches/']) {
      await page.goto(`${report.origin}${route}?branch=second`);
      await page.locator('#tab-second[aria-selected="true"]').waitFor();
      const measurements = await page.locator('#branch-second [data-facility-gallery]').evaluate(gallery => {
        const viewport = gallery.querySelector('[data-gallery-viewport]');
        const track = gallery.querySelector('[data-gallery-track]');
        const slide = gallery.querySelector('[data-gallery-slide]');
        const gap = parseFloat(getComputedStyle(track).columnGap);
        return {
          viewport: viewport.getBoundingClientRect().width,
          slide: slide.getBoundingClientRect().width,
          gap,
          overflow: document.documentElement.scrollWidth > innerWidth,
          transitionDuration: getComputedStyle(track).transitionDuration,
        };
      });
      const columns = (measurements.viewport + measurements.gap) / (measurements.slide + measurements.gap);
      assert(Math.abs(columns - expected) < 0.02, JSON.stringify(measurements));
      assert(!measurements.overflow);
      report.checks.push({ route, width, height, expectedColumns: expected, measuredColumns: columns, ...measurements, result: 'PASS' });
      if (width === 900) {
        await page.evaluate(async () => {
          await document.fonts.ready;
          await Promise.all([...document.images].map(image => { image.loading = 'eager'; return image.decode().catch(() => {}); }));
        });
        await page.screenshot({ path: new URL(route === '/' ? 'home-tablet.png' : 'branches-tablet.png', output).pathname, fullPage: true });
      }
    }
  }
  assert.equal(report.errors.length, 0);
  report.status = 'PASS';
} catch (error) {
  report.status = 'FAIL';
  report.errors.push(error.stack);
  process.exitCode = 1;
} finally {
  await fs.writeFile(new URL('layout-checks.json', output), JSON.stringify(report, null, 2) + '\n');
  await browser.close();
}
console.log(`${report.status}: ${report.checks.length} read-only responsive measurements`);
