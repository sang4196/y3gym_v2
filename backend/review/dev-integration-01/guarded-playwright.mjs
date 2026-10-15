// Import/transport adaptation only. No assertions, waits, or browser modes change.
import assert from 'node:assert/strict';
import { chromium as original, expect } from '../../../prototype/node_modules/@playwright/test/index.mjs';

const origin = ['Y3GYM_BRAND_REVIEW_ORIGIN', 'Y3GYM_BRANCH_REVIEW_ORIGIN', 'Y3GYM_TRAINER_REVIEW_ORIGIN', 'Y3GYM_HOME_NEWS_ORIGIN']
  .map(key => process.env[key]).find(Boolean) || process.env.Y3GYM_INTEGRATION_ORIGIN;
assert(origin, 'Private campaign origin required');
const allowed = new URL(origin);
assert(allowed.hostname === 'localhost' && allowed.protocol === 'http:');
assert(!['8767', '8768', '8769', '8770', '8771', '34471', '52949'].includes(allowed.port));
const permit = value => {
  const url = new URL(typeof value === 'string' ? value : value.url(), origin);
  assert.equal(url.origin, allowed.origin, 'External/protected transport blocked');
};
const launch = original.launch.bind(original);
const chromium = new Proxy(original, { get(target, name) {
  if (name !== 'launch') return Reflect.get(target, name);
  return async (...args) => {
    const browser = await launch(...args);
    const newContext = browser.newContext.bind(browser);
    browser.newContext = async (...contextArgs) => {
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
