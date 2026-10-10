import { chromium, expect } from '@playwright/test';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { branches } from '../branch-data.js';
import { renderHome, renderDetails } from './render-branches.mjs';

const directory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const output = path.join(directory, 'review', 'facility-motion');
const baseURL = process.env.PROTOTYPE_URL || 'http://127.0.0.1:8767';
await mkdir(output, { recursive: true });
const browser = await chromium.launch();
const errors = [];
const report = { reviewedAt: new Date().toISOString(), browser: 'Chromium', designApproval: 'APPROVED — user: 시설슬라이드 통과', homeApplication: 'Applied the approved gallery as requested', tests: [], widths: [], captures: [] };

async function fixture(options = {}) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'ko-KR', ...options });
  await context.addInitScript(() => { if (location.protocol === 'http:') sessionStorage.setItem('y3gym.prototype.auto-attempt', '1'); });
  context.on('page', page => page.on('pageerror', error => errors.push(error.message)));
  return { context, page: await context.newPage() };
}
async function test(name, action) {
  try { await action(); report.tests.push({ name, status: 'PASS' }); }
  catch (error) { report.tests.push({ name, status: 'FAIL', error: error.stack || String(error) }); process.exitCode = 1; }
  console.log(`${report.tests.at(-1).status}: ${name}`);
}
const transform = gallery => gallery.locator('[data-gallery-track]').evaluate(element => Number(element.style.transform.match(/translate3d\(([-.\d]+)/)[1]));
async function blurAndLeave(page) { await page.evaluate(() => document.activeElement.blur()); await page.mouse.move(0, 0); }

try {
  for (const view of ['home', 'details']) {
  const route = view === 'home' ? '/index.html' : '/branches.html';
  const assetPrefix = view === 'home' ? 'home-' : '';
  await test(`${view}: Six widths preserve the existing 3/2/1 photo layout without buttons and keep the track clipped`, async () => {
    const { context, page } = await fixture({ reducedMotion: 'reduce' });
    try {
      for (const width of [320, 375, 768, 1024, 1280, 1440]) {
        await page.setViewportSize({ width, height: width < 768 ? 812 : 900 });
        await page.goto(baseURL + route + '?branch=main');
        const gallery = page.locator('#branch-main [data-facility-gallery]');
        await expect(gallery).toHaveClass(/is-ready/);
        await gallery.scrollIntoViewIfNeeded();
        await page.evaluate(() => document.fonts.ready);
        await expect.poll(() => gallery.locator('[data-gallery-slide] img').evaluateAll(images => images.every(image => image.complete && image.naturalWidth))).toBe(true);
        const columns = width < 768 ? 1 : width < 1024 ? 2 : 3;
        const metrics = await gallery.evaluate(element => {
          const viewport = element.querySelector('[data-gallery-viewport]');
          const card = element.querySelector('[data-gallery-slide]');
          return { content: document.documentElement.scrollWidth, width: viewport.clientWidth,
            card: card.getBoundingClientRect().width, gap: parseFloat(getComputedStyle(element).getPropertyValue('--gallery-gap')) };
        });
        expect(metrics.content).toBeLessThanOrEqual(width + 1);
        expect(Math.abs(metrics.card * columns + metrics.gap * (columns - 1) - metrics.width)).toBeLessThan(1);
        await expect(gallery.locator('[data-gallery-slide]')).toHaveCount(3);
        await expect(gallery.locator('button')).toHaveCount(0);
        await expect(gallery.locator('[data-gallery-clone]:not([aria-hidden="true"])')).toHaveCount(0);
        expect(await gallery.locator('[data-gallery-clone]').evaluateAll(clones => clones.every(clone => clone.inert))).toBe(true);
        report.widths.push({ view, width, columns, ...metrics, status: 'PASS' });
        if (width === 375 || width === 1440) {
          const name = width === 375 ? 'mobile' : 'desktop';
          await page.locator('#main-facilities').screenshot({ path: path.join(output, `${assetPrefix}facilities-${name}.png`) });
          report.captures.push(`${assetPrefix}facilities-${name}.png`);
          await page.evaluate(() => window.scrollTo(0, 0));
          const viewport = page.viewportSize();
          await page.setViewportSize({ width, height: await page.evaluate(() => document.documentElement.scrollHeight) });
          const fullName = `${view === 'home' ? 'home' : 'branches'}-${name}-full.png`;
          await page.screenshot({ path: path.join(output, fullName) });
          await page.setViewportSize(viewport);
          report.captures.push(fullName);
        }
      }
    } finally { await context.close(); }
  });

  await test(`${view}: Autoplay moves left, loops continuously, pauses for hover/focus and resets per branch without buttons`, async () => {
    const { context, page } = await fixture();
    try {
      await page.clock.install();
      await page.goto(baseURL + route + '?branch=main');
      const gallery = page.locator('#branch-main [data-facility-gallery]');
      await gallery.scrollIntoViewIfNeeded();
      await expect(gallery).toHaveClass(/is-ready/);
      await page.clock.runFor(100);
      const initial = await transform(gallery);
      await page.clock.runFor(5200);
      const moved = await transform(gallery);
      expect(moved).toBeLessThan(initial);
      await page.clock.runFor(10300);
      expect(await transform(gallery)).toBeCloseTo(initial, 1);
      await page.setViewportSize({ width: 1440, height: 400 });
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
      await expect(gallery.locator('[data-gallery-viewport]')).not.toBeInViewport({ ratio: 0.15 });
      await page.clock.runFor(10000);
      expect(await transform(gallery)).toBeCloseTo(initial, 1);
      await page.setViewportSize({ width: 1440, height: 900 });
      await gallery.scrollIntoViewIfNeeded();
      await gallery.hover();
      await page.clock.runFor(10000);
      expect(await transform(gallery)).toBeCloseTo(initial, 1);
      await page.mouse.move(0, 0);
      await gallery.locator('[data-gallery-viewport]').focus();
      await page.clock.runFor(6000);
      expect(await transform(gallery)).toBeCloseTo(initial, 1);
      await page.keyboard.press('ArrowLeft');
      await page.clock.runFor(700);
      expect(await transform(gallery)).toBeLessThan(moved);
      await blurAndLeave(page);
      await page.clock.runFor(5200);
      expect(await transform(gallery)).toBeCloseTo(initial, 1);
      await page.getByRole('tab', { name: 'Y3GYM 예시점' }).click();
      await page.getByRole('tab', { name: 'Y3GYM 본점' }).click();
      await gallery.scrollIntoViewIfNeeded();
      expect(await transform(gallery)).toBeCloseTo(initial, 1);
      const hidden = page.locator('#branch-second [data-facility-gallery]');
      const hiddenPosition = await transform(hidden);
      await page.clock.runFor(10000);
      expect(await transform(hidden)).toBe(hiddenPosition);
    } finally { await context.close(); }
  });

  await test(`${view}: Reduced motion starts stopped, mobile touch moves a photo and resize preserves layout`, async () => {
    const { context, page } = await fixture({ viewport: { width: 375, height: 812 }, hasTouch: true, reducedMotion: 'reduce' });
    try {
      await page.clock.install();
      await page.goto(baseURL + route + '?branch=second');
      const gallery = page.locator('#branch-second [data-facility-gallery]');
      await gallery.scrollIntoViewIfNeeded();
      await expect(gallery.locator('button')).toHaveCount(0);
      await page.clock.runFor(100);
      const initial = await transform(gallery);
      await page.clock.runFor(10000);
      expect(await transform(gallery)).toBe(initial);
      const box = await gallery.locator('[data-gallery-viewport]').boundingBox();
      const y = Math.max(100, Math.min(650, box.y + 100));
      const cdp = await context.newCDPSession(page);
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: 300, y }] });
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: 120, y: y + 4 }] });
      await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
      expect(await transform(gallery)).toBeLessThan(initial);
      await page.setViewportSize({ width: 1024, height: 900 });
      await expect.poll(() => gallery.locator('[data-gallery-slide]').first().evaluate(element => element.getBoundingClientRect().width)).toBeGreaterThan(250);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(1024);
    } finally { await context.close(); }
  });

  await test(`${view}: Zero/one photos remain static; failed images and disabled JavaScript retain useful content`, async () => {
    const { context, page } = await fixture({ reducedMotion: 'reduce' });
    try {
      const template = await readFile(path.join(directory, `templates/${view === 'home' ? 'home' : 'branches'}.html`), 'utf8');
      const render = view === 'home' ? renderHome : renderDetails;
      const sparse = [{ ...branches[0], facilities: branches[0].facilities.slice(0, 1) }, { ...branches[1], facilities: [] }];
      await context.route('**/branches-sparse.html*', route => route.fulfill({ contentType: 'text/html', body: render(template, sparse) }));
      await page.goto(baseURL + '/branches-sparse.html');
      await expect(page.locator('#main-facilities button')).toHaveCount(0);
      await expect(page.locator('[data-gallery-clone]')).toHaveCount(0);
      await page.getByRole('tab', { name: 'Y3GYM 예시점' }).click();
      await expect(page.locator('#second-facilities')).toHaveCount(0);
      if (view === 'details') await expect(page.locator('#contact-second')).toContainText('031-000-0002');
      else await expect(page.locator('#branch-second')).toContainText('등록된 시설 사진이 없습니다.');
      await page.goto(baseURL + (view === 'home' ? '/preview-failures.html' : '/branches-failures.html') + '?branch=main');
      await page.locator('#main-facilities').scrollIntoViewIfNeeded();
      await expect(page.locator('#main-facilities [data-gallery-slide] .image-fallback').first()).toBeVisible();
    } finally { await context.close(); }
    const fallback = await fixture({ javaScriptEnabled: false, viewport: { width: 375, height: 812 } });
    try {
      await fallback.page.goto(baseURL + route);
      await expect(fallback.page.locator('[data-gallery-slide]')).toHaveCount(6);
      await expect(fallback.page.locator('[data-gallery-clone]')).toHaveCount(0);
      await expect(fallback.page.locator('[data-facility-gallery] button')).toHaveCount(0);
      await expect(fallback.page.locator('#primary-navigation')).toBeVisible();
      if (view === 'home') await fallback.page.locator('#primary-navigation a').filter({ hasText: '지점 안내' }).click();
      await expect(fallback.page.locator('#contact-second')).toContainText('031-000-0002');
    } finally { await fallback.context.close(); }
  });
  }
  await test('No unexpected script errors', async () => { expect(errors).toEqual([]); });
} finally {
  report.status = report.tests.every(item => item.status === 'PASS') ? 'PASS' : 'FAIL';
  report.errors = errors;
  await browser.close();
  await writeFile(path.join(output, 'checks.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ status: report.status, groups: report.tests.length, widths: report.widths.length, captures: report.captures.length }));
}
