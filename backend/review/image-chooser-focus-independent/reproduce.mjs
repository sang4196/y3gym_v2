import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium, expect } from '../../../prototype/node_modules/@playwright/test/index.mjs';

const here = path.dirname(new URL(import.meta.url).pathname);
const work = path.resolve(process.argv[2]);
assert(work.startsWith('/tmp/y3gym-image-focus-independent-'));
const spec = JSON.parse(await fs.readFile(path.join(work, 'instance.json')));
assert.equal(spec.origin, 'http://localhost:8770');
assert(spec.database.startsWith('test_y3gym_focus_ind_'));
const credentials = JSON.parse(await fs.readFile(path.join(work, '.local-credentials')));
const mode = process.argv[3]; assert(['ablation', 'final'].includes(mode));
const label = process.argv[4] || mode + '-01'; assert(/^[a-z][a-z0-9-]+$/.test(label));
const output = path.join(here, label); await fs.mkdir(output);
const result = {comparison:'Final project JS omitted by QA route versus real final code; not upstream A/B', mode, attempts: [], errors: [], external: [], captures: [], events: []};
const browser = await chromium.launch();
const context = await browser.newContext({viewport: {width: 1440, height: 1000}});
await context.route('**/*', route => {
  const url = new URL(route.request().url());
  if (url.origin !== spec.origin) {result.external.push(url.origin); return route.abort();}
  if (mode === 'ablation' && url.pathname === '/static/news/admin-image-chooser-focus.js') { result.ablationHits = (result.ablationHits || 0) + 1; return route.fulfill({contentType:'text/javascript', body:'/* QA ablation: omit only final project image-focus JS */'}); }
  return route.continue();
});
const page = await context.newPage(); page.setDefaultTimeout(12000);
page.on('pageerror', e => result.errors.push({kind: 'pageerror', message: e.message}));
page.on('console', e => {if (e.type() === 'error') result.errors.push({kind: 'console', message: e.text()});});
const title = '[TEST] W02 작성 중 한국어 제목';
const body = '[TEST] 선택기 닫기와 재열기 뒤에도 이 한국어 본문을 보존합니다.';
const flush = () => fs.writeFile(path.join(output, 'result.json'), JSON.stringify(result, null, 2) + '\n');
async function openCover() {
  const widget = page.locator('#id_cover_image-chooser');
  if (await page.locator('#id_cover_image').inputValue()) await widget.locator('button[data-w-dropdown-target="toggle"]').click();
  await widget.locator('[data-chooser-action-choose]:visible').click();
  await page.getByRole('tab', {name: '업로드', exact: true}).waitFor();
}
async function upload() {
  await page.getByRole('tab', {name: '업로드', exact: true}).click();
  await page.locator('#id_image-chooser-upload-file').setInputFiles(path.join(work, 'fixture.png'));
  await page.locator('#id_image-chooser-upload-title').fill('[TEST] W02 중복 fixture');
  await page.locator('.modal button[type="submit"]').click();
}
async function close() {
  await page.locator('.modal:visible button.close').click();
  await page.locator('.modal').waitFor({state: 'detached'});
}
try {
  await page.goto(spec.origin + '/admin/login/');
  await page.locator('[name=username]').fill(spec.username);
  await page.locator('[name=password]').fill(credentials[spec.username]);
  await Promise.all([page.waitForNavigation(), page.getByRole('button', {name: '로그인', exact: true}).click()]);
  await page.goto(spec.origin + '/admin/snippets/news/post/add/');
  await page.locator('#id_title').fill(title);
  await page.locator('.public-DraftEditor-content').fill(body);
  await page.evaluate(() => {
    const ids = new WeakMap(), states = new WeakMap(); let next = 0;
    window.__focusEvents = [];
    const el = node => node && ({tag: node.tagName, id: node.id, role: node.getAttribute?.('role'), name: node.getAttribute?.('name')});
    window.__focusRecord = (event, target = document.activeElement, detail = {}) => {
      const modal = target?.closest?.('.modal') || document.querySelector('.modal');
      if (modal && !ids.has(modal)) ids.set(modal, ++next);
      const state = modal && states.get(modal);
      const row = {event, ms: performance.now(), modal: modal ? ids.get(modal) : null, generation: state?.generation, phase: state?.phase,
        active: el(document.activeElement), target: el(target), connected: modal?.isConnected, bsShown: !!(modal && window.jQuery(modal).data('bs.modal')?.isShown), ...detail,
        tabs: [...(modal?.querySelectorAll('[role=tab]') || [])].map(t => ({id:t.id, selected:t.getAttribute('aria-selected'), tabindex:t.getAttribute('tabindex'), controls:t.getAttribute('aria-controls')})),
        panels: [...(modal?.querySelectorAll('[role=tabpanel]') || [])].map(p => ({id:p.id, hidden:p.hidden, visible:!!p.getClientRects().length}))};
      window.__focusEvents.push(row); return row;
    };
    window.jQuery(document).on('show.bs.modal shown.bs.modal hide.bs.modal hidden.bs.modal', function(e) {
      if (!e.target.matches('.modal')) return;
      let state = states.get(e.target) || {generation: 0};
      if (e.type === 'show' && !window.jQuery(e.target).data('bs.modal')?.isShown) {state.generation++;state.phase='opening';}
      else if (e.type !== 'show') state.phase = e.type;
      states.set(e.target, state); window.__focusRecord(e.type + '.bs.modal', e.target);
    });
    for (const type of ['focusin','focusout','keydown','pointerdown','pointerup','w-tabs:ready','w-tabs:selected','w-focus:focus'])
      document.addEventListener(type, e => window.__focusRecord(type, e.target, {key:e.key, trusted:e.isTrusted}), true);
    new MutationObserver(records => {
      for (const record of records) if (record.type === 'attributes' && record.target.closest?.('.modal')) {
        window.__focusRecord('attribute:' + record.attributeName, record.target);
      }
    }).observe(document.body,{subtree:true,attributes:true,attributeFilter:['aria-selected','tabindex','hidden']});
  });
  if (mode === 'ablation') {
    await openCover(); await upload();
    await page.locator('.modal').waitFor({state: 'detached'});
    result.originalCover = await page.locator('#id_cover_image').inputValue(); assert(result.originalCover);
    await fs.writeFile(path.join(work, 'original-image.json'), JSON.stringify({id:result.originalCover}));
  } else {
    result.originalCover = JSON.parse(await fs.readFile(path.join(work, 'original-image.json'))).id;
    await openCover();
    const choice = page.locator(`a[data-chooser-modal-choice][href$="/${result.originalCover}/"]`);
    for (let i = 0; !await choice.count(); i++) {
      assert(i < 20, 'Original synthetic image must remain available');
      const next = page.locator('.modal .pagination .next a[href]');
      const number = new URL(await next.getAttribute('href'), spec.origin).searchParams.get('p');
      await next.click();
      await expect(page.locator('.modal .pagination [aria-current=page]')).toHaveText(number);
    }
    await choice.click();
    await page.locator('.modal').waitFor({state: 'detached'});
  }
  const attempts=Number(process.argv[5] || 4);assert(Number.isInteger(attempts)&&attempts>=1&&attempts<=4);
  for (let i=0; i<attempts; i++) {
    await openCover(); await upload(); await page.locator('.duplicate-upload:visible').waitFor(); await close();
    await openCover();
    const attempt = {eventStart: await page.evaluate(() => window.__focusEvents.length), name:'duplicate-close-immediate-reopen-'+i, keys:[], setup:'programmatic search.focus(), followed by real trusted keyboard', status:'RUNNING'};
    result.attempts.push(attempt);
    const search = page.getByRole('tab',{name:'검색',exact:true}), uploadTab = page.getByRole('tab',{name:'업로드',exact:true});
    attempt.before = await page.evaluate(() => {window.__focusRecord('QA programmatic setup focus');document.querySelector('#tab-label-search').focus();return window.__focusRecord('before actual keyboard');});
    for (const [key,target] of [['End',uploadTab],['Home',search],['ArrowRight',uploadTab],['ArrowLeft',search]]) {
      await page.keyboard.press(key);
      try {
        await expect(target).toHaveAttribute('aria-selected','true',{timeout:900});
        await expect(target).toBeFocused({timeout:900});
        const shape=await page.locator('.modal').evaluate(m=>{const tabs=[...m.querySelectorAll('[role=tab]')];const selected=tabs.filter(t=>t.getAttribute('aria-selected')==='true');return {count:selected.length, panels:[...m.querySelectorAll('[role=tabpanel]')].map(p=>({id:p.id,hidden:p.hidden,visible:!!p.getClientRects().length})), selected:selected[0]?.getAttribute('aria-controls')};});
        assert.equal(shape.count,1);for(const panel of shape.panels){assert.equal(panel.hidden,panel.id!==shape.selected);assert.equal(panel.visible,panel.id===shape.selected);}
        attempt.keys.push({key,status:'PASS'});
      } catch(e) {attempt.keys.push({key,status:'FAIL',message:e.message});attempt.status='FAIL';break;}
    }
    // Observe completion AFTER the user's early input; never wait for shown before it.
    await page.waitForFunction(() => window.__focusEvents.some(e => e.event === 'shown.bs.modal' && e.modal === window.__focusEvents.at(-1).modal));
    attempt.after = await page.evaluate(() => window.__focusRecord('after initial completion'));
    const events = await page.evaluate(start => window.__focusEvents.slice(start), attempt.eventStart);
    const firstKey = events.find(e => e.event === 'keydown' && e.key === 'End');
    attempt.firstTrustedKey = firstKey;
    attempt.earlyEligible = firstKey?.trusted === true && firstKey.phase === 'opening';
    attempt.rootFocusIntrusions = events.filter(e => e.event === 'focusin' && e.target?.role === 'dialog' && e.ms > firstKey?.ms && e.phase === 'opening');
    attempt.timeline = events;
    if (!attempt.earlyEligible) attempt.status = 'CONDITION_NOT_MET';
    if (attempt.after.active?.role === 'dialog') attempt.status='FAIL';
    if (attempt.status === 'RUNNING') attempt.status='PASS';
    if (i===0 || attempt.status==='FAIL') {
      const name=`attempt-${i}.png`;await page.locator('.modal-content').screenshot({path:path.join(output,name)});result.captures.push(name);
    }
    await close();
    assert.equal(await page.locator('#id_title').inputValue(),title);
    assert((await page.locator('.public-DraftEditor-content').innerText()).includes(body));
    await flush();
  }
  result.losses = result.attempts.filter(a => a.status === 'FAIL' && a.earlyEligible).length;
  result.eligible = result.attempts.filter(a => a.earlyEligible).length;
  result.rootIntrusionAttempts = result.attempts.filter(a => a.earlyEligible && a.rootFocusIntrusions.length).length;
  assert(result.eligible>0,'No valid original early-input attempt; do not claim resolution.');
  result.ineligible = result.attempts.length - result.eligible;
  assert.equal(result.errors.length,0);assert.equal(result.external.length,0);
  if (mode==='ablation') {assert(result.losses>0 || result.rootIntrusionAttempts>0,'Original race not reproduced; do not claim full resolution.');result.status='REPRODUCED';}
  else {assert.equal(result.losses,0);assert.equal(result.rootIntrusionAttempts,0);result.status='PASS';}
} catch(e) {result.status='ERROR';result.failure=e.stack;process.exitCode=1;}
finally {result.events=await page.evaluate(() => window.__focusEvents || []).catch(()=>[]);await flush();await browser.close();}
console.log(JSON.stringify({mode,status:result.status,attempts:result.attempts.length,losses:result.losses,errors:result.errors.length,external:result.external.length}));
