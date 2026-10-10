import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '../../../prototype/node_modules/@playwright/test/index.mjs';

const backend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const origin = process.env.Y3GYM_SEARCH_REVIEW_ORIGIN;
assert(origin && new URL(origin).hostname === 'localhost' && !['8767', '8768'].includes(new URL(origin).port));
const output = path.resolve(backend, process.env.Y3GYM_SEARCH_REVIEW_DIR || 'review/trainers-independent-recheck/search-browser');
await fs.mkdir(output);
const report = { status: 'RUNNING', isolatedTestDatabase: true, origin, checks: [], requests: [], errors: [] };
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const editor = await context.newPage();
const visitor = await browser.newPage();
editor.on('pageerror', error => report.errors.push(error.message));
visitor.on('pageerror', error => report.errors.push(error.message));
const check = name => report.checks.push({ name, result: 'PASS' });
let branchPK, trainerPK, trainerEdit, secondTrainerPK;
async function save() {
  await Promise.all([editor.waitForNavigation(), editor.getByRole('button', { name: '초안 저장', exact: true }).click()]);
}
async function search(term, expected) {
  const pending = editor.waitForResponse(response => {
    const url = new URL(response.url());
    return url.pathname.endsWith('/trainer/results/') && url.searchParams.get('q') === term;
  });
  await editor.locator('#id_q').fill(term);
  const response = await pending;
  assert.equal(response.status(), 200);
  const url = new URL(response.url());
  assert.equal(url.searchParams.get('branch'), branchPK);
  report.requests.push({ query: term, branch: url.searchParams.get('branch'), status: response.status() });
  await editor.waitForFunction(ids => {
    const actual = [...new Set([...document.querySelectorAll('table a[href]')].map(link => link.getAttribute('href').match(/\/trainer\/edit\/(\d+)\//)?.[1]).filter(Boolean))].sort();
    return JSON.stringify(actual) === JSON.stringify(ids.sort());
  }, expected);
  assert.equal(new URL(editor.url()).searchParams.get('branch'), branchPK);
}
try {
  await editor.goto(origin + '/admin/login/');
  await editor.locator('#id_username').fill('cms-review-editor');
  await editor.locator('#id_password').fill(process.env.Y3GYM_SEARCH_REVIEW_PASSWORD);
  await Promise.all([editor.waitForNavigation(), editor.locator('button[type="submit"]').first().click()]);
  await editor.goto(origin + '/admin/snippets/news/trainer/');
  secondTrainerPK = (await editor.getByRole('link', { name: '트레이너 B', exact: true }).getAttribute('href')).match(/\/edit\/(\d+)\//)[1];
  await editor.getByRole('link', { name: '트레이너 A', exact: true }).click();
  trainerEdit = editor.url();
  trainerPK = trainerEdit.match(/\/edit\/(\d+)\//)[1];
  await visitor.goto(origin + '/branches/?branch=main');
  const originalCard = await visitor.locator(`#branch-main [data-trainer-id="${trainerPK}"]`).innerHTML();
  const originalIntro = await editor.locator('#id_intro').inputValue();
  await editor.locator('#id_name').fill('R1 DraftName · 새 이름');
  await editor.locator('#id_intro').fill('R1 DraftIntro · 새 소개');
  const previousBranch = await editor.locator('#id_branch').inputValue();
  await editor.locator('#id_branch-chooser [data-w-dropdown-target="toggle"]').click();
  await editor.locator('#id_branch-chooser .chosen [data-chooser-action-choose]').click();
  await editor.locator('.modal-content').getByRole('link', { name: 'Y3GYM 예시점', exact: true }).first().click();
  await editor.waitForFunction(previous => {
    const value = document.querySelector('#id_branch').value;
    return value && value !== previous;
  }, previousBranch);
  branchPK = await editor.locator('#id_branch').inputValue();
  await save();
  await editor.goto(origin + '/admin/snippets/news/trainer/?branch=' + branchPK);
  assert.equal(await editor.locator('form[data-search-form] input[name="branch"]').getAttribute('type'), 'hidden');
  await search('DraftName', [trainerPK]);
  assert.equal(await editor.locator(`table a[href$="/edit/${trainerPK}/"]`).first().innerText(), 'R1 DraftName · 새 이름');
  check('실제 운영자 로그인→이름/소개/소속 초안 저장→검색 입력·최신 이름 행 링크');
  await editor.screenshot({ path: path.join(output, 'draft-name.png'), fullPage: true });
  for (const term of ['draftname', 'DRAFTINTRO', '새 소개', '새 이름']) await search(term, [trainerPK]);
  check('이름/소개 대소문자·한글 검색과 최신 소속 유지·다른 지점 동명 초안 제외');
  await search('트레이너 A', []);
  await search(originalIntro, []);
  await search('없는 결과', []);
  check('이전 공개 이름/소개 및 일치 없음은 결과0');
  await search('', [trainerPK, secondTrainerPK]);
  check('검색어 비우면 최신 소속 지점 목록만 복원');
  await visitor.reload();
  assert.equal(await visitor.locator(`#branch-main [data-trainer-id="${trainerPK}"]`).innerHTML(), originalCard);
  await visitor.goto(origin + '/branches/?branch=second');
  assert.equal(await visitor.locator(`#branch-second [data-trainer-id="${trainerPK}"]`).count(), 0);
  check('검색·이동 초안 이후 공개 이름/소개/사진/원 소속 카드 전체 동일');
  await editor.goto(trainerEdit);
  await editor.locator('#id_name').fill('');
  await editor.locator('#id_intro').fill('');
  await save();
  await editor.goto(origin + '/admin/snippets/news/trainer/?branch=' + branchPK);
  for (const term of ['DraftName', 'DraftIntro', '트레이너 A', originalIntro]) await search(term, []);
  check('최신 초안의 빈 이름/소개가 이전 초안/공개 값으로 검색되지 않음');
  await editor.screenshot({ path: path.join(output, 'empty-draft-no-old-result.png'), fullPage: true });
  assert.equal(report.errors.length, 0);
  check('관리자/공개 페이지 JS 오류0');
  report.status = 'PASS';
} catch (error) {
  report.status = 'FAIL'; report.failure = error.stack; process.exitCode = 1;
  await editor.screenshot({ path: path.join(output, 'failure.png'), fullPage: true }).catch(() => {});
} finally {
  await fs.writeFile(path.join(output, 'checks.json'), JSON.stringify(report, null, 2) + '\n', { flag: 'wx' });
  await browser.close();
}
