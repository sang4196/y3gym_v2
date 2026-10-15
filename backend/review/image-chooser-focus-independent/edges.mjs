import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {chromium} from '../../../prototype/node_modules/@playwright/test/index.mjs';

const work=path.resolve(process.argv[2]),mode=process.argv[3],label=process.argv[4];
assert(work.startsWith('/tmp/y3gym-image-focus-independent-'));assert(['without','with'].includes(mode));assert(/^[a-z][a-z0-9-]+$/.test(label));
const spec=JSON.parse(await fs.readFile(path.join(work,'instance.json')));assert.equal(spec.origin,'http://localhost:8770');
assert(spec.database.startsWith('test_y3gym_focus_ind_'));
const credentials=JSON.parse(await fs.readFile(path.join(work,'.local-credentials')));
const original=JSON.parse(await fs.readFile(path.join(work,'original-image.json'))).id;
const out=path.join(path.dirname(new URL(import.meta.url).pathname),label);await fs.mkdir(out);
const result={mode,events:[],cases:[],errors:[],external:[]};
const navigation=process.argv[5]||'Tab';assert(['Tab','Shift+Tab'].includes(navigation));result.navigation=navigation;
const setupOutside=['outside-search','outside-tab'].includes(process.argv[6]);result.programmaticSequentialStartSetup=setupOutside?process.argv[6]:false;
const setupSelector=process.argv[6]==='outside-tab'?'#tab-label-search':'.modal input[name=q]';
const browser=await chromium.launch(),context=await browser.newContext({viewport:{width:1440,height:1000}});
await context.route('**/*',async r=>{const u=new URL(r.request().url());if(u.origin!==spec.origin){result.external.push(u.origin);return r.abort();}if(mode==='without'&&u.pathname==='/static/news/admin-image-chooser-focus.js')return r.fulfill({contentType:'text/javascript',body:'/* QA ablation: omit only new project guard */'});return r.continue();});
const page=await context.newPage();page.setDefaultTimeout(10000);page.on('pageerror',e=>result.errors.push(e.message));
const snap=()=>page.evaluate(()=>window.__snap());
try{
  await page.goto(spec.origin+'/admin/login/');await page.locator('[name=username]').fill(spec.username);await page.locator('[name=password]').fill(credentials[spec.username]);
  await Promise.all([page.waitForNavigation(),page.getByRole('button',{name:'로그인',exact:true}).click()]);await page.goto(spec.origin+'/admin/snippets/news/post/add/');
  await page.evaluate(()=>{
    window.__events=[];window.__shown=new WeakSet();window.__hiding=new WeakSet();window.__hidden=new WeakSet();let n=0;const ids=new WeakMap();
    const d=e=>e&&({tag:e.tagName,id:e.id,connected:e.isConnected,inModal:!!e.closest?.('.modal'),visible:!!e.getClientRects().length,html:e.outerHTML?.slice(0,900)});
    window.__snap=()=>({active:d(document.activeElement),backdrops:document.querySelectorAll('.modal-backdrop').length,bodyModalOpen:document.body.classList.contains('modal-open'),modal:[...document.querySelectorAll('.modal')].map(m=>({id:ids.get(m),shown:window.__shown.has(m),bsShown:jQuery(m).data('bs.modal')?.isShown,ownFocus:Object.hasOwn(m,'focus')}))});
    const log=(event,target,extra={})=>{const m=target?.closest?.('.modal')||document.querySelector('.modal');if(m&&!ids.has(m))ids.set(m,++n);window.__events.push({event,ms:performance.now(),target:d(target),...window.__snap(),...extra});};
    jQuery(document).on('show.bs.modal shown.bs.modal hide.bs.modal hidden.bs.modal',e=>{if(e.type==='shown')window.__shown.add(e.target);if(e.type==='hide')window.__hiding.add(e.target);if(e.type==='hidden')window.__hidden.add(e.target);log(e.type,e.target);});
    for(const t of ['keydown','pointerdown','click','focusin'])document.addEventListener(t,e=>log(t,e.target,{key:e.key,trusted:e.isTrusted}),true);
    const focus=HTMLElement.prototype.focus;HTMLElement.prototype.focus=function(...args){log('native.focus',this);return focus.apply(this,args);};
  });
  await page.locator('#id_cover_image-chooser [data-chooser-action-choose]:visible').click();await page.locator('#tab-label-upload').waitFor();
  if(setupOutside)await page.locator(setupSelector).evaluate(e=>{window.__events.push({event:'QA programmatic sequential start focus+blur',ms:performance.now(),selector:e.id});e.focus();e.blur();});
  const firstBefore=await snap();await page.keyboard.press(navigation);const firstEarly=await snap();await page.evaluate(()=>{window.__early=document.activeElement;});
  await page.waitForFunction(()=>{const m=document.querySelector('.modal');return m&&window.__shown.has(m);});const firstLate=await snap();firstLate.sameAsEarly=await page.evaluate(()=>document.activeElement===window.__early);
  await page.keyboard.press('Escape');await page.locator('.modal').waitFor({state:'detached'});const firstClose=await snap();
  result.cases.push({name:'first Tab from outside on empty chooser',before:firstBefore,early:firstEarly,late:firstLate,close:firstClose});
  await page.locator('#id_cover_image-chooser [data-chooser-action-choose]:visible').click();await page.locator('#tab-label-upload').waitFor();
  const choice=page.locator(`a[data-chooser-modal-choice][href$="/${original}/"]`);
  for(let i=0;!await choice.count();i++){assert(i<20);const next=page.locator('.modal .pagination .next a[href]');const number=new URL(await next.getAttribute('href'),spec.origin).searchParams.get('p');await next.click();await page.locator('.modal .pagination [aria-current=page]').filter({hasText:number}).waitFor();}
  await choice.click();await page.locator('.modal').waitFor({state:'detached'});
  await page.locator('#id_cover_image-chooser [data-w-dropdown-target=toggle]').click();
  const action=page.locator('#id_cover_image-chooser [data-chooser-action-choose]:visible');
  result.opener=await action.evaluate(e=>({html:e.outerHTML,parents:[e.parentElement?.outerHTML?.slice(0,3500)],widget:document.querySelector('#id_cover_image-chooser').outerHTML.slice(0,5000)}));
  await action.click();await page.locator('#tab-label-upload').waitFor();
  if(setupOutside)await page.locator(setupSelector).evaluate(e=>{window.__events.push({event:'QA programmatic sequential start focus+blur',ms:performance.now(),selector:e.id});e.focus();e.blur();});
  const chosenBefore=await snap();await page.keyboard.press(navigation);const chosenEarly=await snap();await page.evaluate(()=>{window.__early=document.activeElement;});
  await page.waitForFunction(()=>{const m=document.querySelector('.modal');return m&&window.__shown.has(m);});const chosenLate=await snap();chosenLate.sameAsEarly=await page.evaluate(()=>document.activeElement===window.__early);
  await page.keyboard.press('Escape');await page.locator('.modal').waitFor({state:'detached'});const chosenClose=await snap();
  result.cases.push({name:'first Tab from outside on dropdown chooser and normal Escape',before:chosenBefore,early:chosenEarly,late:chosenLate,close:chosenClose});
  if(process.argv[6]==='rapid'){
    await page.locator('#id_cover_image-chooser [data-w-dropdown-target=toggle]').click();await action.click();await page.locator('#tab-label-upload').waitFor();
    await page.evaluate(()=>{window.__old=document.querySelector('.modal');});const before=await snap();const closeBox=await page.locator('.modal button.close').boundingBox();await page.mouse.click(closeBox.x+closeBox.width/2,closeBox.y+closeBox.height/2);
    assert(await page.evaluate(()=>window.__hiding.has(window.__old)&&!window.__hidden.has(window.__old)));
    await page.evaluate(()=>{const w=document.querySelector('#id_cover_image-chooser');w.querySelector('[data-w-dropdown-target=toggle]').focus();w.querySelector('[data-chooser-action-choose]').click();});
    await page.locator('#tab-label-upload').waitFor();const q=page.locator('.modal input[name=q]'),b=await q.boundingBox();await page.mouse.click(b.x+b.width/2,b.y+b.height/2);
    const early=await snap();const generations=await page.evaluate(()=>({oldConnected:window.__old.isConnected,different:window.__old!==document.querySelector('.modal'),oldHiddenHandlers:jQuery._data(window.__old,'events')?.hidden?.length||0}));
    await page.waitForFunction(()=>window.__shown.has(document.querySelector('.modal')));await page.waitForTimeout(200);const late=await snap();
    await page.keyboard.press('Escape');await page.locator('.modal').waitFor({state:'detached'});const close=await snap();result.cases.push({name:'rapid reopen before old hidden',before,early,late,close,generations});
    if(mode==='with'){
      assert.equal(close.backdrops,0);assert.equal(close.active.tag,'BUTTON');assert(close.active.html.includes('data-w-dropdown-target="toggle"'));
      await page.locator('#id_cover_image-chooser [data-w-dropdown-target=toggle]').click();await action.click();await page.locator('#tab-label-upload').waitFor();
      await page.waitForFunction(()=>window.__shown.has(document.querySelector('.modal')));await page.keyboard.press('Escape');await page.locator('.modal').waitFor({state:'detached'});
      const subsequent=await snap();assert.equal(subsequent.backdrops,0);assert(subsequent.active.html.includes('data-w-dropdown-target="toggle"'));result.cases.push({name:'normal reopen after rapid cycle restores same persistent widget',close:subsequent});
    }
  }
  result.eligibleCases=result.cases.filter(c=>c.before.active.tag==='BODY'&&!c.before.modal[0].shown&&!c.early.modal[0].shown&&c.early.active.id==='id_q');
  result.ineligibleCount=result.cases.length-result.eligibleCases.length;
  assert(result.eligibleCases.length>0,'Outside-Tab early internal entry condition not met');
  if(mode==='with'){assert(result.eligibleCases.every(c=>c.late.sameAsEarly),'Early entered input focus lost');result.status='PASS';}
  else{result.focusLosses=result.eligibleCases.filter(c=>!c.late.sameAsEarly).length;result.status=result.focusLosses?'REPRODUCED':'NOT_REPRODUCED';}
}catch(e){result.status='FAIL';result.failure=e.stack;process.exitCode=1;}
finally{result.events=await page.evaluate(()=>window.__events||[]).catch(()=>[]);await fs.writeFile(path.join(out,'result.json'),JSON.stringify(result,null,2)+'\n');await browser.close();}
console.log(JSON.stringify({status:result.status,mode,cases:result.cases.length,errors:result.errors.length,external:result.external.length}));
