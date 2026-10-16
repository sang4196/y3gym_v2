// Import/transport adaptation only. No assertions, waits, or browser modes change.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import childProcess from 'node:child_process';
import crypto from 'node:crypto';
import { chromium as original, expect } from '../../prototype/node_modules/@playwright/test/index.mjs';

const origin = ['Y3GYM_BRAND_REVIEW_ORIGIN', 'Y3GYM_BRANCH_REVIEW_ORIGIN', 'Y3GYM_TRAINER_REVIEW_ORIGIN', 'Y3GYM_HOME_NEWS_ORIGIN']
  .map(key => process.env[key]).find(Boolean) || process.env.Y3GYM_QA_ORIGIN;
assert(origin, 'Private campaign origin required');
const allowed = new URL(origin);
const dockerTLS = process.env.Y3GYM_QA_DOCKER === '1';
if (dockerTLS) {
  const run = process.env.Y3GYM_QA_RUN_DIR;
  const marker = JSON.parse(fs.readFileSync(path.join(run, 'owner.json'), 'utf8'));
  const manifest = JSON.parse(fs.readFileSync(path.join(run, 'manifest.json'), 'utf8'));
  assert.equal(marker.token, process.env.Y3GYM_QA_RUN_TOKEN);
  assert.equal(manifest.resource_backend, 'docker');
  assert.equal(allowed.hostname, `qa-${process.env.Y3GYM_QA_RUN_ID.split('-').at(-1)}.test`);
  assert.equal(allowed.protocol, 'https:');
} else assert(allowed.hostname === 'localhost' && allowed.protocol === 'http:');
assert(process.env.Y3GYM_QA_RUN_ID && process.env.Y3GYM_QA_RUN_TOKEN, 'Managed run required');
assert(!['8767','8768','8769','8772','8773','8774','8775','8776','8780','8781'].includes(allowed.port), 'Existing review server blocked');
const permit = value => {
  const url = new URL(typeof value === 'string' ? value : value.url(), origin);
  assert.equal(url.origin, allowed.origin, 'External/protected transport blocked');
};
const launch = original.launch.bind(original);
const chromium = new Proxy(original, { get(target, name) {
  if (name !== 'launch') return Reflect.get(target, name);
  return async (...args) => {
    const run=process.env.Y3GYM_QA_RUN_DIR,token=process.env.Y3GYM_QA_RUN_TOKEN;
    const born=[];
    const event=(payload)=>{
      const payload_json=JSON.stringify(payload),signature=crypto.createHmac('sha256',token).update(payload_json).digest('hex');
      const file=path.join(run,'output/browser-processes.jsonl');
      const fd=fs.openSync(file,fs.constants.O_WRONLY|fs.constants.O_CREAT|fs.constants.O_APPEND|fs.constants.O_NOFOLLOW,0o600);
      try{fs.writeSync(fd,JSON.stringify({payload_json,signature})+'\n');}finally{fs.closeSync(fd);}
    };
    const spawn=childProcess.spawn;
    childProcess.spawn=function(command,argv,options){
      const profile=argv?.find(v=>v.startsWith('--user-data-dir='))?.slice('--user-data-dir='.length);
      if(profile){
        assert(options.env?.Y3GYM_QA_RUN_TOKEN===token,'Browser spawn requires own run token');
        assert(path.resolve(profile).startsWith(path.join(run,'tmp')+path.sep),'Browser profile must stay in run');
      }
      const child=spawn.call(this,command,argv,options);
      if(profile&&child.pid){
        const raw=fs.readFileSync(`/proc/${child.pid}/stat`,'utf8');
        const record={pid:child.pid,start_ticks:Number(raw.slice(raw.lastIndexOf(')')+2).split(' ')[19]),cwd:options.cwd||process.cwd(),exe:fs.realpathSync(command),argv_sha256:crypto.createHash('sha256').update([command,...argv,''].join('\0')).digest('hex'),uid:process.getuid(),boot_id:fs.readFileSync('/proc/sys/kernel/random/boot_id','utf8').trim()};
        if (dockerTLS) record.pid_namespace = 'owned-docker';
        const observed={...record,profile};born.push(observed);event({event:'spawn',record});
        child.once('exit',()=>event({event:'exit',pid:child.pid,start_ticks:record.start_ticks}));
      }
      return child;
    };
    let browser;
    try{browser=await launch(...args);}finally{childProcess.spawn=spawn;}
    try{
      assert.equal(born.length,1,'One locally spawned Chromium process required');
      assert.equal(path.resolve(os.tmpdir()),path.join(run,'tmp'));
      const observed=born[0];
      fs.appendFileSync(path.join(run,'output/browser-runtime.jsonl'),JSON.stringify({...observed,tmpdir:os.tmpdir(),browserCache:process.env.PLAYWRIGHT_BROWSERS_PATH,ownedRun:process.env.Y3GYM_QA_RUN_ID,identity_basis:'signed local ChildProcess spawn, kernel starttime; no complete argv/environment output'})+'\n',{mode:0o600});
    }catch(error){await browser.close();throw error;}
    const newContext = browser.newContext.bind(browser);
    browser.newContext = async (...contextArgs) => {
      if (dockerTLS) assert.notEqual(contextArgs[0]?.ignoreHTTPSErrors, true, 'Owned CA must be trusted; TLS verification cannot be skipped');
      const context = await newContext(...contextArgs);
      const route = context.route.bind(context);
      context.route = (pattern, handler, options) => route(pattern, (r, request) => {
        try { permit(request); } catch { return r.abort('blockedbyclient'); }
        return handler(r, request);
      }, options);
      await context.route('**/*', r => r.fallback());
      // API requests bypass browser routing. Follow internal redirects with the
      // original HTTP semantics, checking every Location before the next request.
      const fetch = context.request.fetch.bind(context.request);
      for (const method of ['get', 'post', 'put', 'patch', 'delete', 'head', 'fetch']) {
        context.request[method] = async (url, options = {}) => {
          let next = url;
          let remaining = options.maxRedirects ?? 20;
          let requestOptions = { ...options, method: method === 'fetch' ? options.method || 'GET' : method.toUpperCase(), maxRedirects: 0 };
          for (;;) {
            permit(next);
            const response = await fetch(next, requestOptions);
            const status = response.status(), location = response.headers().location;
            if (![301, 302, 303, 307, 308].includes(status) || !location) return response;
            next = new URL(location, response.url()).href;
            permit(next);
            if (options.maxRedirects === 0) return response;
            assert(remaining-- > 0, 'Same-origin redirect limit exceeded');
            const previousMethod = requestOptions.method.toUpperCase();
            if (([301, 302].includes(status) && previousMethod === 'POST') || (status === 303 && !['GET', 'HEAD'].includes(previousMethod))) {
              requestOptions = { ...requestOptions, method: 'GET' };
              for (const key of ['data', 'form', 'multipart']) delete requestOptions[key];
              if (requestOptions.headers) requestOptions.headers = Object.fromEntries(Object.entries(requestOptions.headers).filter(([key]) => !['content-type', 'content-length'].includes(key.toLowerCase())));
            }
            delete requestOptions.params;
            await response.dispose();
          }
        };
      }
      return context;
    };
    return browser;
  };
}});
export { chromium, expect };
