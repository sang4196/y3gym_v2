import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium, expect } from '@playwright/test';
import { branches } from '../branch-data.js';
import { renderHome, renderDetails } from './render-branches.mjs';
import { getPopupExample } from '../demo-content.js';
import { isPopupEligible, nextKoreanMidnight, storagePrefix } from '../popup-policy.js';

const directory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const output = path.join(directory, 'review', 'states');
const baseURL = process.env.PROTOTYPE_URL || 'http://127.0.0.1:8767';
const fixedNow = Date.parse('2026-10-09T12:00:00+09:00');
const popupOnly = process.argv.includes('--popup-only');
const branchOnly = process.argv.includes('--branch-only');
const tests = [];
const skipped = [];
const browserErrors = [];
const resourceFailures = [];
const browser = await chromium.launch();
await mkdir(output, { recursive: true });

async function test(name, action) {
  if (branchOnly && !/^(Grouped branch|Branch |Empty optional|Failed photographs|Blocked app|No unexpected)/.test(name)) {
    skipped.push(name);
    return;
  }
  if (popupOnly && !/^(Separate popup|Mobile |Blocked automatic|Today hide|Direct popup|Popup content-loading|Unavailable storage|No unexpected)/.test(name)) {
    skipped.push(name);
    return;
  }
  try {
    await action();
    tests.push({ name, status: 'PASS' });
  } catch (error) {
    tests.push({ name, status: 'FAIL', error: error.stack || String(error) });
    process.exitCode = 1;
  }
  console.log(`${tests.at(-1).status}: ${name}`);
}

async function fixture(options = {}) {
  const context = await browser.newContext({
    viewport: options.viewport || { width: 1440, height: 900 },
    javaScriptEnabled: options.javaScriptEnabled !== false,
    hasTouch: options.hasTouch || false, reducedMotion: options.reducedMotion || 'no-preference',
    locale: 'ko-KR', timezoneId: options.timezoneId || 'Asia/Seoul',
  });
  await context.addInitScript(({ now, blocked, storageBlocked, seeds }) => {
    Date.now = () => now;
    if (storageBlocked) {
      for (const name of ['sessionStorage', 'localStorage']) {
        Object.defineProperty(window, name, { get() { throw new DOMException('Fixture storage blocked', 'SecurityError'); } });
      }
    } else {
      if (location.protocol === 'http:') {
        for (const [key, value] of Object.entries(seeds)) localStorage.setItem(key, value);
      }
    }
    const nativeOpen = window.open.bind(window);
    window.__popupOpenCalls = [];
    window.open = (...args) => {
      window.__popupOpenCalls.push(args);
      if (blocked && !navigator.userActivation.isActive) return null;
      return nativeOpen(...args);
    };
  }, { now: options.now ?? fixedNow, blocked: options.blockAuto ?? true,
    storageBlocked: options.storageBlocked ?? false, seeds: options.seeds || {} });
  context.on('page', page => {
    page.on('pageerror', error => browserErrors.push({ url: page.url(), message: error.message }));
    page.on('response', response => {
      if (response.status() >= 400) resourceFailures.push({ url: response.url(), status: response.status() });
    });
    page.on('requestfailed', request => {
      const error = request.failure()?.errorText;
      // Navigation/context teardown can cancel a font preload. Actual font
      // loading is checked in the layout reviews before captures.
      if (request.resourceType() === 'font' && error === 'net::ERR_ABORTED') return;
      resourceFailures.push({ url: request.url(), error });
    });
  });
  return { context, page: await context.newPage() };
}

async function readyImages(page) {
  await page.evaluate(() => document.fonts.ready);
  for (const image of await page.locator('main img:not([data-gallery-clone] *)').elementHandles()) {
    if (!await image.isVisible()) continue;
    await image.evaluate(element => (element.closest('[data-gallery-viewport]') || element.parentElement).scrollIntoView({ block: 'center' }));
    await expect.poll(() => image.evaluate(element => element.complete)).toBe(true);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
}

async function screenshot(page, filename, full = false, selector = null) {
  await readyImages(page);
  const viewport = page.viewportSize();
  if (full) {
    const height = await page.evaluate(() => document.documentElement.scrollHeight);
    await page.setViewportSize({ width: viewport.width, height });
  }
  const options = { path: path.join(output, filename), animations: 'disabled' };
  if (selector) {
    const y = await page.locator(selector).evaluate(element => Math.ceil(element.getBoundingClientRect().top));
    options.clip = { x: 0, y, width: page.viewportSize().width, height: page.viewportSize().height - y };
  }
  await page.screenshot(options);
  if (full) await page.setViewportSize(viewport);
}

async function verifyLayout(page, widths) {
  for (const width of widths) {
    await page.setViewportSize({ width, height: width < 768 ? 812 : 900 });
    await readyImages(page);
    const result = await page.evaluate(() => ({
      width: innerWidth, content: document.documentElement.scrollWidth,
      ids: [...document.querySelectorAll('[id]')].map(element => element.id),
      missingAnchors: [...document.querySelectorAll('a[href^="#"]')]
        .map(link => link.getAttribute('href').slice(1)).filter(id => id && !document.getElementById(id)),
    }));
    expect(result.content).toBeLessThanOrEqual(result.width + 1);
    expect(new Set(result.ids).size).toBe(result.ids.length);
    expect(result.missingAnchors).toEqual([]);
    if (width < 768) {
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
      expect(await page.evaluate(() => document.querySelector('.footer-note').getBoundingClientRect().bottom <=
        document.querySelector('.mobile-contact-bar').getBoundingClientRect().top)).toBe(true);
    }
  }
}

try {
  await test('Popup period boundaries, publication, activation, and Korean midnight', async () => {
    const { popup, post } = getPopupExample();
    assert.equal(isPopupEligible(popup, post, Date.parse(popup.startsAt) - 1), false);
    assert.equal(isPopupEligible(popup, post, Date.parse(popup.startsAt)), true);
    assert.equal(isPopupEligible(popup, post, Date.parse(popup.endsAt) - 1), true);
    assert.equal(isPopupEligible(popup, post, Date.parse(popup.endsAt)), false);
    assert.equal(isPopupEligible({ ...popup, enabled: false }, post, fixedNow), false);
    assert.equal(isPopupEligible(popup, { ...post, published: false }, fixedNow), false);
    assert.equal(isPopupEligible(popup, { ...post, id: 'another' }, fixedNow), false);
    assert.equal(isPopupEligible(popup, null, fixedNow), false);
    assert.equal(isPopupEligible({ ...popup, startsAt: 'invalid' }, post, fixedNow), false);
    assert.equal(nextKoreanMidnight(Date.parse('2026-10-09T23:59:59+09:00')), Date.parse('2026-10-10T00:00:00+09:00'));
    assert.equal(nextKoreanMidnight(Date.parse('2026-10-10T00:00:00+09:00')), Date.parse('2026-10-11T00:00:00+09:00'));
  });

  await test('Separate popup, display acknowledgement, close, once per tab, manual reuse, and connected post', async () => {
    const { context, page } = await fixture({ blockAuto: false });
    try {
      const popupEvent = page.waitForEvent('popup');
      await page.goto(baseURL);
      const popup = await popupEvent;
      await expect(popup.locator('[data-popup-content]')).toBeVisible();
      await expect.poll(() => page.evaluate(key => sessionStorage.getItem(key), storagePrefix + 'shown:visit-notice')).toBeTruthy();
      const calls = await page.evaluate(() => window.__popupOpenCalls);
      expect(calls[0][2]).toContain('popup=yes');
      await expect(page.locator('[data-popup-status]')).toContainText('열었습니다');
      const desktopGeometry = await popup.evaluate(() => ({
        viewport: { width: innerWidth, height: innerHeight },
        gapBelowClose: innerHeight - document.querySelector('[data-close-popup]').getBoundingClientRect().bottom,
      }));
      expect(desktopGeometry.gapBelowClose).toBeLessThanOrEqual(13);
      expect(desktopGeometry.gapBelowClose).toBeGreaterThanOrEqual(11);
      await screenshot(popup, 'popup-desktop.png');
      await expect(popup.locator('[data-close-popup]')).toBeInViewport();
      const closeControl = popup.getByRole('button', { name: '알림 닫기' });
      await expect(closeControl).toContainText('닫기 ×');
      await popup.locator('[data-hide-today]').focus();
      await popup.keyboard.press('Tab');
      await expect(closeControl).toBeFocused();
      const closeStyle = await closeControl.evaluate(element => ({
        size: getComputedStyle(element).fontSize,
        border: getComputedStyle(element).borderWidth,
        outline: getComputedStyle(element).outlineWidth,
        height: element.getBoundingClientRect().height,
        bottomGap: innerHeight - element.getBoundingClientRect().bottom,
      }));
      expect(closeStyle).toEqual({ size: '14px', border: '0px', outline: '2px', height: 44, bottomGap: 12 });
      await closeControl.evaluate(element => element.blur());
      await closeControl.focus();
      await popup.keyboard.press('Enter').catch(error => {
        // Closing on Enter can destroy the target before its key-up reply.
        if (!popup.isClosed()) throw error;
      });
      await expect.poll(() => popup.isClosed()).toBe(true);
      await page.reload();
      await expect(page.locator('[data-open-popup]')).toBeVisible();
      expect(await page.evaluate(() => window.__popupOpenCalls.length)).toBe(0);
      expect(context.pages().length).toBe(1);
      const manualEvent = page.waitForEvent('popup');
      await page.locator('[data-open-popup]').click();
      const manual = await manualEvent;
      await expect(manual.locator('[data-popup-content]')).toBeVisible();
      await expect(page.locator('[data-popup-status]')).toContainText('열었습니다');
      await page.locator('[data-open-popup]').click();
      expect(context.pages().length).toBe(2);
      await manual.locator('[data-popup-post]').click();
      await expect(manual).toHaveURL(/news\/visit\.html$/);
      await expect(manual.getByRole('heading', { level: 1 })).toHaveText('방문 전 확인해주세요');
      await page.locator('[data-open-popup]').click();
      await expect(manual).toHaveURL(/popup\.html$/);
      expect(context.pages().length).toBe(2);
    } finally { await context.close(); }
  });

  await test('Blocked automatic popup is normal when manual entry succeeds; no false shown record', async () => {
    const { context, page } = await fixture();
    try {
      await page.goto(baseURL);
      await expect(page.locator('[data-popup-status]')).toContainText('차단');
      expect(await page.evaluate(key => sessionStorage.getItem(key), storagePrefix + 'shown:visit-notice')).toBeNull();
      expect(context.pages().length).toBe(1);
      await verifyLayout(page, [320, 375, 768, 1440]);
      await page.setViewportSize({ width: 1440, height: 900 });
      await screenshot(page, 'blocked-auto-desktop.png', true, '#news');
      await page.setViewportSize({ width: 375, height: 812 });
      await screenshot(page, 'blocked-auto-mobile.png', true, '#news');
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.reload();
      expect(await page.evaluate(() => window.__popupOpenCalls.length)).toBe(0);
      const popupEvent = page.waitForEvent('popup');
      await page.locator('[data-open-popup]').click();
      const popup = await popupEvent;
      await expect(popup.locator('[data-popup-content]')).toBeVisible();
      await expect.poll(() => page.evaluate(key => sessionStorage.getItem(key), storagePrefix + 'shown:visit-notice')).toBeTruthy();
    } finally { await context.close(); }
  });

  await test('Mobile layer opens without a new tab; close restores scroll/focus, traps focus, and supports short screens', async () => {
    const { context, page } = await fixture({ viewport: { width: 375, height: 812 } });
    try {
      await page.goto(baseURL);
      const layer = page.getByRole('dialog', { name: '방문 전 확인해주세요' });
      await expect(layer).toBeVisible();
      await expect.poll(() => page.evaluate(key => sessionStorage.getItem(key), storagePrefix + 'shown:visit-notice')).toBeTruthy();
      expect(context.pages().length).toBe(1);
      expect(await page.evaluate(() => window.__popupOpenCalls.length)).toBe(0);
      await expect(page.locator('.mobile-contact-bar')).toBeHidden();
      await expect(page.locator('[data-mobile-close-popup]')).toBeFocused();
      await page.keyboard.press('Tab');
      await expect(page.locator('[data-mobile-popup-post]')).toBeFocused();
      await page.keyboard.press('Shift+Tab');
      await expect(page.locator('[data-mobile-close-popup]')).toBeFocused();
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      await expect(page.locator('[data-mobile-hide-today]')).toBeFocused();
      await page.keyboard.press('Tab');
      const control = page.locator('[data-mobile-close-popup]');
      expect(await control.evaluate(element => ({
        size: getComputedStyle(element).fontSize, outline: getComputedStyle(element).outlineWidth,
        border: getComputedStyle(element).borderWidth, height: element.getBoundingClientRect().height,
        gap: element.closest('dialog').getBoundingClientRect().bottom - element.getBoundingClientRect().bottom,
      }))).toEqual({ size: '14px', outline: '2px', border: '0px', height: 44, gap: 12 });
      await control.evaluate(element => element.blur());
      await page.screenshot({ path: path.join(output, 'popup-mobile.png'), animations: 'disabled' });
      await control.click();
      await expect(layer).toBeHidden();
      await expect(page.locator('.mobile-contact-bar')).toBeVisible();
      await expect(page.locator('html')).not.toHaveClass(/mobile-popup-open/);
      await page.reload();
      await expect(layer).toBeHidden();
      await page.locator('[data-open-popup]').scrollIntoViewIfNeeded();
      await page.locator('[data-open-popup]').focus();
      const beforeScroll = await page.evaluate(() => scrollY);
      await page.locator('[data-open-popup]').click();
      await expect(layer).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(layer).toBeHidden();
      await expect(page.locator('[data-open-popup]')).toBeFocused();
      expect(await page.evaluate(() => scrollY)).toBe(beforeScroll);
      await page.locator('[data-open-popup]').click();
      await page.mouse.click(4, 4);
      await expect(layer).toBeHidden();
      await page.locator('[data-open-popup]').click();
      await page.setViewportSize({ width: 320, height: 568 });
      await expect(control).toBeInViewport();
      const compact = await layer.evaluate(element => {
        const bounds = element.getBoundingClientRect();
        const body = element.querySelector('.mobile-popup-body');
        return { top: bounds.top, bottom: bounds.bottom, width: bounds.width,
          scrollable: body.scrollHeight > body.clientHeight, pageWidth: document.documentElement.scrollWidth };
      });
      expect(compact.top).toBeGreaterThanOrEqual(16);
      expect(compact.bottom).toBeLessThanOrEqual(552);
      expect(compact.width).toBeLessThanOrEqual(288);
      expect(compact.pageWidth).toBe(320);
      await page.setViewportSize({ width: 320, height: 480 });
      await expect(control).toBeInViewport();
      expect(await layer.locator('.mobile-popup-body').evaluate(element => element.scrollHeight > element.clientHeight)).toBe(true);
      await page.screenshot({ path: path.join(output, 'popup-mobile-small.png'), animations: 'disabled' });
      await page.setViewportSize({ width: 1440, height: 900 });
      await expect(layer).toBeHidden();
      await expect(page.locator('html')).not.toHaveClass(/mobile-popup-open/);
      expect(context.pages().length).toBe(1);
    } finally { await context.close(); }
  });

  await test('Mobile today hide, manual reopening, same-tab post, and unavailable storage', async () => {
    const { context, page } = await fixture({ viewport: { width: 375, height: 812 } });
    try {
      await page.goto(baseURL);
      await page.locator('[data-mobile-hide-today]').check();
      await page.locator('[data-mobile-close-popup]').click();
      expect(Number(await page.evaluate(key => localStorage.getItem(key), storagePrefix + 'hide:visit-notice')))
        .toBe(Date.parse('2026-10-10T00:00:00+09:00'));
      const second = await context.newPage();
      await second.setViewportSize({ width: 375, height: 812 });
      await second.goto(baseURL);
      await expect(second.getByRole('dialog')).toBeHidden();
      await expect(second.locator('[data-popup-status]')).toContainText('오늘');
      await second.locator('[data-open-popup]').click();
      await expect(second.getByRole('dialog')).toBeVisible();
      await second.locator('[data-mobile-popup-post]').click();
      await expect(second).toHaveURL(/news\/visit\.html$/);
      const inquiry = new URL(await second.locator('#primary-navigation .header-contact').getAttribute('href'), second.url());
      expect(inquiry.pathname).toBe('/branches.html');
      expect(inquiry.searchParams.get('branch')).toBe('main');
      expect(context.pages().length).toBe(2);
    } finally { await context.close(); }
    const failed = await fixture({ storageBlocked: true, viewport: { width: 375, height: 812 } });
    try {
      await failed.page.goto(baseURL);
      await expect(failed.page.getByRole('dialog')).toBeHidden();
      await failed.page.locator('[data-open-popup]').click();
      await failed.page.locator('[data-mobile-hide-today]').check();
      await failed.page.locator('[data-mobile-close-popup]').click();
      await expect(failed.page.locator('[data-mobile-popup-feedback]')).toContainText('저장하지 못했습니다');
      await expect(failed.page.getByRole('dialog')).toBeVisible();
      await failed.page.locator('[data-mobile-close-popup]').click();
      await expect(failed.page.getByRole('dialog')).toBeHidden();
      expect(await failed.page.evaluate(() => window.__popupOpenCalls.length)).toBe(0);
    } finally { await failed.context.close(); }
  });

  await test('Today hide persists across tabs until Korean midnight and manual reopening remains available', async () => {
    const { context, page } = await fixture({ blockAuto: false, timezoneId: 'America/New_York' });
    try {
      const popupEvent = page.waitForEvent('popup');
      await page.goto(baseURL);
      const popup = await popupEvent;
      await popup.locator('[data-hide-today]').check();
      await popup.locator('[data-close-popup]').click();
      await expect.poll(() => popup.isClosed()).toBe(true);
      const hidden = await page.evaluate(key => localStorage.getItem(key), storagePrefix + 'hide:visit-notice');
      expect(Number(hidden)).toBe(Date.parse('2026-10-10T00:00:00+09:00'));
      const second = await context.newPage();
      await second.goto(baseURL);
      await expect(second.locator('[data-popup-status]')).toContainText('오늘');
      expect(await second.evaluate(() => window.__popupOpenCalls.length)).toBe(0);
      const manualEvent = second.waitForEvent('popup');
      await second.locator('[data-open-popup]').click();
      await expect((await manualEvent).locator('[data-popup-content]')).toBeVisible();
    } finally { await context.close(); }
    const nextDay = await fixture({ blockAuto: false, now: Date.parse('2026-10-10T00:00:00+09:00'),
      seeds: { [storagePrefix + 'hide:visit-notice']: String(Date.parse('2026-10-10T00:00:00+09:00')) } });
    try {
      const popupEvent = nextDay.page.waitForEvent('popup');
      await nextDay.page.goto(baseURL);
      await expect((await popupEvent).locator('[data-popup-content]')).toBeVisible();
    } finally { await nextDay.context.close(); }
  });

  await test('Direct popup URLs enforce expired, future, disabled, unpublished, and missing-post fixture conditions', async () => {
    const { context, page } = await fixture();
    try {
      for (const state of ['expired', 'future', 'disabled', 'unpublished', 'missing-post', 'empty']) {
        await page.goto(`${baseURL}/popup.html?case=${state}`);
        await expect(page.locator('[data-popup-unavailable]')).toBeVisible();
        await expect(page.locator('[data-popup-content]')).toBeHidden();
      }
      await screenshot(page, 'popup-unavailable.png');
      await page.goto(`${baseURL}/popup.html?case=no-image`);
      await expect(page.locator('[data-popup-content]')).toBeVisible();
      await expect(page.locator('[data-popup-image-frame]')).toBeHidden();
      await page.goto(`${baseURL}/popup.html?case=image-failure`);
      await expect(page.locator('[data-popup-image-fallback]')).toBeVisible();
      await expect(page.locator('[data-popup-post]')).toBeVisible();
    } finally { await context.close(); }
  });

  await test('Popup content-loading failure is not counted as displayed; manual retry recovers the same window', async () => {
    const { context, page } = await fixture({ blockAuto: false });
    try {
      await context.route('**/popup.js', route => route.abort());
      const popupEvent = page.waitForEvent('popup');
      await page.goto(baseURL);
      const popup = await popupEvent;
      await expect(page.locator('[data-popup-status]')).toContainText('표시하지 못했습니다', { timeout: 6000 });
      expect(await page.evaluate(key => sessionStorage.getItem(key), storagePrefix + 'shown:visit-notice')).toBeNull();
      await expect(popup.locator('[data-popup-unavailable]')).toBeVisible();
      await context.unroute('**/popup.js');
      await page.locator('[data-open-popup]').click();
      await expect(popup.locator('[data-popup-content]')).toBeVisible();
      expect(context.pages().length).toBe(2);
    } finally { await context.close(); }
  });

  await test('Unavailable storage preserves manual entry and reports inability to save today hide', async () => {
    const { context, page } = await fixture({ storageBlocked: true });
    try {
      await page.goto(baseURL);
      await expect(page.locator('[data-popup-status]')).toContainText('자동 알림을 사용할 수 없습니다');
      expect(await page.evaluate(() => window.__popupOpenCalls.length)).toBe(0);
      const popupEvent = page.waitForEvent('popup');
      await page.locator('[data-open-popup]').click();
      const popup = await popupEvent;
      await popup.locator('[data-hide-today]').check();
      await popup.locator('[data-close-popup]').click();
      await expect(popup.locator('[data-popup-feedback]')).toContainText('저장하지 못했습니다');
      expect(popup.isClosed()).toBe(false);
      await popup.locator('[data-close-popup]').click();
      await expect.poll(() => popup.isClosed()).toBe(true);
    } finally { await context.close(); }
  });

  await test('Grouped branch previews stay on home; detail page groups facilities, trainers and contact', async () => {
    const { context, page } = await fixture();
    try {
      await page.goto(baseURL);
      await expect(page.getByRole('tab')).toHaveCount(2);
      await expect(page.getByRole('tabpanel')).toHaveCount(1);
      await expect(page.locator('#branch-main')).toBeVisible();
      await expect(page.locator('#branch-second')).toBeHidden();
      await expect(page.locator('#news')).toHaveCount(1);
      expect(await page.locator('#news').evaluate(element => !!element.closest('[data-branch-panel]'))).toBe(false);
      await expect(page.locator('#branch-main [data-gallery-slide]')).toHaveCount(3);
      await expect(page.locator('.trainer, .location, .branch-information')).toHaveCount(0);
      await expect(page.locator('#primary-navigation')).not.toContainText('트레이너');
      await expect(page.locator('.footer-navigation')).not.toContainText('트레이너');
      await page.getByRole('tab', { name: 'Y3GYM 예시점' }).click();
      await expect(page.locator('#branch-main')).toBeHidden();
      await expect(page.locator('#branch-second')).toBeVisible();
      await expect(page.locator('#branch-second [data-gallery-slide]')).toHaveCount(3);
      const homeContact = new URL(await page.locator('#intro-contact .button--primary').getAttribute('href'));
      expect(homeContact.pathname).toBe('/branches.html');
      expect(homeContact.searchParams.get('branch')).toBe('second');
      expect(homeContact.hash).toBe('#contact-second');
      await page.locator('#primary-navigation [data-branch-page]').first().click();
      await expect(page).toHaveURL(/branches\.html\?branch=second$/);
      await expect(page.locator('#branch-second .branch-panel-summary')).toContainText('07:00–22:00');
      await expect(page.locator('#branch-second .trainer')).toContainText('트레이너 B');
      await expect(page.locator('#contact-second')).toContainText('031-000-0002');
      await page.locator('#contact-second [data-preview-contact="카카오톡"]').click();
      await expect(page.locator('#second-contact-status')).toContainText('Y3GYM 예시점 카카오톡');
      await expect(page.locator('#primary-navigation [data-branch-jump="contact"]')).toHaveAttribute('href', '#contact-second');
      await page.getByRole('tab', { name: 'Y3GYM 본점' }).click();
      await expect(page.locator('#branch-main .trainer')).toContainText('트레이너 A');
      await page.locator('#contact-main [data-preview-contact="전화"]').click();
      await expect(page.locator('#main-contact-status')).toContainText('Y3GYM 본점 전화');
      await page.getByRole('tab', { name: 'Y3GYM 예시점' }).click();
      await verifyLayout(page, [320, 375, 768, 1440]);
      await page.setViewportSize({ width: 1440, height: 900 });
      await screenshot(page, 'two-branches-desktop.png', true);
      await screenshot(page, 'two-branches-contact-desktop.png', true, '#contact-second');
      await page.setViewportSize({ width: 375, height: 812 });
      await screenshot(page, 'two-branches-mobile.png', true);
      await screenshot(page, 'two-branches-contact-mobile.png', true, '#contact-second');
    } finally { await context.close(); }
  });

  await test('Branch facility gallery shares the approved layout on home/details, wraps, resets and supports keyboard/mobile swipes', async () => {
    const desktop = await fixture({ reducedMotion: 'reduce' });
    try {
      const { page } = desktop;
      await page.goto(baseURL);
      await expect(page.getByRole('heading', { name: '시설 둘러보기', exact: true })).toHaveCount(0);
      await expect(page.locator('section.facilities')).toHaveCount(0);
      const gallery = page.locator('#main-facilities');
      await expect(gallery.locator('[data-gallery-slide] h4')).toHaveText(['웨이트 공간', '유산소 공간', '스트레칭 공간']);
      await expect(gallery.locator('button')).toHaveCount(0);
      const initial = await gallery.locator('[data-gallery-track]').evaluate(element => element.style.transform);
      await gallery.locator('[data-gallery-viewport]').focus();
      for (const title of ['유산소 공간', '스트레칭 공간', '웨이트 공간']) {
        await page.keyboard.press('ArrowRight');
        await expect(gallery.locator('[data-gallery-status]')).toContainText(title);
      }
      expect(await gallery.locator('[data-gallery-track]').evaluate(element => element.style.transform)).toBe(initial);
      await page.keyboard.press('ArrowLeft');
      await expect(gallery.locator('[data-gallery-status]')).toContainText('스트레칭 공간');
      await expect(gallery.locator('[data-gallery-viewport]')).toBeFocused();
      await page.getByRole('tab', { name: 'Y3GYM 예시점' }).click();
      const second = page.locator('#second-facilities');
      await second.locator('[data-gallery-viewport]').focus();
      await page.keyboard.press('ArrowRight');
      await expect(second.locator('[data-gallery-status]')).toContainText('유산소 공간');
      await page.getByRole('tab', { name: 'Y3GYM 본점' }).click();
      expect(await gallery.locator('[data-gallery-track]').evaluate(element => element.style.transform)).toBe(initial);
      await page.getByRole('tab', { name: 'Y3GYM 예시점' }).click();
      await expect(second.locator('[data-gallery-status]')).toBeEmpty();
      await page.locator('.hero-actions .text-link').click();
      await expect(page).toHaveURL(/branches\.html\?branch=second$/);
      await expect(page.locator('#branch-second [data-gallery-slide]')).toHaveCount(3);
      await expect(page.locator('#branch-second [data-facility-gallery]')).toHaveClass(/is-ready/);
      const template = await readFile(path.join(directory, 'templates/home.html'), 'utf8');
      const sparse = [{ ...branches[0], facilities: branches[0].facilities.slice(0, 1) }, { ...branches[1], facilities: [] }];
      await desktop.context.route('**/preview-sparse-photos.html*', route => route.fulfill({ contentType: 'text/html', body: renderHome(template, sparse) }));
      await page.goto(baseURL + '/preview-sparse-photos.html?branch=main');
      await expect(page.locator('#main-facilities [data-gallery-slide]')).toHaveCount(1);
      await expect(page.locator('[data-gallery-clone]')).toHaveCount(0);
      await page.getByRole('tab', { name: 'Y3GYM 예시점' }).click();
      await expect(page.locator('#branch-second [data-facility-gallery]')).toHaveCount(0);
      await expect(page.locator('#branch-second')).toContainText('등록된 시설 사진이 없습니다.');
    } finally { await desktop.context.close(); }

    const mobile = await fixture({ viewport: { width: 375, height: 812 }, hasTouch: true, reducedMotion: 'reduce',
      seeds: { [storagePrefix + 'hide:visit-notice']: String(fixedNow + 60000) } });
    try {
      const { page } = mobile;
      await page.goto(baseURL + '/?branch=main');
      const frame = page.locator('#main-facilities [data-gallery-viewport]');
      await frame.scrollIntoViewIfNeeded();
      const cdp = await mobile.context.newCDPSession(page);
      async function swipe(dx, dy = 0) {
        const box = await frame.boundingBox();
        const x = box.x + box.width * (dx < 0 ? .75 : .25);
        const y = box.y + box.height * .4;
        await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] });
        for (let step = 1; step <= 6; step++) {
          await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: x + dx * step / 6, y: y + dy * step / 6 }] });
          await page.evaluate(() => new Promise(requestAnimationFrame));
        }
        await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
      }
      await swipe(-140);
      await expect(page.locator('#main-facilities [data-gallery-status]')).toContainText('유산소 공간');
      await swipe(140);
      await expect(page.locator('#main-facilities [data-gallery-status]')).toContainText('웨이트 공간');
      const scrollBefore = await page.evaluate(() => scrollY);
      await swipe(0, -100);
      await expect(page.locator('#main-facilities [data-gallery-status]')).toContainText('웨이트 공간');
      await expect.poll(() => page.evaluate(() => scrollY)).toBeGreaterThan(scrollBefore);
    } finally { await mobile.context.close(); }
  });

  await test('Branch tab keyboard navigation, URL/session restore, direct links, and same-tab announcement return', async () => {
    const { context, page } = await fixture({ storageBlocked: false });
    try {
      await page.goto(baseURL);
      const main = page.getByRole('tab', { name: 'Y3GYM 본점' });
      const second = page.getByRole('tab', { name: 'Y3GYM 예시점' });
      await main.focus();
      await page.keyboard.press('ArrowRight');
      await expect(second).toBeFocused();
      await expect(second).toHaveAttribute('aria-selected', 'true');
      await expect(main).toHaveAttribute('tabindex', '-1');
      await page.keyboard.press('Home');
      await expect(main).toBeFocused();
      await page.keyboard.press('ArrowLeft');
      await expect(second).toBeFocused();
      await page.keyboard.press('End');
      await expect(second).toBeFocused();
      await page.keyboard.press('Tab');
      await expect(page.locator('#branch-second')).toBeFocused();
      await page.reload();
      await expect(second).toHaveAttribute('aria-selected', 'true');
      await page.goto(baseURL);
      await expect(second).toHaveAttribute('aria-selected', 'true');
      await page.goto(baseURL + '/branches.html?branch=second#contact-main');
      await expect(main).toHaveAttribute('aria-selected', 'true');
      await expect(page.locator('#contact-main')).toBeVisible();
      await page.goto(baseURL + '/?branch=missing');
      await expect(main).toHaveAttribute('aria-selected', 'true');
      await second.click();
      const popupEvent = page.waitForEvent('popup');
      await page.locator('[data-open-popup]').click();
      const popup = await popupEvent;
      await popup.locator('[data-popup-post]').click();
      expect(new URL(popup.url()).searchParams.get('branch')).toBe('second');
      await popup.locator('.menu-toggle').click();
      await popup.locator('#primary-navigation .header-contact').click();
      await expect(popup.getByRole('tab', { name: 'Y3GYM 예시점' })).toHaveAttribute('aria-selected', 'true');
      await popup.close();
      await page.locator('.news-title-link[href*="visit.html"]').click();
      expect(new URL(page.url()).searchParams.get('branch')).toBe('second');
      await page.locator('#primary-navigation .header-contact').click();
      await expect(second).toHaveAttribute('aria-selected', 'true');
      await expect(page.locator('#contact-second')).toBeInViewport();
      await page.locator('.site-header .wordmark').click();
      await page.setViewportSize({ width: 375, height: 812 });
      await page.locator('[data-open-popup]').click();
      await page.locator('[data-mobile-popup-post]').click();
      expect(new URL(page.url()).searchParams.get('branch')).toBe('second');
      await page.locator('.menu-toggle').click();
      await page.locator('#primary-navigation .header-contact').click();
      await expect(second).toHaveAttribute('aria-selected', 'true');
      expect(context.pages().length).toBe(1);
    } finally { await context.close(); }
  });

  await test('Branch data expansion creates all tabs/panels and keeps many mobile tabs within horizontal scrolling', async () => {
    const { context, page } = await fixture({ storageBlocked: true });
    try {
      const expanded = [...branches, ...Array.from({ length: 5 }, (_, index) => ({
        ...branches[1], id: 'extra-' + index, name: 'Y3GYM 추가 지점 ' + index + ' · 긴 지점명 검수용 예시',
        label: '추가 지점 ' + index,
      }))];
      const template = await readFile(path.join(directory, 'templates/home.html'), 'utf8');
      await context.route('**/preview-many-branches.html*', route => route.fulfill({ contentType: 'text/html', body: renderHome(template, expanded) }));
      await page.goto(baseURL + '/preview-many-branches.html');
      await expect(page.getByRole('tab')).toHaveCount(7);
      await expect(page.locator('[data-branch-panel]')).toHaveCount(7);
      await expect(page.getByRole('tabpanel')).toHaveCount(1);
      await page.setViewportSize({ width: 375, height: 812 });
      await page.getByRole('tab').first().focus();
      await page.keyboard.press('End');
      const last = page.getByRole('tab').last();
      await expect(last).toBeFocused();
      await expect(last).toBeInViewport();
      await expect(page.locator('#branch-extra-4')).toBeVisible();
      await expect(page.locator('#branch-extra-4 .text-link').first()).toHaveAttribute('href', 'branches.html?branch=extra-4');
      const detailTemplate = await readFile(path.join(directory, 'templates/branches.html'), 'utf8');
      await context.route('**/branches.html*', route => route.fulfill({ contentType: 'text/html', body: renderDetails(detailTemplate, expanded) }));
      await page.locator('#branch-extra-4 .text-link').first().click();
      await expect(page.getByRole('tab')).toHaveCount(7);
      await expect(page.locator('#contact-extra-4')).toContainText('추가 지점 4');
      const size = await page.locator('[data-branch-tabs]').evaluate(element => ({ scroll: element.scrollWidth, width: element.clientWidth }));
      expect(size.scroll).toBeGreaterThan(size.width);
      await verifyLayout(page, [320, 375, 768, 1440]);
    } finally { await context.close(); }
  });

  await test('Empty optional data hides photo/trainer blocks, shows news empty state, and preserves core inquiry', async () => {
    const { context, page } = await fixture();
    try {
      await page.goto(`${baseURL}/preview-empty.html`);
      await expect(page.locator('.facilities, .trainers, .hero-figure')).toHaveCount(0);
      await expect(page.locator('.news-item')).toHaveCount(0);
      await expect(page.locator('.empty-message')).toHaveText('등록된 소식이 없습니다.');
      expect(await page.evaluate(() => window.__popupOpenCalls.length)).toBe(0);
      await page.getByRole('tab', { name: 'Y3GYM 예시점' }).click();
      await page.locator('#branch-second .text-link').click();
      await expect(page).toHaveURL(/branches-empty\.html\?branch=second$/);
      await expect(page.locator('.facilities, .trainers')).toHaveCount(0);
      await page.locator('#contact-second [data-preview-contact="전화"]').click();
      await expect(page.locator('#second-contact-status')).toContainText('Y3GYM 예시점 전화');
      await expect(page.locator('#contact-main')).toContainText('Y3GYM 본점');
      await verifyLayout(page, [320, 375, 768, 1440]);
      await page.setViewportSize({ width: 1440, height: 900 });
      await screenshot(page, 'empty-desktop.png', true);
      await page.setViewportSize({ width: 375, height: 812 });
      await screenshot(page, 'empty-mobile.png', true);
    } finally { await context.close(); }
  });

  await test('Failed photographs and simulated unavailable map keep content, address, and inquiry readable', async () => {
    const { context, page } = await fixture();
    try {
      await page.goto(`${baseURL}/preview-failures.html`);
      await readyImages(page);
      await expect(page.locator('.image-fallback:visible:not([data-gallery-clone] *)')).toHaveCount(2);
      await expect(page.locator('.location')).toHaveCount(0);
      await page.locator('#branch-main .text-link').click();
      await expect(page).toHaveURL(/branches-failures\.html\?branch=main$/);
      await readyImages(page);
      await expect(page.locator('.image-fallback:visible:not([data-gallery-clone] *)')).toHaveCount(2);
      await expect(page.locator('.map-placeholder').first()).toContainText('지도를 표시할 수 없습니다');
      await expect(page.locator('.map-placeholder').last()).toContainText('지도를 표시할 수 없습니다');
      await expect(page.locator('#contact-main .location-details')).toContainText('서울 ○○구 ○○로 00');
      await expect(page.locator('#contact-second .location-details')).toContainText('경기 ○○시 ○○로 00');
      await verifyLayout(page, [320, 375, 768, 1440]);
      await page.setViewportSize({ width: 1440, height: 900 });
      await screenshot(page, 'failures-desktop.png', true);
      await page.setViewportSize({ width: 375, height: 812 });
      await screenshot(page, 'failures-mobile.png', true);
    } finally { await context.close(); }
  });

  await test('Blocked app script and disabled JavaScript retain mobile menu, content, addresses, and branch contact text', async () => {
    const partial = await fixture({ viewport: { width: 375, height: 812 }, seeds: { [storagePrefix + 'hide:visit-notice']: String(fixedNow + 60000) } });
    try {
      await partial.context.route('**/app.js', route => route.abort());
      await partial.page.goto(baseURL);
      await expect(partial.page.locator('#primary-navigation')).toBeVisible();
      await partial.page.locator('#primary-navigation .header-contact').click();
      expect(new URL(partial.page.url()).pathname).toBe('/branches.html');
      await expect(partial.page.locator('#contact-second .location-details')).toContainText('연락처');
      await expect(partial.page.locator('[data-branch-panel]:visible')).toHaveCount(2);
    } finally { await partial.context.close(); }
    const noJS = await fixture({ javaScriptEnabled: false, viewport: { width: 375, height: 812 } });
    try {
      await noJS.page.goto(`${baseURL}/preview-two-branches.html`);
      await expect(noJS.page.locator('#primary-navigation')).toBeVisible();
      await expect(noJS.page.locator('[data-gallery-slide]:visible')).toHaveCount(6);
      await expect(noJS.page.locator('[data-facility-gallery] button:visible')).toHaveCount(0);
      await noJS.page.locator('#primary-navigation [data-branch-page]').first().click();
      await expect(noJS.page).toHaveURL(/branches\.html$/);
      await expect(noJS.page.locator('#contact-main')).toContainText('02-0000-0001');
      await expect(noJS.page.locator('#contact-second')).toContainText('031-000-0002');
      await noJS.page.locator('[data-branch-tab][href="#branch-second"]').click();
      expect(new URL(noJS.page.url()).hash).toBe('#branch-second');
      await expect(noJS.page.locator('[data-branch-panel]:visible')).toHaveCount(2);
      await screenshot(noJS.page, 'javascript-disabled-mobile.png', true);
      await noJS.page.locator('.site-header .wordmark').click();
      await noJS.page.locator('[data-open-popup]').click();
      await expect(noJS.page).toHaveURL(/news\/visit\.html$/);
      expect(noJS.context.pages().length).toBe(1);
      await noJS.page.goto(`${baseURL}/popup.html`);
      await expect(noJS.page.locator('[data-popup-unavailable]')).toBeVisible();
      await expect(noJS.page.getByRole('link', { name: '홈 소식 보기' })).toBeVisible();
    } finally { await noJS.context.close(); }
  });

  await test('No unexpected script or resource failures outside deliberately broken fixtures', async () => {
    expect(browserErrors).toEqual([]);
    const unexpected = resourceFailures.filter(item => !/missing-[^/]+\.png|\/popup\.js$|\/app\.js$/.test(item.url));
    expect(unexpected).toEqual([]);
  });
} finally {
  await browser.close();
  const report = {
    reviewedAt: new Date().toISOString(), browser: 'Chromium',
    fixedFixtureClock: new Date(fixedNow).toISOString(),
    homeDesignApproval: 'APPROVED — previous home',
    popupDesignApproval: 'APPROVED — user: 팝업창은 일단 이정도면 될 것 같음',
    branchTabDesignApproval: 'APPROVED — user: 배치 합격',
    pageSeparationVisualApproval: 'APPROVED — user: ㅇㅋ 이대로 가자',
    facilityCarouselVisualApproval: 'APPROVED — user: 시설슬라이드 통과',
    scope: branchOnly ? 'Unified branch/facility carousel, separate details, data expansion, navigation, empty/failure/no-JS states' : popupOnly ? 'Desktop popup and mobile layer behavior' : 'Default two-branch home, desktop popup, mobile layer, empty content, and failure cases',
    status: tests.every(item => item.status === 'PASS') ? 'PASS' : 'FAIL',
    tests, skipped, browserErrors, resourceFailures,
    limitations: ['No backend publication/access controls', 'No real map, telephone, or KakaoTalk integration',
      'No physical device or other-browser verification', 'State screenshots still require user visual review'],
  };
  await writeFile(path.join(output, branchOnly ? 'branch-slide-checks.json' : popupOnly ? 'popup-refinement-checks.json' : 'checks.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ status: report.status, passed: tests.filter(item => item.status === 'PASS').length, total: tests.length }));
}
