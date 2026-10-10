import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '../../prototype/node_modules/@playwright/test/index.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const readOnly = process.argv.includes('--live-read-only');
const origin = readOnly ? 'http://localhost:8768' : process.env.Y3GYM_TRAINER_REVIEW_ORIGIN;
assert(origin && new URL(origin).hostname === 'localhost' && (readOnly || !['8767', '8768'].includes(new URL(origin).port)), 'Writes require an isolated test-server origin.');
const output = path.resolve(root, process.env.Y3GYM_TRAINER_REVIEW_DIR || 'review/trainers/browser');
await fs.mkdir(output, { recursive: true });
const report = { run: new Date().toISOString(), status: 'RUNNING', origin, readOnly, isolatedTestDatabase: !readOnly, checks: [], errors: [], screenshots: [] };
const browser = await chromium.launch();
const visitorContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const editorContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const visitor = await visitorContext.newPage();
const editor = await editorContext.newPage();
for (const context of [visitorContext, editorContext]) context.on('page', page => page.on('pageerror', error => report.errors.push(error.message)));
const check = (name, detail) => { report.checks.push({ name, detail, result: 'PASS' }); console.log('PASS ' + name); };
async function ready(page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].map(image => { image.loading = 'eager'; return image.decode().catch(() => {}); }));
  });
}
async function capture(page, name, fullPage = true) {
  await ready(page);
  await page.screenshot({ path: path.join(output, name + '.png'), fullPage });
  report.screenshots.push(name + '.png');
}
async function noOverflow(page) {
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Page has horizontal overflow');
}
async function selected(key) {
  await visitor.locator(`#branch-${key}:not([hidden])`).waitFor();
  assert.equal(await visitor.locator('[data-branch-panel]:not([hidden])').count(), 1);
}
async function save() {
  const name = await editor.locator('#id_name').inputValue() || '트레이너 (준비 초안)';
  await Promise.all([editor.waitForNavigation(), editor.getByRole('button', { name: '초안 저장', exact: true }).click()]);
  if (!(await editor.locator('#id_name').count())) await editor.getByRole('link', { name, exact: true }).click();
  await editor.locator('#id_name').waitFor();
}
async function publish() {
  const name = await editor.locator('#id_name').inputValue();
  const url = editor.url();
  await editor.locator('footer button[data-w-dropdown-target="toggle"]').click();
  await Promise.all([editor.waitForNavigation(), editor.locator('button[name="action-publish"]').click()]);
  if (url.includes('/edit/')) await editor.goto(url);
  else await editor.getByRole('link', { name, exact: true }).click();
  await editor.locator('#id_name').waitFor();
}
try {
  for (const key of ['main', 'second']) {
    await visitor.goto(origin + '/branches/?branch=' + key);
    await selected(key);
    assert.equal(await visitor.locator(`#branch-${key} [data-trainer-id]`).count(), 1);
    assert.equal(await visitor.locator(`#branch-${key} [data-trainer-biography], #branch-${key} [data-trainer-position]`).count(), 0);
    await noOverflow(visitor);
    await capture(visitor, `initial-${key}-desktop`);
  }
  check('공개 지점별 가상 A/B 1명·선택 직급/약력 숨김·1440 화면');
  if (!readOnly) {
    await editor.goto(origin + '/admin/login/');
    await editor.locator('#id_username').fill('cms-review-editor');
    await editor.locator('#id_password').fill(process.env.Y3GYM_TRAINER_REVIEW_PASSWORD);
    await Promise.all([editor.waitForNavigation(), editor.locator('button[type="submit"], input[type="submit"]').first().click()]);
    await editor.goto(origin + '/admin/snippets/news/branch/');
    await editor.getByRole('link', { name: 'Y3GYM 본점', exact: true }).click();
    const mainEdit = editor.url();
    const mainPK = mainEdit.match(/\/edit\/(\d+)\//)[1];
    await editor.locator('[data-trainer-add]').click();
    assert.equal(await editor.locator('#id_branch').inputValue(), mainPK);
    assert((await editor.locator('main').innerText()).includes('별도 저장 단위'));
    await save();
    const extraEdit = editor.url();
    const extraPK = extraEdit.match(/\/edit\/(\d+)\//)[1];
    await editor.locator('#id_name').fill('검수용 · 선택 정보 없음');
    await publish();
    await visitor.goto(origin + '/branches/?branch=main');
    assert.equal(await visitor.locator('#branch-main [data-trainer-id]').count(), 2);
    assert.equal(await visitor.locator(`[data-trainer-id="${extraPK}"] figure, [data-trainer-id="${extraPK}"] [data-trainer-intro], [data-trainer-id="${extraPK}"] [data-trainer-position], [data-trainer-id="${extraPK}"] [data-trainer-biography]`).count(), 0);
    await capture(visitor, 'optional-empty-desktop');
    check('지점에서 등록·현재 지점 미리 선택·미완성 초안·공개·사진/선택 정보 숨김');
    await editor.goto(mainEdit);
    await editor.locator('[data-trainer-list]').click();
    assert(new URL(editor.url()).searchParams.get('branch') === mainPK);
    await editor.getByRole('link', { name: '트레이너 A', exact: true }).click();
    const trainerEdit = editor.url();
    const trainerPK = trainerEdit.match(/\/edit\/(\d+)\//)[1];
    await editor.locator('#id_position').fill('[검수용] 직급 표시 텍스트');
    for (let index = 0; index < 2; index++) {
      await editor.getByRole('button', { name: '약력 항목 추가', exact: true }).click();
      await editor.locator(`#id_biography-${index}-text`).fill(`[검수용] 짧은 약력 표시 항목 ${index + 1}`);
    }
    await publish();
    await visitor.reload();
    await noOverflow(visitor);
    await capture(visitor, 'short-biography-desktop');
    await visitor.locator('#branch-main [data-branch-section="trainers"]').screenshot({ path: path.join(output, 'short-biography-desktop-section.png') });
    report.screenshots.push('short-biography-desktop-section.png');
    await visitor.setViewportSize({ width: 375, height: 900 });
    await noOverflow(visitor);
    await capture(visitor, 'short-biography-mobile');
    await visitor.locator('#branch-main [data-branch-section="trainers"]').screenshot({ path: path.join(output, 'short-biography-mobile-section.png') });
    report.screenshots.push('short-biography-mobile-section.png');
    await visitor.setViewportSize({ width: 1440, height: 900 });
    check('일반적인 짧은 약력2항목/선택 직급·사진/본문 상단 정렬·PC/모바일 캡처');
    const longName = '검수용긴이름'.repeat(10);
    await editor.locator('#id_name').fill(longName);
    await editor.locator('#id_position').fill('[검수용] 직급 표시 텍스트');
    await editor.locator('#id_intro').fill('[검수용] 긴 소개와 약력 표시를 확인하는 임시 자료입니다.');
    for (let index = 0; index < 12; index++) {
      if (index >= 2) await editor.getByRole('button', { name: '약력 항목 추가', exact: true }).click();
      await editor.locator(`#id_biography-${index}-text`).fill(`[검수용 ${index + 1}] ${'약력표시확인'.repeat(12)}`);
    }
    await save();
    await editor.goto(trainerEdit);
    assert.equal(await editor.locator('#id_name').inputValue(), longName);
    assert.equal(await editor.locator('#id_biography-11-text').inputValue(), `[검수용 12] ${'약력표시확인'.repeat(12)}`);
    await visitor.reload();
    assert(!(await visitor.locator('#branch-main').innerText()).includes(longName));
    await capture(editor, 'trainer-editor-desktop');
    await editor.locator('button[data-side-panel-toggle="preview"]').click();
    const frame = editor.frameLocator('iframe').first();
    await frame.locator('[data-trainer-biography] li').nth(11).waitFor();
    assert((await frame.locator(`[data-trainer-id="${trainerPK}"]`).innerText()).includes(longName));
    await capture(editor, 'trainer-draft-preview');
    await editor.locator('button[data-side-panel-toggle="preview"]').click();
    await publish();
    await visitor.reload();
    assert.equal(await visitor.locator(`#branch-main [data-trainer-id="${trainerPK}"] [data-trainer-biography] li`).count(), 12);
    const alignment = await visitor.locator('#branch-main .trainer-grid').evaluate(grid => {
      const cards = [...grid.querySelectorAll('.trainer')];
      const detailed = grid.querySelector('.trainer--with-biography');
      return { rowTop: cards.map(card => card.getBoundingClientRect().y), photoTop: detailed.querySelector('figure').getBoundingClientRect().y, copyTop: detailed.querySelector('.trainer-copy').getBoundingClientRect().y };
    });
    assert(Math.abs(alignment.rowTop[0] - alignment.rowTop[1]) < 1);
    assert(Math.abs(alignment.photoTop - alignment.copyTop) < 1);
    report.cardAlignment = alignment;
    await noOverflow(visitor);
    await capture(visitor, 'long-profile-desktop');
    check('이름/직급/단일 약력12항목 초안·재진입·권한 미리보기·공개본 분리·명시적 공개');
    for (const width of [900, 375]) {
      await visitor.setViewportSize({ width, height: 900 });
      await noOverflow(visitor);
      const columns = await visitor.locator('#branch-main .trainer-grid').evaluate(element => getComputedStyle(element).gridTemplateColumns.split(' ').length);
      assert.equal(columns, width === 375 ? 1 : 2);
      const frameBox = await visitor.locator(`#branch-main [data-trainer-id="${trainerPK}"] .profile-image-frame`).boundingBox();
      assert(Math.abs(frameBox.width / frameBox.height - 0.8) < 0.02);
      await capture(visitor, 'long-profile-' + width);
    }
    await editor.setViewportSize({ width: 375, height: 900 });
    await editor.locator('#id_name').scrollIntoViewIfNeeded();
    await editor.waitForFunction(() => {
      const box = document.querySelector('#id_name').getBoundingClientRect();
      return Math.abs(box.x - 20) < 1 && Math.abs(box.width - 335) < 1;
    });
    await noOverflow(editor);
    await capture(editor, 'trainer-editor-mobile');
    await editor.setViewportSize({ width: 1440, height: 900 });
    await visitor.setViewportSize({ width: 1440, height: 900 });
    check('긴 이름/약력과 사진4:5·태블릿2열/모바일1열·375 관리자 입력');
    await editor.locator('#id_photo-chooser [data-w-dropdown-target="toggle"]').click();
    await editor.locator('#id_photo-chooser [data-chooser-action-clear]').click();
    await editor.locator('#id_branch-chooser [data-w-dropdown-target="toggle"]').click();
    await editor.locator('#id_branch-chooser .chosen [data-chooser-action-choose]').click();
    await editor.locator('.modal-content').getByRole('link', { name: 'Y3GYM 예시점', exact: true }).first().click();
    await editor.locator('#id_display_order').fill('9');
    await save();
    await visitor.goto(origin + '/branches/?branch=main');
    assert.equal(await visitor.locator(`#branch-main [data-trainer-id="${trainerPK}"]`).count(), 1);
    assert.equal(await visitor.locator(`#branch-main [data-trainer-id="${trainerPK}"] figure`).count(), 1);
    await publish();
    await visitor.goto(origin + '/branches/?branch=second');
    await selected('second');
    assert.equal(await visitor.locator(`#branch-main [data-trainer-id="${trainerPK}"]`).count(), 0);
    assert.equal(await visitor.locator(`#branch-second [data-trainer-id="${trainerPK}"]`).count(), 1);
    assert.equal(await visitor.locator(`#branch-second [data-trainer-id="${trainerPK}"] figure`).count(), 0);
    assert.equal(await visitor.locator('#branch-second [data-trainer-id]').last().getAttribute('data-trainer-id'), trainerPK);
    await capture(visitor, 'moved-profile-no-photo');
    check('동일 프로필 이동/수동 순서/사진 제거 초안 격리·공개 후 새 지점만 표시');
    await editor.goto(origin + `/admin/snippets/news/trainer/unpublish/${trainerPK}/`);
    await Promise.all([editor.waitForNavigation(), editor.locator('form[action*="/unpublish/"] button[type="submit"], form[action*="/unpublish/"] input[type="submit"]').click()]);
    await visitor.reload();
    assert.equal(await visitor.locator(`[data-trainer-id="${trainerPK}"]`).count(), 0);
    check('명시적 프로필 철회·공개 지점의 다른 프로필 유지');
  }
  await visitor.setViewportSize({ width: 375, height: 900 });
  for (const key of ['main', 'second']) {
    await visitor.goto(origin + '/branches/?branch=' + key);
    await selected(key);
    await noOverflow(visitor);
    await capture(visitor, key + '-mobile-final');
  }
  check('375 공개 지점 선택·트레이너 영역·문의 동선');
  const noJS = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 375, height: 900 } });
  const fallback = await noJS.newPage();
  await fallback.goto(origin + '/branches/?branch=second');
  assert.equal(await fallback.locator('[data-branch-panel]').count(), 2);
  assert.equal(await fallback.locator('[data-trainer-id]').count(), 2);
  assert.equal(await fallback.locator('#contact-main, #contact-second').count(), 2);
  await noOverflow(fallback);
  await capture(fallback, 'no-javascript-mobile');
  await noJS.close();
  check('JavaScript 없음·공개 트레이너 본문/모든 공개 지점/기본 탐색 유지');
  const home = await visitorContext.request.get(origin + '/');
  assert(!(await home.text()).includes('data-trainer-id'));
  assert.equal(report.errors.length, 0, JSON.stringify(report.errors));
  check('홈 트레이너/새 고객 메뉴 없음·JS 오류0');
  report.status = 'PASS';
} catch (error) {
  report.status = 'FAIL';
  report.failure = error.stack;
  await capture(editor, 'failure-editor').catch(() => {});
  await capture(visitor, 'failure-visitor').catch(() => {});
  process.exitCode = 1;
} finally {
  await fs.writeFile(path.join(output, 'checks.json'), JSON.stringify(report, null, 2) + '\n');
  await browser.close();
}
