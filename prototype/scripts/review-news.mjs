import { chromium, expect } from '@playwright/test';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { newsPosts, newsPageSize } from '../news-data.js';
import { renderNewsPage, renderPostPage, publicNews } from './render-news.mjs';

const directory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const output = path.join(directory, 'review', 'news');
const baseURL = process.env.PROTOTYPE_URL || 'http://127.0.0.1:8767';
await mkdir(output, { recursive: true });
const browser = await chromium.launch();
const errors = [];
const report = { reviewedAt: new Date().toISOString(), browser: 'Chromium', designApproval: 'LIST_APPROVED — user: 글 목록 통과; detail reflects requested action removal',
  scope: 'Shared news list, categories, static pagination, post reading and return, branch context, empty and no-JS states',
  tests: [], widths: [], captures: [] };

async function fixture(options = {}) {
  const context = await browser.newContext({ viewport: options.viewport || { width: 1440, height: 900 },
    javaScriptEnabled: options.javaScriptEnabled !== false, locale: 'ko-KR', timezoneId: 'Asia/Seoul' });
  await context.addInitScript(() => {
    if (location.protocol === 'http:') sessionStorage.setItem('y3gym.prototype.auto-attempt', '1');
  });
  context.on('page', page => {
    page.on('pageerror', error => errors.push(error.message));
    page.on('response', response => { if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
  });
  return { context, page: await context.newPage() };
}
async function test(name, action) {
  try { await action(); report.tests.push({ name, status: 'PASS' }); }
  catch (error) { report.tests.push({ name, status: 'FAIL', error: error.stack || String(error) }); process.exitCode = 1; }
  console.log(`${report.tests.at(-1).status}: ${name}`);
}
async function ready(page) { await page.evaluate(() => document.fonts.ready); }
async function capture(page, name, full = false) {
  await ready(page);
  const viewport = page.viewportSize();
  await page.evaluate(() => window.scrollTo(0, 0));
  if (full) await page.setViewportSize({ width: viewport.width, height: await page.evaluate(() => document.documentElement.scrollHeight) });
  await page.screenshot({ path: path.join(output, name), animations: 'disabled' });
  report.captures.push({ name, viewport: page.viewportSize(), full });
  if (full) await page.setViewportSize(viewport);
}

try {
  await test('List and post layouts at six widths, images/fonts, menu, footer and contact bar remain readable', async () => {
    const { context, page } = await fixture();
    try {
      for (const width of [320, 375, 768, 1024, 1280, 1440]) {
        await page.setViewportSize({ width, height: width < 768 ? 812 : 900 });
        for (const [name, route] of [['list', '/news.html?branch=second'], ['notice', '/news/visit.html?branch=second'], ['event', '/news/event.html?branch=second'], ['empty', '/news-empty.html?branch=second']]) {
          await page.goto(baseURL + route);
          await ready(page);
          const metrics = await page.evaluate(() => ({
            width: innerWidth, content: document.documentElement.scrollWidth,
            h1Count: document.querySelectorAll('h1').length,
            fontLoaded: [...document.fonts].some(font => font.family === 'Pretendard' && font.status === 'loaded'),
            ids: [...document.querySelectorAll('[id]')].map(element => element.id),
            overflowingControls: [...document.querySelectorAll('.button, .news-filter')].filter(element =>
              element.getClientRects().length && element.scrollWidth > element.clientWidth + 1).map(element => element.textContent.trim()),
          }));
          expect(metrics.content).toBeLessThanOrEqual(width + 1);
          expect(metrics.h1Count).toBe(1);
          expect(metrics.fontLoaded).toBe(true);
          expect(new Set(metrics.ids).size).toBe(metrics.ids.length);
          expect(metrics.overflowingControls).toEqual([]);
          await expect(page.locator('.footer-navigation a')).toHaveText(['지점 안내', '소식']);
          if (width < 768) {
            await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
            expect(await page.evaluate(() => document.querySelector('.footer-note').getBoundingClientRect().bottom <=
              document.querySelector('.mobile-contact-bar').getBoundingClientRect().top)).toBe(true);
          }
          report.widths.push({ name, width, ...metrics, status: 'PASS' });
          if (width === 375 || width === 1440) {
            const device = width === 375 ? 'mobile' : 'desktop';
            await capture(page, `${name}-${device}-first.png`);
            await capture(page, `${name}-${device}-full.png`, true);
          }
        }
      }
    } finally { await context.close(); }
  });

  await test('All/notice/event filters, event detail and return preserve category and selected branch', async () => {
    const { context, page } = await fixture();
    try {
      await page.goto(baseURL + '/news.html?branch=second');
      await expect(page.locator('.news-title-link')).toHaveText(['방문 전 확인해주세요', '이벤트 소식 안내']);
      await expect(page.locator('.news-pagination')).toHaveCount(0);
      await page.locator('.news-filter').filter({ hasText: '공지' }).click();
      await expect(page.locator('.news-title-link')).toHaveCount(1);
      await expect(page.locator('.news-filter[aria-current="page"]')).toHaveText('공지');
      await page.locator('.news-filter').filter({ hasText: '이벤트' }).click();
      await expect(page.locator('.news-title-link')).toHaveText('이벤트 소식 안내');
      await page.locator('.news-title-link').click();
      await expect(page.locator('h1')).toHaveText('이벤트 소식 안내');
      await expect(page.locator('.post-body')).toContainText('이벤트 예시');
      await expect(page.locator('.post-body strong')).toBeVisible();
      await expect(page.locator('.post-actions')).toHaveCount(0);
      await expect(page.getByRole('link', { name: '지점 위치와 문의 보기' })).toHaveCount(0);
      await page.locator('.breadcrumb [data-news-return]').click();
      await expect(page).toHaveURL(/news-events\.html\?branch=second$/);
      await page.setViewportSize({ width: 375, height: 812 });
      await page.locator('.menu-toggle').click();
      await expect(page.locator('#primary-navigation')).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(page.locator('.menu-toggle')).toBeFocused();
      await page.locator('.mobile-contact-bar .button--primary').click();
      await expect(page.getByRole('tab', { name: 'Y3GYM 예시점' })).toHaveAttribute('aria-selected', 'true');
      await expect(page.locator('#contact-second')).toBeInViewport();
      for (const branch of ['main', 'second']) {
        await page.goto(baseURL + '/news.html?branch=' + branch);
        await expect(page.locator('.news-title-link')).toHaveText(['방문 전 확인해주세요', '이벤트 소식 안내']);
      }
    } finally { await context.close(); }
  });

  await test('Home and branch-page menus and home previews enter news with the selected branch', async () => {
    const { context, page } = await fixture();
    try {
      for (const route of ['/?branch=second', '/branches.html?branch=second']) {
        await page.goto(baseURL + route);
        await page.locator('#primary-navigation a').filter({ hasText: '소식' }).click();
        await expect(page).toHaveURL(/news\.html\?branch=second$/);
      }
      await page.goto(baseURL + '/?branch=second');
      await page.getByRole('link', { name: '소식 모두 보기' }).click();
      await expect(page).toHaveURL(/news\.html\?branch=second$/);
      await page.locator('.site-header .wordmark').click();
      await page.locator('.news-title-link[href*="event.html"]').click();
      await expect(page).toHaveURL(/news\/event\.html\?branch=second$/);
    } finally { await context.close(); }
  });

  await test('Empty lists keep categories and basic navigation; direct posts recover from unknown return context', async () => {
    const { context, page } = await fixture();
    try {
      await page.goto(baseURL + '/news-empty.html?branch=second');
      await expect(page.locator('.news-item')).toHaveCount(0);
      await expect(page.locator('.news-empty-state h2')).toHaveText('등록된 소식이 없습니다.');
      await page.locator('.news-filter').filter({ hasText: '이벤트' }).click();
      await expect(page.locator('.news-empty-state h2')).toHaveText('등록된 이벤트가 없습니다.');
      await expect(page.locator('.news-pagination')).toHaveCount(0);
      await page.goto(baseURL + '/preview-empty.html?branch=second');
      await page.locator('#primary-navigation a').filter({ hasText: '소식' }).click();
      await expect(page).toHaveURL(/news-empty\.html\?branch=second$/);
      await expect(page.locator('.news-item')).toHaveCount(0);
      await page.goto(baseURL + '/news/visit.html?branch=second&category=invalid&listPage=999');
      await page.locator('.breadcrumb [data-news-return]').click();
      await expect(page).toHaveURL(/news\.html\?branch=second$/);
      const isolated = await context.newPage();
      await isolated.goto(baseURL + '/news.html?branch=unknown');
      await expect(isolated.locator('.mobile-contact-bar')).toHaveAttribute('aria-label', '문의할 지점 선택');
      const contact = new URL(await isolated.locator('#primary-navigation .header-contact').getAttribute('href'));
      expect(contact.hash).toBe('#branch');
      expect(contact.searchParams.has('branch')).toBe(false);
    } finally { await context.close(); }
  });

  await test('Expanded fixture paginates 23 public examples without exposing an unpublished record and restores page after reading', async () => {
    const { context, page } = await fixture({ viewport: { width: 375, height: 812 } });
    try {
      const template = await readFile(path.join(directory, 'templates/content.html'), 'utf8');
      const expanded = [...newsPosts, ...Array.from({ length: 21 }, (_, index) => ({ ...newsPosts[0], id: `sample-${index}`, title: `검수용 추가 소식 ${index} · 긴 제목의 줄바꿈을 확인하는 임시 예시` }))];
      const records = [...expanded, { ...newsPosts[0], id: 'unpublished', published: false, title: '비공개 검수 표식' }];
      await context.route('**/news-data.js', route => route.fulfill({ contentType: 'text/javascript', body: `export const newsPageSize=${newsPageSize}; export const newsPosts=${JSON.stringify(expanded)};` }));
      await context.route('**/*.html*', route => {
        const url = new URL(route.request().url());
        const match = url.pathname.match(/^\/news(?:-(notices|events))?(?:-page-(\d+))?\.html$/);
        if (match) return route.fulfill({ contentType: 'text/html', body: renderNewsPage(template, records, { category: match[1] || 'all', page: Number(match[2] || 1) }) });
        const post = publicNews(records).find(item => url.pathname === `/news/${item.id}.html`);
        if (post) return route.fulfill({ contentType: 'text/html', body: renderPostPage(template, post) });
        return route.continue();
      });
      await page.goto(baseURL + '/news.html?branch=second');
      await expect(page.locator('.news-item')).toHaveCount(10);
      await expect(page.locator('main')).not.toContainText('비공개 검수 표식');
      await page.getByRole('link', { name: '2페이지', exact: true }).click();
      await expect(page.locator('.news-item')).toHaveCount(10);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
      await page.locator('.news-title-link').first().click();
      await page.locator('.breadcrumb [data-news-return]').click();
      await expect(page).toHaveURL(/news-page-2\.html\?branch=second$/);
      await page.getByRole('link', { name: '3페이지', exact: true }).click();
      await expect(page.locator('.news-item')).toHaveCount(3);
      await capture(page, 'pagination-mobile.png', true);
    } finally { await context.close(); }
  });

  await test('Disabled JavaScript retains filters, post reading, menu, footer and branch information links', async () => {
    const { context, page } = await fixture({ javaScriptEnabled: false, viewport: { width: 375, height: 812 } });
    try {
      await page.goto(baseURL + '/news.html');
      await expect(page.locator('#primary-navigation')).toBeVisible();
      await page.locator('.news-filter').filter({ hasText: '공지' }).click();
      await expect(page.locator('.news-title-link')).toHaveCount(1);
      await page.locator('.news-title-link').click();
      await expect(page.locator('.post-body')).toContainText('위치와 운영시간');
      await page.locator('.breadcrumb [data-news-return]').click();
      await expect(page).toHaveURL(/news\.html$/);
      await page.locator('#primary-navigation a').filter({ hasText: '지점 안내' }).click();
      await expect(page.locator('#contact-main')).toContainText('02-0000-0001');
      await expect(page.locator('#contact-second')).toContainText('031-000-0002');
      expect(context.pages().length).toBe(1);
    } finally { await context.close(); }
  });

  await test('No unexpected script or resource errors in news review', async () => { expect(errors).toEqual([]); });
} finally {
  report.status = report.tests.every(test => test.status === 'PASS') ? 'PASS' : 'FAIL';
  report.errors = errors;
  report.limitations = ['List visually approved by user; detail reflects requested removal without separate explicit approval', 'Static public examples, not backend publication or access controls', 'No administration, real inquiries/maps, physical-device or other-browser verification'];
  await browser.close();
  await writeFile(path.join(output, 'checks.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ status: report.status, groups: report.tests.length, widths: report.widths.length, captures: report.captures.length }));
}
