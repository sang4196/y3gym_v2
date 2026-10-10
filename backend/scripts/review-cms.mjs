import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from '../../prototype/node_modules/@playwright/test/index.mjs';

// This local review creates one fictional post and uploads test images. It
// withdraws that post at the end; it never resets or deletes existing content.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const output = path.join(root, 'review');
const origin = 'http://localhost:8768';
const credentials = JSON.parse(await fs.readFile(path.join(root, '.local-credentials'), 'utf8'));
const run = new Date().toISOString().replace(/[:.]/g, '-');
const title = `[TEST] 소식 편집 검수 ${run}`;
const changedTitle = `${title} · 수정`;
const checks = [];
const errors = [];
const warnings = [];
const screenshots = [];
const report = { run, origin, checks, errors, warnings, screenshots, status: 'RUNNING' };
await fs.mkdir(output, { recursive: true });
const browser = await chromium.launch();
const editorContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const publicContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const editor = await editorContext.newPage();
const visitor = await publicContext.newPage();
editor.setDefaultTimeout(15000);
editor.setDefaultNavigationTimeout(20000);
visitor.setDefaultTimeout(15000);
for (const page of [editor, visitor]) page.on('pageerror', error => {
  // Wagtail 7.4.3's duplicate-upload confirmation replaces a tab panel. Its
  // native tab controller reports a transient unmatched panel, while image
  // selection remains usable. Record this explicitly, never hide all errors.
  const known = page === editor && error.message === "Cannot find matching a matching panel for the trigger/tab in 'aria-controls', 'href' or 'data-w-tabs-id-param'.";
  (known ? warnings : errors).push({ url: page.url(), message: error.message });
});
const check = (name, detail) => {
  checks.push({ name, result: 'PASS', detail });
  console.log(`PASS ${name}`);
};
const capture = async (page, name, fullPage = false) => {
  const filename = `${name}.png`;
  await page.screenshot({ path: path.join(output, filename), fullPage });
  screenshots.push(filename);
};
const settle = async page => {
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].map(img => img.decode().catch(() => {})));
  });
};
const saveDraft = async () => {
  await Promise.all([
    editor.waitForNavigation(),
    editor.getByRole('button', { name: '초안 저장', exact: true }).click(),
  ]);
  await editor.goto(`${origin}/admin/snippets/news/post/`);
};
const openPost = async name => {
  if (report.postId) await editor.goto(`${origin}/admin/snippets/news/post/edit/${report.postId}/`);
  else await editor.getByRole('link', { name, exact: true }).click();
  await editor.locator('#id_title').waitFor();
};
const publish = async () => {
  await editor.locator('footer button[data-w-dropdown-target="toggle"]').click();
  await Promise.all([
    editor.waitForNavigation(),
    editor.locator('button[name="action-publish"]').click(),
  ]);
  await editor.goto(`${origin}/admin/snippets/news/post/`);
};
const uploadImage = async (filename, imageTitle) => {
  await editor.getByRole('tab', { name: '업로드', exact: true }).click();
  await editor.locator('#id_image-chooser-upload-file').setInputFiles(path.join(root, '../prototype/assets/images', filename));
  await editor.locator('#id_image-chooser-upload-title').fill(imageTitle);
  await editor.locator('.modal button[type="submit"]').click();
  const duplicate = editor.getByRole('link', { name: 'Use new image', exact: true });
  await Promise.race([
    editor.locator('.modal').waitFor({ state: 'hidden' }),
    duplicate.waitFor({ state: 'visible' }),
    editor.locator('#id_image-chooser-insertion-alt_text').waitFor({ state: 'visible' }),
  ]);
  // Keep both test uploads; do not delete any existing asset on repeated runs.
  if (await duplicate.isVisible()) await duplicate.click();
};
const preview = async expectedTitle => {
  await editor.locator('button[data-side-panel-toggle="preview"]').click();
  const frame = editor.frameLocator('iframe').first();
  await frame.locator('#post-title').filter({ hasText: expectedTitle }).waitFor({ timeout: 20000 });
  await capture(editor, expectedTitle === title ? 'cms-draft-preview' : 'cms-revised-preview');
  await editor.locator('button[data-side-panel-toggle="preview"]').click();
};

try {
  await editor.goto(`${origin}/admin/login/`);
  await editor.locator('[name="username"]').fill('cms-review-editor');
  await editor.locator('[name="password"]').fill(credentials['cms-review-editor']);
  await editor.locator('button[type="submit"]').click();
  await editor.goto(`${origin}/admin/snippets/news/post/add/`);
  console.log('작성 화면 진입');
  await editor.locator('#id_title').fill(title);
  await editor.locator('#id_summary').fill('실제 CMS의 초안·미리보기·공개 흐름을 확인하는 테스트 글입니다.');
  await editor.getByRole('button', { name: '이미지 선택', exact: true }).click();
  await uploadImage('gym-strength.png', `[TEST] 대표 사진 ${run}`);
  await editor.locator('.modal').waitFor({ state: 'hidden' });
  const originalCover = await editor.locator('#id_cover_image').inputValue();
  assert(originalCover);
  console.log('대표 사진 업로드 완료');
  const body = editor.locator('.public-DraftEditor-content');
  await body.click();
  await editor.keyboard.insertText('시설 이용 안내를 준비하는 테스트 본문입니다.');
  await editor.keyboard.press('Enter');
  await editor.keyboard.press('Control+b');
  await editor.keyboard.insertText('확인할 내용');
  await editor.keyboard.press('Control+b');
  await editor.keyboard.press('Enter');
  await editor.keyboard.insertText('한글 문단과 줄바꿈을 확인합니다.');
  await editor.keyboard.press('Shift+Enter');
  await editor.keyboard.insertText('같은 문단의 다음 줄입니다.');
  await editor.keyboard.press('Enter');
  await editor.getByRole('button', { name: 'Insert a block', exact: true }).click();
  await editor.getByRole('option', { name: '이미지', exact: true }).click();
  console.log('본문 사진 선택 창 진입');
  await uploadImage('gym-cardio.png', `[TEST] 본문 사진 ${run}`);
  await editor.locator('#id_image-chooser-insertion-format_0').check();
  await editor.locator('#id_image-chooser-insertion-alt_text').fill('테스트 자료: 유산소 운동 시설');
  await editor.locator('.modal input[type="submit"]').click();
  await editor.locator('.modal').waitFor({ state: 'hidden' });
  await saveDraft();
  await openPost(title);
  const postId = Number(editor.url().match(/\/post\/edit\/(\d+)\//)[1]);
  report.postId = postId;
  const publicUrl = `${origin}/news/${postId}/?branch=second`;
  report.publicUrlDuringReview = publicUrl;
  const source = await editor.locator('#id_body').inputValue();
  const raw = JSON.parse(source);
  assert(raw.blocks.some(block => block.text.includes('한글 문단')));
  assert(raw.blocks.some(block => block.inlineStyleRanges.some(range => range.style === 'BOLD')));
  assert(Object.values(raw.entityMap).some(entity => entity.type === 'IMAGE'));
  assert.equal((await visitor.goto(publicUrl)).status(), 404);
  await preview(title);
  check('한글 문단·줄바꿈·굵게·본문 사진·대표 사진 저장과 초안 미리보기', { originalCover, publicDraftStatus: 404 });
  await publish();
  assert.equal((await visitor.goto(publicUrl)).status(), 200);
  assert.equal(await visitor.locator('#post-title').innerText(), title);
  await settle(visitor);
  assert.equal(await visitor.locator('.post-body strong, .post-body b').innerText(), '확인할 내용');
  const originalImages = await visitor.locator('.post-body img').evaluateAll(images => images.map(image => image.src));
  assert.equal(originalImages.length, 2);
  for (const url of originalImages) assert.equal((await publicContext.request.get(url)).status(), 200);
  const originalDate = await visitor.locator('.post-meta').innerText();
  check('명시적 공개 후 공개 HTML·본문 서식·대표/본문 이미지 제공', { imageCount: originalImages.length });

  // Responsive checks and captures use the real CMS publication, without
  // regenerating any static prototype HTML or historical evidence.
  for (const width of [320, 375, 768, 1024, 1280, 1440]) {
    await visitor.setViewportSize({ width, height: width <= 375 ? 812 : 900 });
    for (const [kind, url] of [['list', `${origin}/news/?branch=second`], ['detail', publicUrl]]) {
      await visitor.goto(url);
      await settle(visitor);
      const layout = await visitor.evaluate(() => ({
        overflow: document.documentElement.scrollWidth > innerWidth + 1,
        font: document.fonts.check('16px Pretendard'),
        brokenImages: [...document.images].filter(img => !img.complete || img.naturalWidth === 0).length,
        distortedImages: [...document.querySelectorAll('.post-body img')].filter(img => {
          const rect = img.getBoundingClientRect();
          return Math.abs(rect.height - rect.width * img.naturalHeight / img.naturalWidth) > 2;
        }).length,
      }));
      assert.equal(layout.overflow, false, `${kind} overflow at ${width}`);
      assert.equal(layout.brokenImages, 0, `${kind} images at ${width}`);
      assert.equal(layout.distortedImages, 0, `${kind} image aspect ratio at ${width}`);
      assert.equal(layout.font, true);
      if ([375, 1440].includes(width)) {
        await capture(visitor, `${kind}-${width}-first`);
        await capture(visitor, `${kind}-${width}-full`, true);
      }
    }
  }
  check('공개 목록·상세 6개 폭에서 가로 넘침·이미지·글꼴 확인', [320, 375, 768, 1024, 1280, 1440]);
  await visitor.goto(`${origin}/news/?branch=second&category=notices`);
  assert((await visitor.locator('.news-title-link').allTextContents()).includes(title));
  await visitor.getByRole('link', { name: title, exact: true }).click();
  assert.equal(new URL(visitor.url()).searchParams.get('branch'), 'second');
  check('분류와 소식 상세 진입 시 선택 지점 유지', 'second');

  await openPost(title);
  await editor.locator('#id_title').fill(changedTitle);
  // Replace the cover reference, not the existing stored image file.
  await editor.locator('#id_cover_image-chooser button[data-w-dropdown-target="toggle"]').click();
  await editor.locator('[data-chooser-action-choose]:visible').click();
  await uploadImage('gym-stretch.png', `[TEST] 교체 대표 사진 ${run}`);
  await editor.locator('.modal').waitFor({ state: 'hidden' });
  const replacementCover = await editor.locator('#id_cover_image').inputValue();
  assert.notEqual(replacementCover, originalCover);
  // Replace the body placement through the editor, without deleting its asset.
  await editor.locator('.Draftail-block--atomic img').click();
  await editor.getByRole('button', { name: '삭제', exact: true }).click();
  await body.click();
  await editor.keyboard.press('Control+End');
  await editor.keyboard.press('Enter');
  await editor.getByRole('button', { name: 'Insert a block', exact: true }).click();
  await editor.getByRole('option', { name: '이미지', exact: true }).click();
  await uploadImage('gym-hero.png', `[TEST] 교체 본문 사진 ${run}`);
  await editor.locator('#id_image-chooser-insertion-format_0').check();
  await editor.locator('#id_image-chooser-insertion-alt_text').fill('테스트 자료: 교체한 시설 사진');
  await editor.locator('.modal input[type="submit"]').click();
  await editor.locator('.modal').waitFor({ state: 'hidden' });
  await editor.locator('.Draftail-block--atomic img[src*="gym-hero"]').waitFor();
  await editor.locator('.public-DraftStyleDefault-block').last().click();
  await editor.keyboard.press('End');
  await editor.keyboard.insertText('수정 초안에만 있는 안내입니다.');
  assert((await body.innerText()).includes('수정 초안에만'));
  await saveDraft();
  await visitor.goto(publicUrl);
  assert.equal(await visitor.locator('#post-title').innerText(), title);
  assert.equal(await visitor.locator('.post-meta').innerText(), originalDate);
  assert(!(await visitor.locator('.post-body').innerText()).includes('수정 초안에만'));
  assert.deepEqual(await visitor.locator('.post-body img').evaluateAll(images => images.map(image => image.src)), originalImages);
  await openPost(changedTitle);
  await preview(changedTitle);
  check('공개 글 수정 초안·미리보기 중 기존 제목·본문·사진·날짜 유지', { replacementCover });
  await publish();
  await visitor.goto(publicUrl);
  await settle(visitor);
  assert.equal(await visitor.locator('#post-title').innerText(), changedTitle);
  assert((await visitor.locator('.post-body').innerText()).includes('수정 초안에만'));
  const updatedImages = await visitor.locator('.post-body img').evaluateAll(images => images.map(image => image.src));
  assert.notEqual(updatedImages[0], originalImages[0]);
  assert.equal((await publicContext.request.get(originalImages[0])).status(), 404);
  assert.equal((await publicContext.request.get(updatedImages[0])).status(), 200);
  assert.notEqual(updatedImages[1], originalImages[1]);
  assert.equal((await publicContext.request.get(originalImages[1])).status(), 404);
  assert.equal((await publicContext.request.get(updatedImages[1])).status(), 200);
  check('재공개 시 대표·본문 사진 참조 교체와 이전 사진 차단', '실제 미디어 HTTP 요청');

  // Use the CMS's actual withdrawal confirmation form, including its CSRF token.
  await editor.goto(`${origin}/admin/snippets/news/post/unpublish/${postId}/`);
  await Promise.all([
    editor.waitForNavigation(),
    editor.locator('form[action*="/unpublish/"] button[type="submit"], form[action*="/unpublish/"] input[type="submit"]').click(),
  ]);
  await editor.goto(`${origin}/admin/snippets/news/post/`);
  assert.equal((await visitor.goto(publicUrl)).status(), 404);
  for (const url of updatedImages) {
    const response = await publicContext.request.get(url);
    assert.equal(response.status(), 404);
    assert(response.headers()['cache-control'].includes('no-store'));
  }
  await visitor.goto(`${origin}/news/`);
  assert(!(await visitor.locator('.news-title-link').allTextContents()).includes(changedTitle));
  check('CMS 공개 철회 후 목록·상세·마지막 공개 이미지 차단', { postId, finalState: '초안/비공개' });

  const noJs = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 375, height: 812 } });
  const plain = await noJs.newPage();
  await plain.goto(`${origin}/news/?branch=second`);
  assert((await plain.locator('.news-title-link').count()) >= 2);
  const branchLink = plain.locator('.primary-navigation a').filter({ hasText: '지점 안내' });
  assert(await branchLink.isVisible());
  assert((await branchLink.getAttribute('href')).includes('branch=second'));
  await plain.locator('.news-title-link').first().click();
  assert(await plain.locator('#post-title').isVisible());
  await noJs.close();
  check('JavaScript 비활성 모바일에서 핵심 본문·기본 메뉴 탐색 유지', '서버 HTML 링크');
  assert.deepEqual(errors, []);
  report.status = warnings.length ? 'PASS_WITH_WARNINGS' : 'PASS';
} catch (error) {
  report.status = 'FAIL';
  // Never persist login credentials in browser review artifacts.
  let message = error.stack || error.message;
  for (const secret of Object.values(credentials)) message = message.replaceAll(secret, '[REDACTED]');
  report.failure = message;
  await capture(editor, 'failure-editor').catch(() => {});
  process.exitCode = 1;
} finally {
  await browser.close();
  await fs.writeFile(path.join(output, 'checks.json'), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ status: report.status, checks: checks.length, screenshots: screenshots.length, report: 'review/checks.json', failure: report.failure }));
}
