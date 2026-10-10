import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '../../prototype/node_modules/@playwright/test/index.mjs';

// Creates its own clearly marked local review posts; never edits existing posts.
// On success the two examples remain available for user review for 24 hours.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const output = path.join(root, 'review/popups');
const origin = 'http://localhost:8768';
const credentials = JSON.parse(await fs.readFile(path.join(root, '.local-credentials'), 'utf8'));
const run = new Date().toISOString();
const kst = timestamp => new Date(timestamp + 9 * 3600000).toISOString().slice(0, 16);
const starts = kst(Date.now() - 3600000);
const ends = kst(Date.now() + 24 * 3600000);
const suffix = kst(Date.now()).replace('T', ' ');
const report = { run, origin, status: 'RUNNING', checks: [], errors: [], warnings: [], screenshots: [], posts: [] };
await fs.mkdir(output, { recursive: true });
const browser = await chromium.launch();
const editorContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const editor = await editorContext.newPage();
editor.setDefaultTimeout(15000);
editor.setDefaultNavigationTimeout(20000);
function monitor(page, admin = false) {
  page.on('pageerror', error => {
    const known = admin && error.message === "Cannot find matching a matching panel for the trigger/tab in 'aria-controls', 'href' or 'data-w-tabs-id-param'.";
    (known ? report.warnings : report.errors).push({ url: page.url(), message: error.message });
  });
}
monitor(editor, true);
const check = (name, detail) => {
  report.checks.push({ name, detail, result: 'PASS' });
  console.log(`PASS ${name}`);
};
const settle = page => page.evaluate(async () => {
  if (!location.pathname.startsWith('/admin/')) {
    // Full-page captures also inspect below-fold and offscreen gallery copies.
    // Eager loading is a review-only browser setting, not a UI source change.
    document.querySelectorAll('img').forEach(image => { image.loading = 'eager'; });
  }
  await Promise.race([
    Promise.all([document.fonts.ready, ...[...document.images].filter(image => image.complete ||
      (image.getClientRects().length && image.getBoundingClientRect().top < innerHeight))
      .map(image => image.decode().catch(() => {}))]),
    new Promise(resolve => setTimeout(resolve, 3000)),
  ]);
});
const capture = async (page, name, fullPage = false) => {
  if (page === editor) await page.getByRole('heading', { name: '팝업 설정', exact: true }).scrollIntoViewIfNeeded();
  await settle(page);
  await page.screenshot({ path: path.join(output, `${name}.png`), fullPage });
  report.screenshots.push(`${name}.png`);
};
const openEditor = async post => {
  await editor.goto(`${origin}/admin/snippets/news/post/edit/${post.id}/`);
  await editor.locator('[data-popup-settings-url]').waitFor();
};
const submitBody = async publish => {
  if (publish) await editor.locator('footer button[data-w-dropdown-target="toggle"]').click();
  const button = publish ? editor.locator('button[name="action-publish"]') : editor.getByRole('button', { name: '초안 저장', exact: true });
  await Promise.all([editor.waitForNavigation(), button.click()]);
};
const applyPopup = async ({ enabled = true, start = starts, end = ends, expected = 200 } = {}) => {
  await editor.locator('[data-popup-field="enabled"]').setChecked(enabled);
  await editor.locator('#popup-starts-at').fill(start);
  await editor.locator('#popup-ends-at').fill(end);
  const [response] = await Promise.all([
    editor.waitForResponse(response => response.url().includes('/admin/news-popup/') && response.request().method() === 'POST'),
    editor.locator('[data-apply-popup]').click(),
  ]);
  assert.equal(response.status(), expected);
  const result = await response.json();
  assert.equal(result.applied, expected === 200);
  return result;
};
const homePayload = async context => {
  const response = await context.request.get(`${origin}/?branch=second`);
  assert.equal(response.status(), 200);
  const html = await response.text();
  const content = html.match(/<script id="home-popup-data" type="application\/json">([\s\S]*?)<\/script>/)[1];
  return JSON.parse(content);
};
const newPublic = async (mobile = false) => {
  const context = await browser.newContext({ viewport: mobile ? { width: 375, height: 812 } : { width: 1440, height: 900 } });
  context.on('page', page => monitor(page));
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  return { context, page };
};
const withdraw = async post => {
  await editor.goto(`${origin}/admin/snippets/news/post/unpublish/${post.id}/`);
  await Promise.all([
    editor.waitForNavigation(),
    editor.locator('form[action*="/unpublish/"] button[type="submit"], form[action*="/unpublish/"] input[type="submit"]').click(),
  ]);
};

try {
  await editor.goto(`${origin}/admin/login/`);
  await editor.locator('[name="username"]').fill('cms-review-editor');
  await editor.locator('[name="password"]').fill(credentials['cms-review-editor']);
  await editor.locator('button[type="submit"]').click();

  for (let index = 0; index < 2; index++) {
    const post = { title: `[TEST] ${index ? '시설 사진 안내' : '방문 전 이용 안내'} · ${suffix}`, index };
    await editor.goto(`${origin}/admin/snippets/news/post/add/`);
    assert((await editor.locator('[data-popup-settings]').innerText()).includes('먼저 게시글을 초안 저장'));
    await editor.locator('#id_title').fill(post.title);
    await editor.locator('#id_summary').fill('로컬 CMS와 팝업 연결을 확인하는 테스트 안내입니다. 실제 운영 정보가 아닙니다.');
    await editor.locator('.public-DraftEditor-content').click();
    await editor.keyboard.insertText('선택한 지점의 시설과 이용 안내를 확인해 주세요. 이 게시글은 팝업 연동 검토를 위한 테스트 자료입니다.');
    await submitBody(false);
    await editor.goto(`${origin}/admin/snippets/news/post/`);
    await editor.getByRole('link', { name: post.title, exact: true }).click();
    post.id = Number(editor.url().match(/\/post\/edit\/(\d+)\//)[1]);
    report.posts.push(post);
    if (index === 0) {
      const result = await applyPopup();
      assert.equal(result.state, '게시글 비공개');
      assert.equal((await editorContext.request.get(`${origin}/popups/${post.id}/`)).status(), 404);
      assert.equal((await editorContext.request.get(`${origin}/news/${post.id}/`)).status(), 404);
      await capture(editor, 'admin-draft-settings', true);
      check('신규 글 초안 저장 안내·팝업 적용만으로 초안 게시 안 함', post.id);
    }
  }
  const [first, second] = report.posts;
  // Publish in reverse order: registration order must still control popups.
  for (const post of [second, first]) {
    await openEditor(post);
    await submitBody(true);
    await openEditor(post);
    await applyPopup();
  }
  await editor.reload();
  assert.equal(await editor.locator('#popup-starts-at').inputValue(), starts);
  assert.equal(await editor.locator('#popup-ends-at').inputValue(), ends);
  assert(await editor.locator('[data-popup-field="enabled"]').isChecked());
  await capture(editor, 'admin-popup-settings', true);
  check('한국 시간 설정 실제 DB 저장·재진입 유지', { starts, ends, zone: 'Asia/Seoul' });

  // Apply settings while actual title and rich text inputs contain unsaved work.
  await editor.locator('#id_title').fill(`${first.title} · 수정 초안`);
  await editor.locator('.public-DraftEditor-content').click();
  await editor.keyboard.press('Control+End');
  await editor.keyboard.insertText(' 공개하면 안 되는 수정 초안 문장.');
  const dirtyBody = await editor.locator('.public-DraftEditor-content').innerText();
  const revisionBefore = await editor.locator('[name="loaded_revision_id"]').inputValue();
  await applyPopup();
  assert.equal(await editor.locator('#id_title').inputValue(), `${first.title} · 수정 초안`);
  assert.equal(await editor.locator('.public-DraftEditor-content').innerText(), dirtyBody);
  assert.equal(await editor.locator('[name="loaded_revision_id"]').inputValue(), revisionBefore);
  let payload = await homePayload(editorContext);
  assert.equal(payload.find(popup => popup.postId === String(first.id)).title, first.title);
  await submitBody(false);
  await openEditor(first);
  assert.equal(await editor.locator('#popup-starts-at').inputValue(), starts);
  assert.equal(await editor.locator('#id_title').inputValue(), `${first.title} · 수정 초안`);
  payload = await homePayload(editorContext);
  assert.equal(payload.find(popup => popup.postId === String(first.id)).title, first.title);
  const live = await editorContext.request.get(`${origin}/news/${first.id}/`);
  assert(!(await live.text()).includes('공개하면 안 되는'));
  await capture(editor, 'admin-unsaved-body-preserved', true);
  check('작성 중 본문 유지·수정 초안 저장 뒤 팝업 설정 유지·공개본 보호', first.id);
  assert.deepEqual(payload.filter(popup => report.posts.some(post => String(post.id) === popup.postId)).map(popup => Number(popup.postId)), [first.id, second.id]);

  const desktop = await newPublic();
  const opened = [];
  desktop.page.on('popup', page => opened.push(page));
  await desktop.page.goto('http://localhost:8767/?branch=second');
  assert.equal(new URL(desktop.page.url()).port, '8768');
  await desktop.page.waitForFunction(ids => ids.every(id =>
    sessionStorage.getItem(`y3gym.prototype.shown:${id}`) === '1'), payload.map(popup => popup.id));
  await new Promise(resolve => setTimeout(resolve, 1500));
  assert.equal(opened.length, payload.length);
  for (let index = 0; index < opened.length; index++) {
    await opened[index].locator('[data-close-popup]').waitFor();
    assert.equal(new URL(opened[index].url()).pathname, payload[index].url);
    assert.equal(new URL(opened[index].url()).searchParams.get('branch'), 'second');
  }
  const automaticOrder = opened.map(page => new URL(page.url()).pathname);
  assert.equal(await desktop.page.getByRole('link', { name: '알림 보기', exact: true }).count(), 0);
  await capture(desktop.page, 'home-desktop-first');
  await capture(desktop.page, 'home-desktop-full', true);
  const firstWindow = opened.find(page => new URL(page.url()).pathname === `/popups/${first.id}/`);
  await capture(firstWindow, 'popup-desktop');
  await firstWindow.locator('[data-popup-post]').click();
  await firstWindow.locator('#post-title').waitFor();
  assert.equal(await firstWindow.locator('#post-title').innerText(), first.title);
  assert.equal(new URL(firstWindow.url()).searchParams.get('branch'), 'second');
  assert(!(await firstWindow.locator('.post-body').innerText()).includes('공개하면 안 되는'));
  await desktop.page.reload();
  await new Promise(resolve => setTimeout(resolve, 700));
  assert.equal(opened.length, payload.length);
  assert.equal(new URL(firstWindow.url()).pathname, `/popups/${first.id}/`);
  check('실제 홈 리디렉션·전체 PC 자동 노출 순서·실제 글 이동·새로고침 시 열린 창 재사용', { order: automaticOrder });
  await desktop.context.close();

  const blocked = await newPublic();
  await blocked.page.addInitScript(() => {
    window.originalPopupOpen = window.open.bind(window);
    window.open = () => null;
  });
  await blocked.page.goto(`${origin}/?branch=second`);
  await blocked.page.locator('[data-popup-recovery] a').first().waitFor();
  assert.equal(await blocked.page.locator('[data-popup-recovery] a').count(), payload.length);
  await blocked.page.reload();
  await blocked.page.locator('[data-popup-recovery] a').first().waitFor();
  await capture(blocked.page, 'home-blocked-manual-links', true);
  await blocked.page.evaluate(() => { window.open = window.originalPopupOpen; });
  const [recovered] = await Promise.all([blocked.page.waitForEvent('popup'), blocked.page.getByRole('link', { name: `${first.title} · 직접 열기`, exact: true }).click()]);
  await recovered.locator('[data-popup-content]').waitFor();
  await settle(recovered);
  await recovered.locator('[data-hide-today]').check();
  await Promise.all([recovered.waitForEvent('close'), recovered.locator('[data-close-popup]').click()]);
  const hiddenUntil = await blocked.page.evaluate(id => Number(localStorage.getItem(`y3gym.prototype.hide:post-${id}`)), first.id);
  const nextMidnight = (Math.floor((Date.now() + 9 * 3600000) / 86400000) + 1) * 86400000 - 9 * 3600000;
  assert.equal(hiddenUntil, nextMidnight);
  const newTab = await blocked.context.newPage();
  await newTab.addInitScript(() => { window.open = () => null; });
  await newTab.goto(`${origin}/`);
  await newTab.locator('[data-popup-recovery] a').first().waitFor();
  assert(!(await newTab.locator('[data-popup-recovery]').innerText()).includes(first.title));
  check('자동 차단·새로고침 후 수동 복구·한국 시간 다음 날 0시까지 숨김', { hiddenUntil: new Date(hiddenUntil).toISOString() });
  await blocked.context.close();

  const mobile = await newPublic(true);
  const mobileWindows = [];
  mobile.page.on('popup', page => mobileWindows.push(page));
  await mobile.page.goto(`${origin}/?branch=second`);
  // Existing content is preserved on repeat runs. Verify/close earlier items
  // before inspecting this run's two newly registered examples.
  for (const popup of payload) {
    if (popup.postId === String(first.id)) break;
    await mobile.page.locator('dialog[open] #mobile-popup-title').filter({ hasText: popup.title }).waitFor();
    await mobile.page.locator('[data-mobile-close-popup]').click();
  }
  await mobile.page.locator('dialog[open] #mobile-popup-title').filter({ hasText: first.title }).waitFor();
  await capture(mobile.page, 'popup-mobile-first');
  assert.equal(await mobile.page.locator('dialog[open]').count(), 1);
  await mobile.page.locator('[data-mobile-close-popup]').click();
  await mobile.page.locator('dialog[open] #mobile-popup-title').filter({ hasText: second.title }).waitFor();
  await capture(mobile.page, 'popup-mobile-second');
  assert.equal(mobileWindows.length, 0);
  await mobile.page.locator('[data-mobile-popup-post]').click();
  assert.equal(await mobile.page.locator('#post-title').innerText(), second.title);
  assert.equal(new URL(mobile.page.url()).searchParams.get('branch'), 'second');
  await mobile.context.close();
  check('모바일 한 개씩 순차 노출·새 창 없음·선택 지점 유지한 실제 글 이동', [first.id, second.id]);

  // Independent body publish must preserve the separately applied configuration.
  await openEditor(first);
  const settingVersion = await editor.locator('[data-popup-settings]').getAttribute('data-popup-version');
  await submitBody(true);
  await openEditor(first);
  assert.equal(await editor.locator('[data-popup-settings]').getAttribute('data-popup-version'), settingVersion);
  assert.equal(await editor.locator('#popup-ends-at').inputValue(), ends);
  check('본문 재게시가 독립 적용 팝업 설정을 되돌리지 않음', { version: settingVersion });

  await applyPopup({ enabled: false });
  assert(!(await homePayload(editorContext)).some(popup => popup.postId === String(first.id)));
  assert.equal((await editorContext.request.get(`${origin}/popups/${first.id}/`)).status(), 404);
  assert.equal((await editorContext.request.get(`${origin}/news/${first.id}/`)).status(), 200);
  await applyPopup({ start: kst(Date.now() - 7200000), end: kst(Date.now() - 3600000) });
  assert((await editor.locator('[data-popup-state]').innerText()).includes('기간 종료'));
  assert(!(await homePayload(editorContext)).some(popup => popup.postId === String(first.id)));
  assert.equal((await editorContext.request.get(`${origin}/news/${first.id}/`)).status(), 200);
  await applyPopup({ start: kst(Date.now() + 3600000), end: ends });
  assert((await editor.locator('[data-popup-state]').innerText()).includes('시작 전'));
  assert(!(await homePayload(editorContext)).some(popup => popup.postId === String(first.id)));
  await applyPopup();
  await withdraw(first);
  assert(!(await homePayload(editorContext)).some(popup => popup.postId === String(first.id)));
  assert.equal((await editorContext.request.get(`${origin}/popups/${first.id}/`)).status(), 404);
  assert.equal((await editorContext.request.get(`${origin}/news/${first.id}/`)).status(), 404);
  check('사용 해제·시작 전·종료 후·공개 철회 실제 홈 제외, 종료 후 게시글 유지', first.id);

  // Restore only these two test examples to a clean public body for user review.
  await openEditor(first);
  await editor.locator('#id_title').fill(first.title);
  await editor.locator('.public-DraftEditor-content').click();
  await editor.keyboard.press('Control+a');
  await editor.keyboard.insertText('로컬 CMS와 팝업 연결을 확인하는 테스트 본문입니다. 실제 운영 정보가 아닙니다.');
  await submitBody(true);
  await openEditor(first);
  await applyPopup();

  const responsive = await newPublic();
  await responsive.page.addInitScript(ids => {
    // Explicit hide-today fixtures isolate layout checks from popup overlays.
    for (const id of ids) localStorage.setItem(`y3gym.prototype.hide:${id}`, String(Date.now() + 3600000));
  }, payload.map(popup => popup.id));
  for (const width of [320, 375, 768, 1024, 1440]) {
    await responsive.page.setViewportSize({ width, height: width <= 375 ? 812 : 900 });
    await responsive.page.goto(`${origin}/?branch=second`);
    await settle(responsive.page);
    await responsive.page.waitForFunction(() => [...document.images]
      .filter(image => image.offsetParent).every(image => image.complete && image.naturalWidth > 0),
      null, { timeout: 15000 });
    const state = await responsive.page.evaluate(() => ({
      overflow: document.documentElement.scrollWidth > innerWidth + 1,
      font: document.fonts.check('16px Pretendard'),
      broken: [...document.images].filter(image => image.offsetParent && (!image.complete || !image.naturalWidth)).length,
    }));
    assert.deepEqual(state, { overflow: false, font: true, broken: 0 });
    if ([375, 1440].includes(width)) {
      await capture(responsive.page, `home-${width}-first`);
      await capture(responsive.page, `home-${width}-full`, true);
    }
  }
  await responsive.context.close();
  const noJs = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 375, height: 812 } });
  const plain = await noJs.newPage();
  await plain.goto(`${origin}/?branch=second`);
  assert(await plain.locator('.primary-navigation').isVisible());
  await plain.locator('[data-live-popup-entry] noscript a').first().click();
  assert(await plain.locator('#post-title').isVisible());
  await noJs.close();
  check('홈 5개 폭·글꼴·이미지·JavaScript 실패 시 기본 메뉴/공개 글 탐색', [320, 375, 768, 1024, 1440]);
  assert.deepEqual(report.errors, []);
  report.status = report.warnings.length ? 'PASS_WITH_WARNINGS' : 'PASS';
  report.finalState = { examples: 'two public TEST posts; popup enabled for review', starts, ends, timezone: 'Asia/Seoul' };
} catch (error) {
  report.status = 'FAIL';
  let message = error.stack || error.message;
  for (const secret of Object.values(credentials)) message = message.replaceAll(secret, '[REDACTED]');
  report.failure = message;
  await capture(editor, 'failure-editor', true).catch(() => {});
  for (const post of report.posts) {
    try { await openEditor(post); await applyPopup({ enabled: false }); await withdraw(post); }
    catch { /* Report IDs; never reset or delete existing content on failure. */ }
  }
  process.exitCode = 1;
} finally {
  await browser.close();
  await fs.writeFile(path.join(output, 'checks.json'), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ status: report.status, checks: report.checks.length, screenshots: report.screenshots.length, failure: report.failure }));
}
