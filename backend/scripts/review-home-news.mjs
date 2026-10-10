import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '../../prototype/node_modules/@playwright/test/index.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const readOnly = process.argv.includes('--live-read-only');
const origin = readOnly ? 'http://localhost:8768' : process.env.Y3GYM_HOME_NEWS_ORIGIN;
assert(origin && new URL(origin).hostname === 'localhost' && (readOnly || !['8767', '8768'].includes(new URL(origin).port)), 'Writes require an isolated test server.');
const output = path.resolve(root, process.env.Y3GYM_HOME_NEWS_REVIEW_DIR || (readOnly ? 'review/home-news/live' : 'review/home-news/browser'), 'home');
await fs.mkdir(output, { recursive: true });
assert(!(await fs.readdir(output)).includes('checks.json'), 'Use a new evidence directory for each run.');
const report = { origin, readOnly, isolatedTestDatabase: !readOnly, status: 'RUNNING', checks: [], errors: [], screenshots: [] };
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const html = await (await context.request.get(origin)).text();
const popupIds = JSON.parse(html.match(/<script[^>]*id="home-popup-data"[^>]*>([\s\S]*?)<\/script>/)?.[1] || '[]').map(item => item.id);
await context.addInitScript(({ ids, origin }) => {
  if (location.origin !== origin) return;
  for (const id of ids) localStorage.setItem(`y3gym.prototype.hide:${id}`, String(Date.now() + 3600000));
}, { ids: popupIds, origin });
context.on('page', page => page.on('pageerror', error => report.errors.push(error.message)));
const page = await context.newPage();
page.setDefaultTimeout(12000);
const check = (name, detail) => { report.checks.push({ name, detail, result: 'PASS' }); console.log(`PASS ${name}`); };
async function settled() {
  await page.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.images].map(image => { image.loading = 'eager'; return image.decode().catch(() => {}); })); });
}
async function capture(name) {
  await settled();
  await page.screenshot({ path: path.join(output, `${name}-full.png`), fullPage: true });
  await page.locator('#news').screenshot({ path: path.join(output, `${name}-news.png`) });
  report.screenshots.push(`${name}-full.png`, `${name}-news.png`);
}
async function rows() {
  return page.locator('#news .news-title-link').evaluateAll(links => links.map(link => ({ id: Number(new URL(link.href).pathname.split('/')[2]), title: link.textContent, href: link.href })));
}
async function branch(key) {
  await page.waitForFunction(key => new URL(location.href).searchParams.get('branch') === key, key);
  assert.equal(await page.locator('[data-branch-panel]:not([hidden])').getAttribute('data-branch-id'), key);
  for (const href of await page.locator('#news .news-title-link, #news .section-heading > a').evaluateAll(links => links.map(link => link.href))) {
    assert.deepEqual(new URL(href).searchParams.getAll('branch'), [key]);
  }
}
try {
  await page.goto(`${origin}/news/?branch=second`);
  const expected = readOnly
    ? await page.locator('.news-title-link').evaluateAll(links => links.slice(0, 5).map(link => ({ id: Number(new URL(link.href).pathname.split('/')[2]), title: link.textContent })))
    : JSON.parse(process.env.Y3GYM_HOME_NEWS_POSTS).slice(0, 5);
  const expectedIds = expected.map(post => post.id);
  for (const [name, viewport] of [['desktop', { width: 1440, height: 900 }], ['mobile', { width: 375, height: 812 }]]) {
    await page.setViewportSize(viewport);
    await page.goto(`${origin}/?branch=second`);
    await branch('second');
    assert.deepEqual((await rows()).map(row => row.id), expectedIds);
    assert.deepEqual((await rows()).map(row => row.title), expected.map(post => post.title));
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), viewport.width);
    assert(!(await page.locator('#news').innerText()).includes('날짜 예시'));
    assert(!(await page.locator('#news').innerText()).includes('비공개 수정 초안'));
    const geometry = await page.locator('#news .news-item').evaluateAll(items => items.map(item => {
      const style = getComputedStyle(item), title = getComputedStyle(item.querySelector('h3'));
      return { padding: style.paddingTop, border: style.borderBottomWidth, titleSize: title.fontSize, font: title.fontFamily, titleWeight: title.fontWeight, columns: style.gridTemplateColumns, category: getComputedStyle(item.querySelector('.news-category')).color };
    }));
    for (const row of geometry) { assert.equal(row.padding, name === 'desktop' ? '10px' : '8px'); assert.equal(row.border, '1px'); assert.equal(row.titleSize, name === 'desktop' ? '18px' : '16px'); }
    await capture(`${name}-${readOnly ? 'actual' : 'five'}`);
    check(`${name}: 공개 목록과 같은 최근 글·최대 5건·A 행 간격/글꼴·넘침 없음`, { count: expectedIds.length, ids: expectedIds, geometry });
    if (name === 'mobile' && expected.length) {
      const last = page.locator('#news .news-item').last();
      await last.evaluate(element => element.scrollIntoView({ block: 'center' }));
      const readability = await page.evaluate(() => {
        const row = [...document.querySelectorAll('#news .news-item')].at(-1);
        const link = row.querySelector('h3 a');
        const title = link.getClientRects()[0];
        const copy = (row.querySelector('.news-copy p') || link).getBoundingClientRect();
        const bar = document.querySelector('.mobile-contact-bar').getBoundingClientRect();
        const hit = document.elementFromPoint(title.x + title.width / 2, title.y + title.height / 2);
        return { viewport: [innerWidth, innerHeight], titleTop: title.top, copyBottom: copy.bottom, contactTop: bar.top, titleReceivesClick: hit === link || link.contains(hit), scrollY, documentHeight: document.documentElement.scrollHeight };
      });
      assert.deepEqual(readability.viewport, [375, 812]);
      assert(readability.titleTop >= 0 && readability.copyBottom < readability.contactTop);
      assert.equal(readability.titleReceivesClick, true);
      const file = `mobile-${readOnly ? 'actual' : 'five'}-last-row-visible.png`;
      await page.screenshot({ path: path.join(output, file) });
      report.screenshots.push(file);
      await last.locator('h3 a').click();
      assert.equal(await page.locator('#post-title').innerText(), expected.at(-1).title);
      assert.equal(new URL(page.url()).pathname, `/news/${expected.at(-1).id}/`);
      await page.locator('.breadcrumb a').first().click();
      await branch('second');
      check('375×812: 마지막 제목·요약이 문의 바 위에서 읽히고 실제 상세로 클릭됨', readability);
      await settled();
      const height = await page.evaluate(() => Math.max(812, document.documentElement.scrollHeight));
      await page.setViewportSize({ width: 375, height });
      await page.evaluate(() => scrollTo(0, 0));
      assert(await page.locator('#news .news-item').last().evaluate(row => row.getBoundingClientRect().bottom < document.querySelector('.mobile-contact-bar').getBoundingClientRect().top));
      const sectionFile = `mobile-${readOnly ? 'actual' : 'five'}-news-unobscured.png`;
      await page.locator('#news').screenshot({ path: path.join(output, sectionFile) });
      report.screenshots.push(sectionFile);
      check('긴 모바일 viewport의 5건 전체 구역 캡처: 고정 문의 바와 행 비중첩', { width: 375, height, screenshot: sectionFile });
      await page.setViewportSize({ width: 375, height: 812 });
    }
  }
  await page.getByRole('tab', { name: 'Y3GYM 본점', exact: true }).click();
  await branch('main');
  assert.deepEqual((await rows()).map(row => row.id), expectedIds);
  await page.getByRole('tab', { name: 'Y3GYM 예시점', exact: true }).click();
  await branch('second');
  await page.reload();
  await branch('second');
  check('본점↔예시점 전환·새로고침·공통 소식 동일·branch 중복 없음');
  if (expected.length) {
    await page.locator('#news .news-title-link').first().click();
    assert.equal(new URL(page.url()).pathname, `/news/${expected[0].id}/`);
    assert.equal(new URL(page.url()).searchParams.get('branch'), 'second');
    assert.equal(await page.locator('#post-title').innerText(), expected[0].title);
    await page.locator('.breadcrumb [data-news-return]').click();
    assert.equal(new URL(page.url()).searchParams.get('category'), 'all');
    assert.equal(new URL(page.url()).searchParams.get('page'), '1');
    await page.locator('.breadcrumb a').first().click();
    await branch('second');
    await page.locator('#news .section-heading > a').click();
    assert.equal(new URL(page.url()).pathname, '/news/');
    assert.equal(new URL(page.url()).searchParams.get('branch'), 'second');
    await page.goBack();
    await branch('second');
    check('실제 글 상세→목록 기본 all/1→홈·모두 보기·뒤로가기 지점 유지');
  }
  const noScript = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 375, height: 812 } });
  const fallback = await noScript.newPage();
  await fallback.goto(`${origin}/?branch=second`);
  const hrefs = await fallback.locator('#news .news-title-link, #news .section-heading > a').evaluateAll(links => links.map(link => link.getAttribute('href')));
  for (const href of hrefs) assert.deepEqual(new URL(href, origin).searchParams.getAll('branch'), ['second']);
  if (expected.length) {
    await fallback.locator('#news .news-title-link').first().click();
    assert.equal(await fallback.locator('#post-title').innerText(), expected[0].title);
    assert.equal(new URL(fallback.url()).searchParams.get('branch'), 'second');
    await fallback.locator('.breadcrumb a').first().click();
  }
  await fallback.locator('#news .section-heading > a').click();
  assert.equal(new URL(fallback.url()).pathname, '/news/');
  assert.equal(new URL(fallback.url()).searchParams.get('branch'), 'second');
  await noScript.close();
  check('JavaScript 없는 모바일: 서버 상세·모두 보기·홈 왕복 링크 유효', hrefs);
  if (!readOnly) {
    const editor = await context.newPage();
    await editor.goto(`${origin}/admin/login/`);
    await editor.locator('[name="username"]').fill('cms-review-editor');
    await editor.locator('[name="password"]').fill(process.env.Y3GYM_HOME_NEWS_PASSWORD);
    await editor.locator('button[type="submit"]').click();
    for (const post of JSON.parse(process.env.Y3GYM_HOME_NEWS_POSTS)) {
      await editor.goto(`${origin}/admin/snippets/news/post/unpublish/${post.id}/`);
      await Promise.all([editor.waitForNavigation(), editor.locator('form[action*="/unpublish/"] button[type="submit"], form[action*="/unpublish/"] input[type="submit"]').click()]);
    }
    for (const [name, viewport] of [['desktop', { width: 1440, height: 900 }], ['mobile', { width: 375, height: 812 }]]) {
      await page.setViewportSize(viewport);
      await page.goto(`${origin}/?branch=second`);
      assert.equal(await page.locator('#news .news-item').count(), 0);
      assert.equal(await page.locator('#news .news-empty-state h2').innerText(), '등록된 소식이 없습니다.');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth), viewport.width);
      await capture(`${name}-empty`);
    }
    const detail = await context.request.get(`${origin}/news/${expected[0].id}/`);
    assert.equal(detail.status(), 404);
    check('실제 관리자 철회 후 PC·모바일 0건 안내·예시 행 제거·상세 404');
  }
  assert.deepEqual(report.errors, []);
  report.status = 'PASS';
} catch (error) {
  report.status = 'FAIL'; report.failure = error.stack || error.message; process.exitCode = 1;
  await page.screenshot({ path: path.join(output, 'failure.png'), fullPage: true }).catch(() => {});
} finally {
  await browser.close();
  await fs.writeFile(path.join(output, 'checks.json'), `${JSON.stringify(report, null, 2)}\n`, { flag: 'wx' });
  console.log(JSON.stringify({ status: report.status, checks: report.checks.length, failure: report.failure }));
}
