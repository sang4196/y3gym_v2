import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '../../prototype/node_modules/@playwright/test/index.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const readOnly = process.argv.includes('--live-read-only');
const origin = readOnly ? 'http://localhost:8768' : process.env.Y3GYM_BRANCH_REVIEW_ORIGIN;
assert(origin && new URL(origin).hostname === 'localhost' && (readOnly || !['8767', '8768'].includes(new URL(origin).port)), 'Writes require the temporary Django test-server origin.');
const output = path.resolve(root, process.env.Y3GYM_BRANCH_REVIEW_DIR || (readOnly ? 'review/branches/live' : 'review/branches'));
await fs.mkdir(output, { recursive: true });
const report = { run: new Date().toISOString(), origin, readOnly, isolatedTestDatabase: !readOnly, status: 'RUNNING', checks: [], errors: [], screenshots: [] };
const browser = await chromium.launch();
const editorContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const visitorContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
// Hide active notifications only inside this independent screenshot context.
// Their DB settings and the user's browser are unchanged.
const html = await (await visitorContext.request.get(origin)).text();
const active = JSON.parse(html.match(/<script[^>]*id="home-popup-data"[^>]*>([\s\S]*?)<\/script>/)?.[1] || '[]');
await visitorContext.addInitScript(({ ids, origin }) => {
  if (location.origin !== origin) return;
  for (const id of ids) localStorage.setItem(`y3gym.prototype.hide:${id}`, String(Date.now() + 3600000));
}, { ids: active.map(popup => popup.id), origin });
for (const context of [editorContext, visitorContext]) context.on('page', page => page.on('pageerror', error => report.errors.push({ url: page.url(), message: error.message })));
const editor = await editorContext.newPage();
const visitor = await visitorContext.newPage();
editor.setDefaultTimeout(12000);
visitor.setDefaultTimeout(12000);
const check = (name, detail) => { report.checks.push({ name, detail, result: 'PASS' }); console.log(`PASS ${name}`); };
async function ready(page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].map(image => { image.loading = 'eager'; return image.decode().catch(() => {}); }));
  });
}
async function capture(page, name, fullPage = false) {
  await ready(page);
  await page.screenshot({ path: path.join(output, `${name}.png`), fullPage });
  report.screenshots.push(`${name}.png`);
}
async function save() {
  const name = await editor.locator('#id_name').inputValue();
  await Promise.all([editor.waitForNavigation(), editor.getByRole('button', { name: '초안 저장', exact: true }).click()]);
  if (!(await editor.locator('#id_name').count())) await editor.getByRole('link', { name, exact: true }).click();
  await editor.locator('#id_name').waitFor();
}
async function publish({ invalid = false } = {}) {
  const name = await editor.locator('#id_name').inputValue();
  const editURL = editor.url();
  await editor.locator('footer button[data-w-dropdown-target="toggle"]').click();
  if (invalid) { await editor.locator('button[name="action-publish"]').click(); await editor.getByText('공개하려면 입력해 주세요.', { exact: false }).first().waitFor(); }
  else {
    await Promise.all([editor.waitForNavigation(), editor.locator('button[name="action-publish"]').click()]);
    if (editURL.includes('/edit/')) await editor.goto(editURL);
    else await editor.getByRole('link', { name, exact: true }).click();
    await editor.locator('#id_name').waitFor();
  }
}
async function selected(page, key) {
  const panelId = await page.locator(`[data-branch-panel][data-branch-id="${key}"]`).getAttribute('id');
  await page.locator(`[data-branch-tab][role="tab"][aria-controls="${panelId}"][aria-selected="true"]`).waitFor();
  await page.locator(`[data-branch-panel][data-branch-id="${key}"]:not([hidden])`).waitFor();
  assert.equal(await page.locator('[data-branch-panel]:not([hidden])').count(), 1);
}
async function noOverflow(page) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
}
try {
  if (!readOnly) {
    await editor.goto(`${origin}/admin/login/`);
    await editor.locator('[name="username"]').fill('cms-review-editor');
    await editor.locator('[name="password"]').fill(process.env.Y3GYM_BRANCH_REVIEW_PASSWORD);
    await editor.locator('button[type="submit"]').click();
    await editor.getByRole('link', { name: '지점', exact: true }).click();
    await capture(editor, 'branch-list');
    await editor.getByRole('link', { name: 'Y3GYM 본점', exact: true }).click();
    await editor.locator('#id_name').waitFor();
    const mainEdit = editor.url();
    await capture(editor, 'branch-editor-desktop', true);
    await editor.setViewportSize({ width: 375, height: 812 });
    await editor.waitForFunction(() => {
      const rect = document.querySelector('#id_name').getBoundingClientRect();
      return Math.abs(rect.x - 20) < 1 && Math.abs(rect.width - 335) < 1;
    });
    report.adminMobileNameBox = await editor.locator('#id_name').boundingBox();
    await noOverflow(editor);
    await capture(editor, 'branch-editor-mobile');
    await editor.setViewportSize({ width: 1440, height: 900 });
    await editor.locator('#id_address').fill('[TEST] 수정 초안 주소');
    await editor.locator('#inline_child_facilities-2 [data-inline-panel-child-move-up]').click();
    await editor.locator('#id_facilities-1-DELETE-button').click();
    await save();
    await editor.goto(mainEdit);
    assert.equal(await editor.locator('#id_address').inputValue(), '[TEST] 수정 초안 주소');
    await visitor.goto(`${origin}/branches/?branch=main`);
    await selected(visitor, 'main');
    assert.equal(await visitor.locator('#branch-main [data-gallery-slide]').count(), 3);
    assert(!(await visitor.locator('#branch-main').innerText()).includes('수정 초안 주소'));
    check('관리자 시설 재정렬·삭제 초안 저장과 재진입, 공개 주소·사진 3장 유지');
    await editor.locator('button[data-side-panel-toggle="preview"]').click();
    const frame = editor.frameLocator('iframe').first();
    await frame.locator('#branch-main').filter({ hasText: '[TEST] 수정 초안 주소' }).waitFor();
    await capture(editor, 'branch-draft-preview');
    await editor.locator('button[data-side-panel-toggle="preview"]').click();
    await publish();
    await visitor.reload();
    await selected(visitor, 'main');
    assert.equal(await visitor.locator('#branch-main [data-gallery-slide]').count(), 2);
    assert((await visitor.locator('#branch-main').innerText()).includes('수정 초안 주소'));
    assert.equal((await visitor.locator('#branch-main [data-gallery-slide] h4').allTextContents()).join('|'), '웨이트 공간|스트레칭 공간');
    check('실제 템플릿 미리보기와 명시적 공개 후 시설 순서·삭제·주소 일괄 반영');

    await editor.goto(`${origin}/admin/snippets/news/branch/add/`);
    await editor.locator('#id_name').fill('[TEST] 새 예시 지점');
    await save();
    const thirdEdit = editor.url();
    await publish({ invalid: true });
    assert.equal(await editor.locator('#id_name').inputValue(), '[TEST] 새 예시 지점');
    await editor.locator('#id_address').fill('[TEST] 주소 예시');
    await editor.locator('#id_opening_hours').fill('[TEST] 운영시간 예시');
    await editor.locator('#id_phone').fill('[TEST] 전화 안내 예시');
    await publish();
    await visitor.goto(`${origin}/branches/`);
    assert.equal(await visitor.locator('[data-branch-tab]').count(), 3);
    await visitor.getByRole('tab', { name: '[TEST] 새 예시 지점', exact: true }).click();
    const third = new URL(visitor.url()).searchParams.get('branch');
    await selected(visitor, third);
    assert.equal(await visitor.locator(`[data-branch-id="${third}"] [data-gallery-slide]`).count(), 0);
    await visitor.locator('.primary-navigation a[href*="/news/"]').click();
    assert.equal(new URL(visitor.url()).searchParams.get('branch'), third);
    assert.equal(await visitor.locator('[data-inquiry="channel"]').isHidden(), true);
    assert.equal(await visitor.locator('.site-header .wordmark').getAttribute('href'), '/');
    await visitor.locator('.site-header .wordmark').click();
    assert.equal(new URL(visitor.url()).pathname, '/');
    assert.equal(new URL(visitor.url()).searchParams.has('branch'), false);
    await selected(visitor, third);
    await visitor.getByRole('link', { name: '[TEST] 새 예시 지점 자세히 보기', exact: true }).click();
    await selected(visitor, third);
    assert.equal(new URL(visitor.url()).port, new URL(origin).port);
    check('미완성 신규 초안·공개 필수값 오류·3번째 지점 증가·사진 0장·선택 전화 채널·홈/소식/상세 맥락 유지');

    await editor.goto(thirdEdit);
    await editor.getByRole('button', { name: '시설 사진 추가', exact: false }).click();
    await editor.locator('#id_facilities-0-image-chooser [data-chooser-action-choose]').click();
    await editor.locator('.modal-content a.image-choice').first().click();
    await editor.locator('#id_facilities-0-title').fill('[TEST] 새 시설 사진');
    await editor.locator('#id_facilities-0-position_x').fill('35');
    await editor.locator('#id_facilities-0-position_y').fill('65');
    await publish();
    await visitor.reload();
    assert.equal(await visitor.locator(`[data-branch-id="${third}"] [data-gallery-slide]`).count(), 1);
    assert.equal(await visitor.locator(`[data-branch-id="${third}"] [data-gallery-clone]`).count(), 0);
    assert.equal(await visitor.locator(`[data-branch-id="${third}"] [data-gallery-slide] img`).evaluate(image => getComputedStyle(image).objectPosition), '50% 50%');
    assert.equal(await visitor.locator(`[data-branch-id="${third}"] [data-gallery-slide] img`).evaluate(image => getComputedStyle(image).objectFit), 'contain');
    assert.equal(await editor.locator('#id_facilities-0-position_x').inputValue(), '35');
    assert.equal(await editor.locator('#id_facilities-0-position_y').inputValue(), '65');
    check('실제 사진 선택기로 시설 추가·1장 전체 중앙 표시·저장 중심 값 보존');
    // Many tabs and a long unbroken name are created only in the test DB.
    for (let index = 0; index < 5; index++) {
      await editor.goto(`${origin}/admin/snippets/news/branch/add/`);
      await editor.locator('#id_name').fill(`[TEST ${index}] ${'긴이름'.repeat(20)}`);
      await editor.locator('#id_address').fill('[TEST] 임시 주소');
      await editor.locator('#id_opening_hours').fill('[TEST] 임시 운영시간');
      await publish();
    }
    await visitor.goto(`${origin}/branches/?branch=unknown`);
    await selected(visitor, 'main');
    await visitor.setViewportSize({ width: 375, height: 812 });
    await visitor.getByRole('tab').last().click();
    await noOverflow(visitor);
    const tabVisible = await visitor.locator('[data-branch-tab][aria-selected="true"]').evaluate(tab => { const selected = tab.getBoundingClientRect(); const strip = tab.parentElement.getBoundingClientRect(); return selected.left < strip.right && selected.right > strip.left; });
    assert(tabVisible);
    await capture(visitor, 'many-tabs-long-name-mobile', true);
    check('8개 탭·긴 지점명·알 수 없는 ID 복구·모바일 가로 넘침 없음');
  }

  for (const [device, viewport] of [['desktop', { width: 1440, height: 900 }], ['mobile', { width: 375, height: 812 }]]) {
    await visitor.setViewportSize(viewport);
    for (const [kind, route] of [['home', '/'], ['branches', '/branches/']]) {
      await visitor.goto(`${origin}${route}?branch=second`);
      await selected(visitor, 'second');
      await noOverflow(visitor);
      await capture(visitor, `${kind}-${device}-first`);
      await capture(visitor, `${kind}-${device}-full`, true);
      if (!readOnly || kind === 'home') {
        // Existing isolated fixtures still explicitly verify zero trainers.
        assert.equal(await visitor.locator('.trainers').count(), 0);
      } else {
        assert.equal(await visitor.locator('.trainers:not([data-branch-section="trainers"])').count(), 0);
        for (const key of ['main', 'second']) {
          assert.equal(await visitor.locator(`#branch-${key} [data-trainer-id]`).count(), 1, 'Approved live A/B seed: one trainer per branch.');
        }
      }
      const loaded = await visitor.locator('[data-gallery-slide] img').evaluateAll(images => images.every(image => image.complete && image.naturalWidth > 0));
      assert(loaded);
    }
  }
  check(readOnly
    ? 'PC 1440×900·모바일 375×812 홈/상세 첫 화면·전체 캡처, 이미지 준비·홈 트레이너 숨김·실제 지점별 A/B 각 1명'
    : 'PC 1440×900·모바일 375×812 홈/상세 첫 화면·전체 캡처, 이미지 준비·0명 트레이너 숨김');
  await visitor.setViewportSize({ width: 1440, height: 900 });
  await visitor.goto(`${origin}/branches/?branch=second`);
  const gallery = visitor.locator('#branch-second [data-facility-gallery]');
  await gallery.scrollIntoViewIfNeeded();
  await visitor.mouse.move(0, 0);
  const track = gallery.locator('[data-gallery-track]');
  const initial = await track.evaluate(element => element.style.transform);
  await visitor.waitForFunction(value => document.querySelector('#branch-second [data-gallery-track]').style.transform !== value, initial, { timeout: 8000 });
  check('승인된 시설 자동 이동 실제 transform 변화');
  await visitor.emulateMedia({ reducedMotion: 'reduce' });
  await visitor.reload();
  await gallery.scrollIntoViewIfNeeded();
  await gallery.locator('[data-gallery-viewport]').focus();
  await visitor.keyboard.press('ArrowRight');
  assert.match(await gallery.locator('[data-gallery-status]').innerText(), /^시설 사진 2 \/ 3/);
  check('동작 줄이기·사진 영역 키보드 이동');
  await visitor.setViewportSize({ width: 375, height: 812 });
  await gallery.scrollIntoViewIfNeeded();
  const touchPoint = await gallery.locator('[data-gallery-viewport]').boundingBox();
  const cdp = await visitorContext.newCDPSession(visitor);
  const start = { x: Math.round(touchPoint.x + touchPoint.width * .8), y: Math.round(touchPoint.y + 40) };
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [start] });
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ ...start, x: start.x - 120 }] });
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  assert.match(await gallery.locator('[data-gallery-status]').innerText(), /^시설 사진 3 \/ 3/);
  await cdp.detach();
  check('모바일 가로 터치 스와이프의 시설 이동');
  const plain = await browser.newContext({ javaScriptEnabled: false });
  const basic = await plain.newPage();
  for (const route of ['/', '/branches/']) {
    await basic.goto(origin + route);
    assert.equal(await basic.locator('[data-branch-panel]:not([hidden])').count() >= 2, true);
    assert((await basic.locator('#branch-second').innerText()).includes('경기 ○○시 ○○로 00'));
    assert((await basic.locator('#branch-second').innerText()).includes('07:00'));
    assert.equal(await basic.locator('.primary-navigation').isVisible(), true);
  }
  await plain.close();
  check('JavaScript 없는 홈/상세의 모든 공개 지점·주소·운영시간·기본 메뉴 접근');

  if (!readOnly) {
    const ids = await editorContext.request.get(`${origin}/branches/`).then(response => response.text()).then(text => [...text.matchAll(/data-branch-id="([^"]+)"/g)].map(match => match[1]));
    // Withdraw through the real administrator UI; do not delete any data.
    for (const key of ids) {
      await editor.goto(`${origin}/admin/snippets/news/branch/`);
      const name = await visitorContext.request.get(`${origin}/branches/?branch=${key}`).then(response => response.text()).then(text => JSON.parse(text.match(/id="branch-navigation-data"[^>]*>([\s\S]*?)<\/script>/)[1]).find(branch => branch.id === key).name);
      await editor.getByRole('link', { name, exact: true }).click();
      const pk = editor.url().match(/\/edit\/(\d+)\//)[1];
      await editor.goto(`${origin}/admin/snippets/news/branch/unpublish/${pk}/`);
      await Promise.all([editor.waitForNavigation(), editor.locator('form[action*="/unpublish/"] button[type="submit"], form[action*="/unpublish/"] input[type="submit"]').click()]);
    }
    for (const route of ['/', '/branches/', '/news/']) {
      await visitor.goto(origin + route + '?branch=second');
      assert.equal(await visitor.locator('[data-inquiry]:not([hidden])').count(), 0);
      assert.equal(await visitor.locator('a[href*="/news/"]').count() > 0, true);
    }
    await capture(visitor, 'no-public-branches-mobile');
    check('마지막 공개 지점까지 철회·0곳 문의 버튼 숨김·브랜드/소식 탐색 유지');
  }
  assert.equal(report.errors.length, 0, JSON.stringify(report.errors));
  report.status = 'PASS';
} catch (error) {
  report.status = 'FAIL';
  report.failure = error.stack;
  await capture(editor, 'failure-editor', true).catch(() => {});
  await capture(visitor, 'failure-public', true).catch(() => {});
  throw error;
} finally {
  await fs.writeFile(path.join(output, 'checks.json'), JSON.stringify(report, null, 2) + '\n');
  await browser.close();
}
