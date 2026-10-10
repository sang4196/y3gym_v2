import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '../../prototype/node_modules/@playwright/test/index.mjs';

// Invoke through the opt-in StaticLiveServerTestCase. Never mutate the running
// local CMS singleton or use its private credentials for this write review.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const liveReadOnly = process.argv.includes('--live-read-only');
const origin = liveReadOnly ? 'http://localhost:8768' : process.env.Y3GYM_BRAND_REVIEW_ORIGIN;
assert(origin && new URL(origin).hostname === 'localhost' && (liveReadOnly || !['8767', '8768'].includes(new URL(origin).port)), 'Writes require a temporary Django test-server origin.');
const password = liveReadOnly ? JSON.parse(await fs.readFile(path.join(root, '.local-credentials'), 'utf8'))['cms-review-editor'] : process.env.Y3GYM_BRAND_REVIEW_PASSWORD;
assert(password, 'Local review account required.');
const output = path.resolve(root, process.env.Y3GYM_BRAND_REVIEW_DIR || (liveReadOnly ? 'review/brand-home/live' : 'review/brand-home'));
await fs.mkdir(output, { recursive: true });
const report = { run: new Date().toISOString(), origin, isolatedTestDatabase: !liveReadOnly, liveReadOnly, status: 'RUNNING', checks: [], errors: [], screenshots: [] };
const browser = await chromium.launch();
const editorContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const publicContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
if (liveReadOnly) {
  const html = await (await publicContext.request.get(origin)).text();
  const payload = html.match(/<script[^>]*id="home-popup-data"[^>]*>([\s\S]*?)<\/script>/);
  const ids = JSON.parse(payload?.[1] || '[]').map(popup => popup.id);
  await publicContext.addInitScript(({ ids, origin }) => {
    if (location.origin !== origin) return;
    for (const id of ids) localStorage.setItem(`y3gym.prototype.hide:${id}`, String(Date.now() + 3600000));
  }, { ids, origin });
  report.popupIdsHiddenOnlyInIsolatedBrowserContext = ids;
}
for (const context of [editorContext, publicContext]) context.on('page', page => page.on('pageerror', error => report.errors.push({ url: page.url(), message: error.message })));
const editor = await editorContext.newPage();
const visitor = await publicContext.newPage();
editor.setDefaultTimeout(12000);
visitor.setDefaultTimeout(12000);
const editUrl = `${origin}/admin/snippets/news/brandcontent/edit/1/`;
let originalTitle = '운동할 공간을\n먼저 둘러보세요.';
const draftTitle = '[TEST] 저장한 소개 초안';
const check = (name, detail) => { report.checks.push({ name, detail, result: 'PASS' }); console.log(`PASS ${name}`); };
async function settle(page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].map(image => {
      image.loading = 'eager';
      return image.decode().catch(() => {});
    }));
  });
}
async function capture(page, name, fullPage = false) {
  await settle(page);
  const file = `${name}.png`;
  await page.screenshot({ path: path.join(output, file), fullPage });
  report.screenshots.push(file);
}
async function reopen() { await editor.goto(editUrl); await editor.locator('#id_name').waitFor(); }
async function draft() {
  await Promise.all([editor.waitForNavigation(), editor.getByRole('button', { name: '초안 저장', exact: true }).click()]);
  await reopen();
}
async function publish() {
  await editor.locator('footer button[data-w-dropdown-target="toggle"]').click();
  await Promise.all([editor.waitForNavigation(), editor.locator('button[name="action-publish"]').click()]);
  await reopen();
}
async function home(title) {
  await visitor.goto(`${origin}/?branch=second`);
  assert.equal(await visitor.locator('#intro-title').innerText(), title);
  await settle(visitor);
}
async function geometry(page) {
  return page.evaluate(() => {
    const image = document.querySelector('.hero-figure img');
    const rect = image?.getBoundingClientRect();
    const title = document.querySelector('#intro-title');
    return {
      width: innerWidth, documentWidth: document.documentElement.scrollWidth,
      titleSize: getComputedStyle(title).fontSize,
      image: rect ? { width: rect.width, height: rect.height, loaded: image.complete && image.naturalWidth > 0, position: getComputedStyle(image).objectPosition } : null,
      background: getComputedStyle(document.body).backgroundColor,
    };
  });
}
try {
  if (!liveReadOnly) {
    const html = await (await publicContext.request.get(`${origin}/branches/`)).text();
    const navigation = JSON.parse(html.match(/<script[^>]*id="branch-navigation-data"[^>]*>([\s\S]*?)<\/script>/)?.[1] || '[]');
    assert.deepEqual(navigation.map(branch => branch.id), ['main', 'second'], 'Brand review requires two published branch fixtures.');
  }
  await editor.goto(`${origin}/admin/login/`);
  await editor.locator('[name="username"]').fill('cms-review-editor');
  await editor.locator('[name="password"]').fill(password);
  await editor.locator('button[type="submit"]').click();
  await editor.getByRole('link', { name: '브랜드·홈', exact: true }).click();
  await editor.getByRole('link', { name: 'Y3GYM', exact: true }).click();
  await editor.locator('#id_name').waitFor();
  if (liveReadOnly) originalTitle = await editor.locator('#id_intro_title').inputValue();
  else assert.equal(await editor.locator('#id_intro_title').inputValue(), originalTitle);
  const originalImage = await editor.locator('#id_hero_image').inputValue();
  await capture(editor, 'brand-editor', true);
  await editor.locator('#id_hero_alt').scrollIntoViewIfNeeded();
  await capture(editor, 'brand-editor-photo');
  await editor.setViewportSize({ width: 375, height: 812 });
  await editor.waitForFunction(() => {
    const rect = document.querySelector('#id_name').getBoundingClientRect();
    return Math.abs(rect.x - 20) < 1 && Math.abs(rect.width - 335) < 1;
  });
  report.adminMobileNameBox = await editor.locator('#id_name').boundingBox();
  await editor.locator('#id_name').scrollIntoViewIfNeeded();
  assert.equal(await editor.evaluate(() => document.documentElement.scrollWidth), 375);
  await capture(editor, 'brand-editor-mobile');
  await editor.setViewportSize({ width: 1440, height: 900 });
  check('운영자 메뉴 → 브랜드·홈 입력 화면·기존 승인 콘텐츠', { originalImage });

  await home(originalTitle);
  const desktop = await geometry(visitor);
  assert.equal(desktop.titleSize, '40px');
  assert(desktop.image.loaded && Math.abs(desktop.image.width / desktop.image.height - 4 / 3) < 0.01);
  assert.equal(desktop.width, desktop.documentWidth);
  await capture(visitor, 'home-pc-first');
  await capture(visitor, 'home-pc-full', true);
  await visitor.setViewportSize({ width: 375, height: 812 });
  await home(originalTitle);
  const mobile = await geometry(visitor);
  assert.equal(mobile.titleSize, '30px');
  assert(mobile.image.loaded && Math.abs(mobile.image.width / mobile.image.height - 16 / 10) < 0.01);
  assert.equal(mobile.width, mobile.documentWidth);
  const bar = await visitor.locator('.mobile-contact-bar').boundingBox();
  assert(bar && bar.y + bar.height <= 813);
  await capture(visitor, 'home-mobile-first');
  await capture(visitor, 'home-mobile-full', true);
  check('승인 홈 PC·모바일 글꼴·이미지 비율·가로 넘침·하단 문의 바', { desktop, mobile, bar });

  const noScript = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 375, height: 812 } });
  const fallback = await noScript.newPage();
  await fallback.goto(origin);
  assert.equal(await fallback.locator('#intro-title').innerText(), originalTitle);
  assert.equal(await fallback.locator('[data-branch-panel]').count(), 2);
  assert(await fallback.getByRole('link', { name: '소식', exact: true }).first().isVisible());
  assert.equal(await fallback.evaluate(() => document.documentElement.scrollWidth), 375);
  await noScript.close();
  check('JavaScript 비활성 모바일: 서버 소개·두 지점 본문·기본 탐색 유지');

  await editor.locator('#id_intro_title').fill(draftTitle);
  await editor.locator('#id_intro_text').fill('[TEST] 미리보기에서만 보이는 설명입니다.');
  await editor.locator('#id_hero_position_x').fill('35');
  await editor.locator('#id_hero_position_y').fill('65');
  if (!liveReadOnly) await draft();
  assert.equal(await editor.locator('#id_intro_title').inputValue(), draftTitle);
  await home(originalTitle);
  await editor.locator('button[data-side-panel-toggle="preview"]').click();
  const frame = editor.frameLocator('iframe').first();
  await frame.locator('#intro-title').filter({ hasText: draftTitle }).waitFor();
  assert.equal(await frame.locator('.hero-figure img').evaluate(image => getComputedStyle(image).objectPosition), '35% 65%');
  assert.equal(await frame.locator('script[src*="home-popups.js"]').count(), 0);
  await capture(editor, 'brand-draft-preview');
  await editor.locator('button[data-side-panel-toggle="preview"]').click();
  check(liveReadOnly ? '실행 중 CMS의 저장 전 미리보기·공개 홈 유지·사진 중심·자동 팝업 없음' : '초안 저장·재진입·권한 미리보기: 공개 홈 유지·사진 중심·자동 팝업 없음');

  if (!liveReadOnly) {
  await publish();
  await home(draftTitle);
  assert.equal((await geometry(visitor)).image.position, '35% 65%');
  check('명시적 공개 후에만 실제 홈 소개·사진 중심 변경');

  // Wagtail's chooser clear button updates its hidden input and visible state.
  const chooser = editor.locator('#id_hero_image-chooser');
  await chooser.locator('button[data-w-dropdown-target="toggle"]').click();
  await chooser.locator('button[data-chooser-action-clear]').click();
  await draft();
  await home(draftTitle);
  assert.equal(await visitor.locator('.hero-figure').count(), 1);
  await publish();
  await home(draftTitle);
  assert.equal(await visitor.locator('.hero-figure').count(), 0);
  assert.equal(await visitor.locator('.hero-layout--text-only').count(), 1);
  check('대표 사진 제거도 초안·공개 분리·사진 없는 배치');
  await capture(visitor, 'home-mobile-no-photo');

  await editor.goto(`${origin}/admin/snippets/news/brandcontent/unpublish/1/`);
  await Promise.all([editor.waitForNavigation(), editor.locator('form[action*="/unpublish/"] button[type="submit"], form[action*="/unpublish/"] input[type="submit"]').click()]);
  await home('브랜드 소개를 준비 중입니다.');
  assert(await visitor.getByRole('link', { name: '지점 안내', exact: true }).count() > 0);
  assert(await visitor.getByRole('link', { name: '소식', exact: true }).count() > 0);
  await capture(visitor, 'home-mobile-withdrawn');
  check('공개 철회 시 소개·사진 제외·지점과 소식 기본 탐색 유지');
  } else {
    // Leave the editor without saving or publishing the temporary preview.
    await editor.goto(`${origin}/admin/snippets/news/brandcontent/`);
    await home(originalTitle);
  }

  assert.deepEqual(report.errors, []);
  report.status = 'PASS';
} catch (error) {
  report.status = 'FAIL';
  report.failure = { message: error.message, stack: error.stack };
  await capture(editor, 'failure-editor').catch(() => {});
  throw error;
} finally {
  await fs.writeFile(path.join(output, 'result.json'), JSON.stringify(report, null, 2));
  await browser.close();
}
