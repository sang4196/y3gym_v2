import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from '../../prototype/node_modules/@playwright/test/index.mjs';

const run = process.env.Y3GYM_QA_RUN_DIR;
const origin = process.env.Y3GYM_BRAND_REVIEW_ORIGIN;
const input = JSON.parse(fs.readFileSync(path.join(run, 'logo-browser-input.json'), 'utf8'));
const output = path.join(run, 'output/logo-header');
fs.mkdirSync(output, { recursive: true, mode: 0o700 });
const report = { status: 'FAIL', checks: [], captures: [], geometries: [] };
const browser = await chromium.launch({ headless: true });
try {
  const editorContext = await browser.newContext();
  const visitorContext = await browser.newContext();
  const editor = await editorContext.newPage();
  const visitor = await visitorContext.newPage();
  const edit = `${origin}/admin/snippets/news/brandcontent/edit/1/`;
  await editor.goto(`${origin}/admin/login/`);
  await editor.locator('#id_username').fill('logo_editor');
  await editor.locator('#id_password').fill(process.env.Y3GYM_LOGO_REVIEW_PASSWORD);
  const [loginResponse] = await Promise.all([editor.waitForNavigation(), editor.locator('button[type=submit]').click()]);
  assert.equal(editor.url(), `${origin}/admin/`);
  assert.equal(loginResponse.status(), 200);
  async function reopen() { await editor.goto(edit); await editor.locator('#id_name').waitFor(); }
  async function publish() {
    await editor.locator('footer button[data-w-dropdown-target="toggle"]').click();
    await Promise.all([editor.waitForNavigation(), editor.locator('button[name="action-publish"]').click()]);
  }
  async function capture(name, height = 96) {
    await visitor.screenshot({ path: path.join(output, `${name}.png`), clip: { x: 0, y: 0, width: visitor.viewportSize().width, height } });
    report.captures.push(`${name}.png`);
  }
  const routes = ['/', '/branches/?branch=main', '/news/?branch=main', `/news/${input.post_id}/?branch=main`];
  async function inspect(label, logo, name = 'TEST Y3GYM') {
    for (const width of [1440, 375, 320]) {
      await visitor.setViewportSize({ width, height: 900 });
      for (const route of routes) {
        await visitor.goto(origin + route);
        const header = visitor.locator('.site-header .wordmark');
        assert.equal(await header.getAttribute('href'), '/');
        assert.equal(await header.getAttribute('aria-label'), name + ' 홈');
        assert.equal(await header.locator('.brand-name').textContent(), name);
        assert.equal(await header.locator('.brand-logo').count(), logo ? 1 : 0);
        if (logo) await header.locator('img').evaluate(image => image.decode());
        const geometry = await header.evaluate((node) => {
          const image = node.querySelector('img'), text = node.querySelector('.brand-name');
          const rect = node.getBoundingClientRect(), menu = document.querySelector('.menu-toggle');
          const slot = node.querySelector('.brand-logo-slot');
          return { viewport: innerWidth, document: document.documentElement.scrollWidth, headerHeight: document.querySelector('.header-inner').getBoundingClientRect().height, image: image ? { fit: getComputedStyle(image).objectFit, alt: image.alt, ratio: image.naturalWidth / image.naturalHeight, slotWidth: slot.getBoundingClientRect().width, slotHeight: slot.getBoundingClientRect().height, full: image.hasAttribute('data-image-full'), x: image.getBoundingClientRect().x } : null, textX: text.getBoundingClientRect().x, textOverflow: getComputedStyle(text).textOverflow, truncated: text.scrollWidth > text.clientWidth, menuOverlap: !menu.hidden && rect.right > menu.getBoundingClientRect().left + 1 };
        });
        assert.equal(geometry.viewport, geometry.document);
        assert.equal(geometry.menuOverlap, false);
        assert.equal(geometry.headerHeight, width < 768 ? 64 : 80);
        if (logo) {
          assert.equal(geometry.image.fit, 'contain');
          assert.equal(geometry.image.alt, '');
          assert.equal(geometry.image.full, false);
          assert.equal(geometry.image.slotWidth, width < 768 ? 32 : 40);
          assert.equal(geometry.image.slotHeight, width < 768 ? 32 : 40);
          assert.equal(geometry.image.ratio, logo.size[0] / logo.size[1]);
          assert(geometry.image.x < geometry.textX);
        }
        if (label === 'long') { assert.equal(geometry.textOverflow, 'ellipsis'); assert(geometry.truncated); }
        report.geometries.push({ label, width, route, ...geometry });
        if (route === '/' && (width !== 320 || label === 'long')) await capture(`${label}-${width}`);
        await header.click();
        await visitor.waitForURL(origin + '/');
        assert.equal(await visitor.locator('.content-image-viewer[open]').count(), 0);
        assert.equal(await visitor.locator('.site-header .wordmark .brand-name').textContent(), name);
      }
    }
    report.checks.push(`${label}: PC1440/mobile375/320 four routes, header home and no lightbox`);
  }
  await inspect('none', null);
  for (const logo of input.logos) {
    await reopen();
    const chooser = editor.locator('#id_logo_image-chooser');
    if (await chooser.locator('button[data-w-dropdown-target="toggle"]').isVisible()) {
      await chooser.locator('button[data-w-dropdown-target="toggle"]').click();
    }
    await chooser.locator('button[data-chooser-action-choose]:visible').click();
    await editor.locator('.modal a[data-chooser-modal-choice]').filter({ hasText: `TEST logo ${logo.label}` }).click();
    await editor.locator('.modal').waitFor({ state: 'hidden' });
    assert.equal(await editor.locator('#id_logo_image').inputValue(), String(logo.id));
    if (logo.label === 'square') {
      await editor.locator('#id_logo_image-chooser').screenshot({ path: path.join(output, 'admin-logo-chooser.png') });
      report.captures.push('admin-logo-chooser.png');
      await editor.locator('button[data-side-panel-toggle="preview"]').click();
      await editor.frameLocator('iframe').first().locator('.site-header .brand-logo').waitFor();
      await visitor.goto(origin);
      assert.equal(await visitor.locator('.site-header .brand-logo').count(), 0);
      const previewURL = await editor.frameLocator('iframe').first().locator('.site-header .brand-logo').getAttribute('src');
      assert.equal((await visitorContext.request.get(origin + previewURL)).status(), 404);
      await editor.locator('button[data-side-panel-toggle="preview"]').click();
      await Promise.all([editor.waitForNavigation(), editor.getByRole('button', { name: '초안 저장', exact: true }).click()]);
      await reopen();
      assert.equal(await editor.locator('#id_logo_image').inputValue(), String(logo.id));
      report.checks.push('Actual chooser selection, private preview and draft reopen without public leak');
    }
    await publish();
    await inspect(logo.label, logo);
    assert.equal((await visitorContext.request.get(origin + logo.original)).status(), 404);
  }
  const longName = 'TEST 아주 긴 브랜드 이름 '.repeat(4).slice(0, 80).trim();
  await reopen(); await editor.locator('#id_name').fill(longName); await publish();
  await inspect('long', input.logos.at(-1), longName);
  await visitor.setViewportSize({ width: 320, height: 900 }); await visitor.goto(origin);
  await visitor.locator('.menu-toggle').click();
  await visitor.locator('.primary-navigation').waitFor({ state: 'visible' });
  assert.equal(await visitor.evaluate(() => document.documentElement.scrollWidth), 320);
  await capture('long-320-menu-open', 340);
  report.checks.push('320px long brand mobile menu remains usable');
  await reopen();
  const chooser = editor.locator('#id_logo_image-chooser');
  await chooser.locator('button[data-w-dropdown-target="toggle"]').click();
  await chooser.locator('button[data-chooser-action-clear]').click();
  assert.equal(await editor.locator('#id_logo_image').inputValue(), '');
  await publish(); await visitor.goto(origin);
  assert.equal(await visitor.locator('.brand-logo-slot').count(), 0);
  report.checks.push('Actual chooser clear and publish returns text without an empty frame');
  report.status = 'PASS';
} finally {
  await browser.close();
  fs.writeFileSync(path.join(output, 'checks.json'), JSON.stringify(report, null, 2) + '\n', { mode: 0o600 });
}
console.log(JSON.stringify({ status: report.status, checks: report.checks.length, captures: report.captures.length, geometries: report.geometries.length }));
