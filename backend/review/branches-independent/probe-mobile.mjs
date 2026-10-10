import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { chromium } from '../../../prototype/node_modules/@playwright/test/index.mjs';

const origin = process.env.Y3GYM_INDEPENDENT_ORIGIN;
assert(new URL(origin).hostname === 'localhost' && !['8767','8768'].includes(new URL(origin).port));
const output = new URL(process.env.Y3GYM_INDEPENDENT_PROBE_DIR || './mobile-probe/', import.meta.url);
await fs.mkdir(output, { recursive: true });
const report = { isolatedTestDatabase: true, origin, checks: [], measurements: [], errors: [], warnings: [], screenshots: [] };
const browser = await chromium.launch();
async function capture(page, name, fullPage = false) {
  await page.evaluate(async () => { await document.fonts.ready; });
  await page.screenshot({ path: new URL(name + '.png', output).pathname, fullPage });
  report.screenshots.push(name + '.png');
}
async function measure(page, name) {
  const measurement = await page.evaluate(() => {
    const selectors = ['#main', '#wagtail-sidebar', 'header', '#id_name', '#id_address', '#id_facilities-0-title', 'footer'];
    return { width: innerWidth, documentWidth: document.documentElement.scrollWidth, bodyClasses: document.body.className, elements: selectors.map(selector => {
      const e = document.querySelector(selector); if (!e) return { selector };
      const b = e.getBoundingClientRect(), s = getComputedStyle(e);
      return { selector, x:b.x, y:b.y, width:b.width, height:b.height, marginLeft:s.marginLeft, paddingLeft:s.paddingLeft, display:s.display, text:selector === 'header' ? e.innerText.slice(0,100) : undefined };
    }), panels: [...document.querySelectorAll('[data-side-panel-toggle]')].map(e => ({ name:e.dataset.sidePanelToggle, expanded:e.getAttribute('aria-expanded'), pressed:e.getAttribute('aria-pressed') })) };
  });
  report.measurements.push({ name, ...measurement });
  const input = measurement.elements.find(e => e.selector === '#id_name');
  if (input?.width < 230) report.warnings.push({ name, problem:'Narrow mobile name field', x:input.x, width:input.width });
  await capture(page, name);
}
async function login(context, editURL) {
  const page = await context.newPage();
  page.setDefaultTimeout(10000);
  page.on('pageerror', e => report.errors.push(e.message));
  await page.goto(`${origin}/admin/login/?next=${encodeURIComponent(editURL)}`);
  await page.locator('[name=username]').fill('cms-review-editor');
  await page.locator('[name=password]').fill(process.env.Y3GYM_INDEPENDENT_PASSWORD);
  await Promise.all([page.waitForNavigation(), page.locator('button[type=submit]').click()]);
  if (!(await page.locator('#id_name').count())) await page.goto(origin + editURL);
  await page.locator('#id_name').waitFor();
  return page;
}
async function saveAndPublish(page, name, editURL) {
  await page.locator('#id_name').fill(name);
  await page.locator('#id_address').fill(`${name} 주소 입력 확인`);
  await page.locator('#id_facilities-0-title').fill(`${name} 시설 입력 확인`);
  await page.locator('#id_facilities-0-image-chooser button[data-w-dropdown-target=toggle]').click();
  await page.locator('[data-chooser-action-choose]:visible').first().click();
  await page.locator('.modal-content a.image-choice').first().waitFor();
  await capture(page, name + '-image-chooser');
  await page.locator('.modal-content a.image-choice').first().click();
  await page.locator('#inline_child_facilities-2 [data-inline-panel-child-move-up]').click();
  await page.getByRole('button', { name:'초안 저장', exact:true }).scrollIntoViewIfNeeded();
  await capture(page, name + '-save-controls');
  await Promise.all([page.waitForNavigation(), page.getByRole('button', { name:'초안 저장', exact:true }).click()]);
  await page.goto(origin + editURL);
  assert.equal(await page.locator('#id_name').inputValue(), name);
  assert.equal(await page.locator('#id_address').inputValue(), `${name} 주소 입력 확인`);
  assert((await page.locator('[name^="facilities-"][name$="-title"]').evaluateAll(items => items.map(item => item.value))).includes(`${name} 시설 입력 확인`));
  await page.locator('footer button[data-w-dropdown-target=toggle]').click();
  await capture(page, name + '-publish-controls');
  await Promise.all([page.waitForNavigation(), page.locator('button[name=action-publish]').click()]);
  const response = await page.request.get(origin + '/branches/?branch=main');
  assert((await response.text()).includes(`${name} 주소 입력 확인`));
  report.checks.push({ name, result:'PASS', detail:'Mobile input, facility chooser/reorder, save/reopen and publish performed in temporary DB.' });
}
const editURL = `/admin/snippets/news/branch/edit/${process.env.Y3GYM_INDEPENDENT_MAIN_PK}/`;
try {
  const fresh = await browser.newContext({ viewport:{ width:375, height:812 } });
  const a = await login(fresh, editURL);
  await measure(a, 'A-fresh-mobile-direct');
  await saveAndPublish(a, 'A모바일검수', editURL);
  await fresh.close();
  const resized = await browser.newContext({ viewport:{ width:1440, height:900 } });
  const b = await login(resized, editURL);
  await b.setViewportSize({ width:375, height:812 });
  await measure(b, 'B-desktop-resize');
  await b.waitForTimeout(600);
  await measure(b, 'B-desktop-resize-settled');
  await b.reload();
  await measure(b, 'B-mobile-reload');
  await b.locator('button[data-side-panel-toggle=preview]').click();
  await b.frameLocator('iframe').first().locator('#branch-main').waitFor();
  await measure(b, 'B-preview-open');
  await b.locator('button[data-side-panel-toggle=preview]').click();
  await measure(b, 'B-preview-closed');
  const sidebarToggle = b.locator('button.sidebar-nav-toggle--mobile:visible');
  report.sidebarToggleCandidates = await sidebarToggle.count();
  if (await sidebarToggle.count()) {
    await sidebarToggle.first().click();
    await measure(b, 'B-sidebar-toggled');
    await sidebarToggle.first().click();
    await b.waitForTimeout(300);
  }
  await saveAndPublish(b, 'B모바일검수', editURL);
  await resized.close();

  const visitorContext = await browser.newContext({ viewport:{ width:375,height:812 } });
  await visitorContext.addInitScript(() => { window.open=()=>null; });
  const page = await visitorContext.newPage();
  page.on('pageerror', e => report.errors.push(e.message));
  for (const route of ['/', '/branches/', '/news/', `/news/${process.env.Y3GYM_INDEPENDENT_POST_PK}/`, `/popups/${process.env.Y3GYM_INDEPENDENT_POST_PK}/`]) {
    await page.goto(origin + route + '?branch=third-independent');
    await page.waitForFunction(() => new URL(location.href).searchParams.get('branch') === 'third-independent');
    assert.equal(await page.locator('[data-inquiry="channel"]:visible').count(), 0);
    const links = await page.locator('[data-branch-page], [data-popup-post], [data-news-link]').evaluateAll(items => items.map(a=>a.href));
    assert(links.length);
    for (const link of links) assert.equal(new URL(link).searchParams.get('branch'), 'third-independent', link);
    report.checks.push({ name:'third-branch-context', route, result:'PASS', links });
  }
  for (const route of ['/', '/branches/', '/news/']) {
    await page.goto(origin + route);
    assert.equal(new URL(page.url()).searchParams.get('branch'), 'third-independent');
    report.checks.push({ name:'same-tab-selection', route, result:'PASS' });
  }
  await page.goto(origin + '/branches/?branch=unknown');
  await page.locator('#tab-main[aria-selected=true]').waitFor();
  assert.equal(new URL(page.url()).searchParams.get('branch'), 'main');
  report.checks.push({ name:'invalid-id-overrides-saved-choice', result:'PASS' });
  await visitorContext.close();
  assert.equal(report.errors.length, 0);
  report.status = report.warnings.length ? 'PASS_WITH_WARNINGS' : 'PASS';
} catch (e) { report.status='FAIL'; report.failure=e.stack; process.exitCode=1; }
finally {
  await fs.writeFile(new URL('checks.json', output), JSON.stringify(report,null,2)+'\n');
  await browser.close();
}
console.log(JSON.stringify({ status:report.status, checks:report.checks.length, warnings:report.warnings, failure:report.failure }));
