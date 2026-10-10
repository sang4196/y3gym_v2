import { chromium, expect } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const directory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const output = path.join(directory, 'review', 'branch-slides');
const baseURL = process.env.PROTOTYPE_URL || 'http://127.0.0.1:8767';
await mkdir(output, { recursive: true });
const browser = await chromium.launch();
const errors = [];
const report = {
  reviewedAt: new Date().toISOString(), browser: 'Chromium',
  scope: 'Unified branch preview with facility carousel and separate branch information page',
  branchTabDesignApproval: 'APPROVED — user: 배치 합격',
  pageSeparationVisualApproval: 'APPROVED — user: ㅇㅋ 이대로 가자',
  facilityCarouselVisualApproval: 'APPROVED — user: 시설슬라이드 통과', homeGalleryApplication: 'Applied shared approved gallery as requested', widths: [], captures: [],
};

async function ready(page) {
  await page.evaluate(() => document.fonts.ready);
  for (const image of await page.locator('main img:not([data-gallery-clone] *)').elementHandles()) {
    if (!await image.isVisible()) continue;
    await image.evaluate(element => (element.closest('[data-gallery-viewport]') || element.parentElement).scrollIntoView({ block: 'center' }));
    await expect.poll(() => image.evaluate(element => element.complete && element.naturalWidth > 0)).toBe(true);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
}

async function capture(page, name, { full = false, branch = false } = {}) {
  const viewport = page.viewportSize();
  await ready(page);
  if (full) {
    const height = await page.evaluate(() => document.documentElement.scrollHeight);
    // A tall real viewport places the fixed contact bar at the composition's end.
    // Its overlap is checked separately using a normal mobile viewport.
    await page.setViewportSize({ width: viewport.width, height });
  }
  if (branch) await page.locator('#branch').evaluate(element => element.scrollIntoView());
  await page.screenshot({ path: path.join(output, name), animations: 'disabled' });
  report.captures.push({ name, viewport: page.viewportSize(), full, branch });
  if (full) await page.setViewportSize(viewport);
}

try {
  const context = await browser.newContext({ locale: 'ko-KR', timezoneId: 'Asia/Seoul', deviceScaleFactor: 1, reducedMotion: 'reduce' });
  await context.addInitScript(() => { if (location.protocol === 'http:') sessionStorage.setItem('y3gym.prototype.auto-attempt', '1'); });
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  page.on('response', response => { if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
  page.on('requestfailed', request => errors.push(`${request.failure()?.errorText} ${request.url()}`));

  for (const width of [320, 375, 768, 1024, 1280, 1440]) {
    await page.setViewportSize({ width, height: width < 768 ? 812 : 900 });
    for (const [name, url] of [['home', '/?branch=main'], ['details', '/branches.html?branch=main']]) {
      await page.goto(baseURL + url, { waitUntil: 'networkidle' });
      await ready(page);
      const metrics = await page.evaluate(() => ({
        documentWidth: document.documentElement.scrollWidth,
        fontLoaded: [...document.fonts].some(font => font.family === 'Pretendard' && font.status === 'loaded'),
        h1Count: document.querySelectorAll('h1').length,
        headingSize: getComputedStyle(document.querySelector('h1')).fontSize,
        visibleContactBar: getComputedStyle(document.querySelector('.mobile-contact-bar')).display !== 'none',
        overflowingButtons: [...document.querySelectorAll('.button')].filter(element =>
          element.getClientRects().length && element.scrollWidth > element.clientWidth + 1).map(element => element.textContent.trim()),
        missingAnchors: [...document.querySelectorAll('a[href^="#"]')].map(link => link.hash.slice(1))
          .filter(id => id && !document.getElementById(id)),
      }));
      expect(metrics.documentWidth).toBeLessThanOrEqual(width + 1);
      expect(metrics.fontLoaded).toBe(true);
      expect(metrics.h1Count).toBe(1);
      expect(metrics.visibleContactBar).toBe(width < 768);
      expect(metrics.overflowingButtons).toEqual([]);
      expect(metrics.missingAnchors).toEqual([]);
      if (width < 768) {
        await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
        expect(await page.evaluate(() => document.querySelector('.footer-note').getBoundingClientRect().bottom <=
          document.querySelector('.mobile-contact-bar').getBoundingClientRect().top)).toBe(true);
      }
      report.widths.push({ page: name, width, ...metrics, status: 'PASS' });
      if (width === 375 || width === 1440) {
        const device = width === 375 ? 'mobile' : 'desktop';
        await capture(page, `${name}-${device}-main-first.png`);
        await capture(page, `${name}-${device}-main-full.png`, { full: true });
        if (name === 'home') {
          await capture(page, `${name}-${device}-main-tabs.png`, { branch: true });
          await page.locator('#main-facilities [data-gallery-viewport]').focus();
          await page.keyboard.press('ArrowRight');
          await capture(page, `${name}-${device}-main-slide-2.png`, { branch: true });
        }
        await page.getByRole('tab', { name: 'Y3GYM 예시점' }).click();
        await capture(page, `${name}-${device}-second-full.png`, { full: true });
        await capture(page, `${name}-${device}-second-${name === 'home' ? 'tabs' : 'first'}.png`, { branch: name === 'home' });
      }
    }
  }

  await page.goto(baseURL + '/?branch=second');
  await expect(page.locator('.trainers, .location, .branch-information')).toHaveCount(0);
  await expect(page.locator('#primary-navigation')).not.toContainText('트레이너');
  await expect(page.locator('.footer-navigation')).not.toContainText('트레이너');
  await page.locator('#primary-navigation a').filter({ hasText: '지점 안내' }).click();
  await expect(page).toHaveURL(/\/branches\.html\?branch=second$/);
  await expect(page.getByRole('tab', { name: 'Y3GYM 예시점' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('#branch-second .trainer')).toContainText('트레이너 B');
  await page.locator('#primary-navigation .header-contact').click();
  await expect(page.locator('#contact-second')).toBeInViewport();
  await page.locator('#contact-second [data-preview-contact="전화"]').click();
  await expect(page.locator('#second-contact-status')).toContainText('Y3GYM 예시점 전화');
  await page.locator('.site-header .wordmark').click();
  await expect(page).toHaveURL(/\/index\.html\?branch=second$/);
  await expect(page.getByRole('tab', { name: 'Y3GYM 예시점' })).toHaveAttribute('aria-selected', 'true');
  report.crossPageNavigation = 'PASS — header, selected branch, contact and home return';

  await page.setViewportSize({ width: 375, height: 812 });
  await page.locator('.menu-toggle').click();
  await expect(page.locator('#primary-navigation')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('.menu-toggle')).toBeFocused();
  await page.locator('.mobile-contact-bar .button--primary').click();
  await expect(page).toHaveURL(/branches\.html\?branch=second#contact-second$/);
  await expect(page.locator('#contact-second')).toBeInViewport();
  report.mobileNavigation = 'PASS — menu and fixed contact bar lead to selected branch';
  await page.setViewportSize({ width: 1440, height: 900 });
  const button = page.locator('#contact-second .button--primary');
  await button.hover();
  expect(await button.evaluate(element => getComputedStyle(element).backgroundColor)).toBe('rgb(39, 76, 107)');
  await button.focus();
  await page.keyboard.press('Tab');
  expect(await page.evaluate(() => getComputedStyle(document.activeElement).outlineWidth)).toBe('2px');
  report.buttonStates = 'PASS — hover and keyboard focus';
  expect(errors).toEqual([]);
  report.status = 'PASS';
  await context.close();
} catch (error) {
  report.status = 'FAIL';
  report.error = error.stack || String(error);
  process.exitCode = 1;
} finally {
  report.errors = errors;
  report.limitations = ['No physical-device or other-browser verification', 'No backend or real service integration'];
  await browser.close();
  await writeFile(path.join(output, 'checks.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ status: report.status, pagesAndWidths: report.widths.length, captures: report.captures.length, error: report.error }, null, 2));
}
