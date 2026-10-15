import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {chromium, expect} from '../../../prototype/node_modules/@playwright/test/index.mjs';

const here=path.dirname(new URL(import.meta.url).pathname),work=path.resolve(process.argv[2]);
assert(work.startsWith('/tmp/y3gym-image-focus-independent-'));
const spec=JSON.parse(await fs.readFile(path.join(work,'instance.json')));
assert.equal(spec.origin,'http://localhost:8770');assert(spec.database.startsWith('test_y3gym_focus_ind_'));
const credentials=JSON.parse(await fs.readFile(path.join(work,'.local-credentials')));
const out=path.join(here,process.argv[3]);assert(/^[a-z][a-z0-9-]+$/.test(process.argv[3]));await fs.mkdir(out);
const result={checks:[],events:[],errors:[],external:[],captures:[]};let phase='setup';
const browser=await chromium.launch(),context=await browser.newContext({viewport:{width:1440,height:1000}});
await context.route('**/*',r=>{const u=new URL(r.request().url());if(u.origin!==spec.origin){result.external.push({phase,origin:u.origin});return r.abort();}return r.continue();});
const page=await context.newPage();page.setDefaultTimeout(10000);
page.on('pageerror',e=>result.errors.push({phase,message:e.message}));
page.on('console',e=>{if(e.type()==='error')result.errors.push({phase,message:e.text()});});
const flush=()=>fs.writeFile(path.join(out,'result.json'),JSON.stringify(result,null,2)+'\n');
const note=label=>page.evaluate(label=>window.__note(label),label);
const check=async(name,evidence={})=>{result.checks.push({name,status:'PASS',evidence});await flush();};
const editor=()=>page.locator('.public-DraftEditor-content');
const title='[TEST] W02 후속 확인 한국어 제목',body='[TEST] 수정 중 한국어 본문과 이미지 선택 내용을 보존합니다.';
const original=JSON.parse(await fs.readFile(path.join(work,'original-image.json'))).id;
async function preserved(){
  assert.equal(await page.locator('#id_title').inputValue(),title);
  assert((await editor().innerText()).includes(body));
  const raw=await page.locator('#id_body').evaluate(e=>{e.draftailEditor.saveState();return e.value;});
  assert(raw.includes(body),'Serialized Draftail content must preserve Korean text');
}
async function shown(){await page.waitForFunction(()=>{const m=document.querySelector('.modal');return m&&window.__shown.has(m);});}
async function openCover(){
  const w=page.locator('#id_cover_image-chooser');
  if(await page.locator('#id_cover_image').inputValue())await w.locator('[data-w-dropdown-target=toggle]').click();
  await w.locator('[data-chooser-action-choose]:visible').click();
  await page.locator('#tab-label-upload').waitFor();
}
async function point(locator,downOnly=false){if(!downOnly)return locator.click({force:true});const b=await locator.boundingBox();assert(b);await page.mouse.move(b.x+b.width/2,b.y+b.height/2);await page.mouse.down();}
async function closed(){await page.locator('.modal').waitFor({state:'detached'});await preserved();return page.evaluate(()=>{const a=document.activeElement;return {tag:a.tagName,id:a.id,connected:a.isConnected,visible:!!a.getClientRects().length,inChooser:!!a.closest('[id$="-chooser"]'),inEditor:!!a.closest('.Draftail-Editor'),role:a.getAttribute('role')};});}
async function escape(){await page.keyboard.press('Escape');return closed();}
async function upload(){
  await page.locator('#tab-label-upload').click();
  await page.locator('#id_image-chooser-upload-file').setInputFiles(path.join(work,'fixture.png'));
  await page.locator('#id_image-chooser-upload-title').fill('[TEST] W02 관련 중복');
  await page.locator('.modal button[type=submit]').click();await page.locator('.duplicate-upload:visible').waitFor();
}
async function openBody(){
  await editor().click();await page.keyboard.press('Control+End');await page.keyboard.press('Enter');
  await page.getByRole('button',{name:'Insert a block',exact:true}).click();
  await page.getByRole('option',{name:'이미지',exact:true}).click();await page.locator('#tab-label-upload').waitFor();
}
try{
  await page.goto(spec.origin+'/admin/login/');await page.locator('[name=username]').fill(spec.username);await page.locator('[name=password]').fill(credentials[spec.username]);
  await Promise.all([page.waitForNavigation(),page.getByRole('button',{name:'로그인',exact:true}).click()]);
  await page.goto(spec.origin+'/admin/snippets/news/post/add/');await page.locator('#id_title').fill(title);
  await editor().click();await page.keyboard.insertText(body);await preserved();
  await page.evaluate(()=>{
    window.__events=[];window.__shown=new WeakSet();window.__hiding=new WeakSet();window.__hidden=new WeakSet();window.__ids=new WeakMap();let next=0;
    const desc=e=>e&&({tag:e.tagName,id:e.id,role:e.getAttribute?.('role'),name:e.getAttribute?.('name'),connected:e.isConnected});
    window.__note=(event,target=document.activeElement,extra={})=>{
      const m=target?.closest?.('.modal')||document.querySelector('.modal');if(m&&!window.__ids.has(m))window.__ids.set(m,++next);
      const row={event,ms:performance.now(),modal:m?window.__ids.get(m):null,connected:m?.isConnected,shown:!!(m&&window.__shown.has(m)),bsShown:!!(m&&jQuery(m).data('bs.modal')?.isShown),active:desc(document.activeElement),target:desc(target),...extra,
        tabs:[...(m?.querySelectorAll('[role=tab]')||[])].map(e=>({id:e.id,selected:e.getAttribute('aria-selected'),tabindex:e.getAttribute('tabindex'),controls:e.getAttribute('aria-controls')})),
        panels:[...(m?.querySelectorAll('[role=tabpanel]')||[])].map(e=>({id:e.id,hidden:e.hidden,visible:!!e.getClientRects().length}))};window.__events.push(row);return row;
    };
    const trigger=jQuery.fn.trigger;
    jQuery.fn.trigger=function(event,...args){const name=typeof event==='string'?event:event.type;if(this[0]?.matches?.('.modal')&&/^(show|shown|hide|hidden|focus)(\.|$)/.test(name))window.__note('trigger:'+name,this[0]);return trigger.call(this,event,...args);};
    const focus=HTMLElement.prototype.focus;
    HTMLElement.prototype.focus=function(...args){window.__note('native.focus',this);return focus.apply(this,args);};
    jQuery(document).on('show.bs.modal shown.bs.modal hide.bs.modal hidden.bs.modal',e=>{if(e.type==='shown')window.__shown.add(e.target);if(e.type==='hide')window.__hiding.add(e.target);if(e.type==='hidden')window.__hidden.add(e.target);window.__note(e.type+'.bs.modal',e.target);});
    for(const type of ['keydown','pointerdown','pointerup','focusin','focusout'])document.addEventListener(type,e=>window.__note(type,e.target,{key:e.key,trusted:e.isTrusted}),true);
  });
  // Establish the existing representative image in this fresh editor.
  await openCover();
  const choice=page.locator(`a[data-chooser-modal-choice][href$="/${original}/"]`);
  for(let i=0;!await choice.count();i++){
    assert(i<20,'Original synthetic image must remain available');
    const next=page.locator('.modal .pagination .next a[href]');
    const number=new URL(await next.getAttribute('href'),spec.origin).searchParams.get('p');
    await next.click();await expect(page.locator('.modal .pagination [aria-current=page]')).toHaveText(number);
  }
  await choice.click();await closed();

  phase='cover duplicate close';
  const beforeCover=await page.locator('#id_cover_image').inputValue();
  await openCover();await upload();
  await page.locator('.modal button.close').click();const duplicateRestore=await closed();
  assert.equal(await page.locator('#id_cover_image').inputValue(),beforeCover);
  assert(duplicateRestore.connected&&duplicateRestore.visible&&duplicateRestore.inChooser);
  assert.equal(await page.locator('.modal-backdrop').count(),0);
  await check('representative duplicate close preserves image/title/body and same widget',duplicateRestore);

  phase='internal Escape starts hide then immediate programmatic reopen';
  await openCover();await point(page.locator('.modal input[name=q]'));
  const old=await page.evaluate(()=>{window.__oldEscape=document.querySelector('.modal');window.__oldEscapeBackdrop=jQuery(window.__oldEscape).data('bs.modal')?.$backdrop?.[0];return window.__note('before actual internal Escape');});
  assert.equal(old.shown,false,'Escape early-input setup must precede shown');
  await page.keyboard.press('Escape');
  assert(await page.evaluate(()=>window.__hiding.has(window.__oldEscape)&&!window.__hidden.has(window.__oldEscape)),'Internal trusted Escape must actually start hide before hidden');
  await page.evaluate(()=>{window.__note('QA programmatic reopen after real Escape hide');const w=document.querySelector('#id_cover_image-chooser');w.querySelector('[data-w-dropdown-target=toggle]').focus();w.querySelector('[data-chooser-action-choose]').click();});
  await page.locator('#tab-label-upload').waitFor();await point(page.locator('.modal input[name=q]'));
  const early=await page.evaluate(()=>({oldConnected:window.__oldEscape.isConnected,oldHiddenHandlers:jQuery._data(window.__oldEscape,'events')?.hidden?.length||0,oldBackdropConnected:window.__oldEscapeBackdrop?.isConnected,backdrops:document.querySelectorAll('.modal-backdrop').length,newBackdropDistinct:jQuery(document.querySelector('.modal')).data('bs.modal')?.$backdrop?.[0]!==window.__oldEscapeBackdrop,focus:window.__note('new actual pointer after Escape reopen')}));
  assert.equal(early.oldConnected,false);assert.equal(early.oldHiddenHandlers,0);assert.equal(early.oldBackdropConnected,false);assert(early.newBackdropDistinct);assert.equal(early.backdrops,1);assert.equal(early.focus.shown,false);
  await shown();await page.waitForTimeout(200);
  await expect(page.locator('.modal input[name=q]')).toBeFocused();
  const restore=await escape();assert(restore.inChooser&&restore.connected&&restore.visible);assert.equal(await page.locator('.modal-backdrop').count(),0);
  await openCover();await shown();const next=await escape();assert(next.inChooser&&next.connected&&next.visible);assert.equal(await page.locator('.modal-backdrop').count(),0);
  await check('trusted internal Escape hide, before-hidden reopen, owned backdrop cleanup and next normal cycle',{old,early,restore,next});
  assert.equal(result.errors.length,0);assert.equal(result.external.length,0);result.status='PASS';
}catch(e){result.status='FAIL';result.failure={phase,message:e.stack};process.exitCode=1;}
finally{result.events=await page.evaluate(()=>window.__events||[]).catch(()=>[]);await flush();await browser.close();}
console.log(JSON.stringify({status:result.status,checks:result.checks.length,errors:result.errors.length,external:result.external.length}));
