// QA observation only: actual window.open results, ready messages, and documents.
// No storage markers, synthetic events, product changes, or timeout extensions.
import assert from 'node:assert/strict';

export async function installPopupObservation(context) {
  await context.addInitScript(() => {
    const observation = window.integrationPopupObservation = { opens: [], opened: [], ready: [] };
    const windows = new Map();
    const open = window.open.bind(window);
    window.open = (...args) => {
      const opened = open(...args);
      observation.opens.push(String(args[0]));
      if (opened) {
        windows.set(opened, String(args[0]));
        observation.opened.push(String(args[0]));
      }
      return opened;
    };
    window.addEventListener('message', event => {
      if (event.origin === location.origin && windows.has(event.source) &&
          event.data?.type === 'y3gym-popup-ready') observation.ready.push(event.data.id);
    });
  });
}

async function inspect(page, expected) {
  await page.locator('[data-close-popup]').waitFor();
  const actual = JSON.parse(await page.locator('#popup-data').textContent());
  assert.equal(actual.id, expected.id);
  assert.equal(actual.postId, expected.postId);
  assert.equal(actual.post.url, expected.post.url);
  assert.equal(new URL(page.url()).pathname, expected.url);
  assert.equal(new URL(await page.locator('[data-popup-post]').getAttribute('href'), page.url()).pathname, expected.post.url);
  return actual.id;
}

export async function observePopupBatch(home, payload) {
  const ids = payload.map(item => item.id);
  await home.waitForFunction(ids => window.integrationPopupObservation?.opens.length === ids.length &&
    ids.every(id => window.integrationPopupObservation.ready.includes(id)), ids);
  const urls = await home.evaluate(() => integrationPopupObservation.opens);
  assert.deepEqual(urls.map(url => new URL(url, home.url()).pathname), payload.map(item => item.url));
  const pages = home.context().pages().filter(page => !page.isClosed() && new URL(page.url()).pathname.startsWith('/popups/'));
  assert.equal(pages.length, payload.length);
  const actualIds = [];
  for (const page of pages) {
    const expected = payload.find(item => item.url === new URL(page.url()).pathname);
    assert(expected, 'Opened popup must belong to the current eligible payload');
    actualIds.push(await inspect(page, expected));
  }
  assert.deepEqual(actualIds.sort(), [...ids].sort());
  assert.equal(new Set(actualIds).size, ids.length);
}

export async function observePopupOne(home, popup) {
  const actual = JSON.parse(await popup.locator('#popup-data').textContent());
  const payload = JSON.parse(await home.locator('#home-popup-data').textContent());
  const expected = payload.find(item => item.id === actual.id);
  assert(expected, 'Recovered popup must belong to the current eligible payload');
  await home.waitForFunction(id => window.integrationPopupObservation?.ready.includes(id), expected.id);
  await inspect(popup, expected);
  const opened = await home.evaluate(() => integrationPopupObservation.opened);
  assert.equal(opened.filter(url => new URL(url, home.url()).pathname === expected.url).length, 1);
}

export async function ordinaryCloseAndRevisit(home, payload) {
  const origin = new URL(home.url()).origin;
  for (const page of home.context().pages().filter(page => page !== home && !page.isClosed())) {
    const closed = page.waitForEvent('close');
    await page.locator('[data-close-popup]').click().catch(error => { if (!page.isClosed()) throw error; });
    await closed;
  }
  const hidden = await home.evaluate(ids => ids.filter(id => Number(localStorage.getItem(`y3gym.prototype.hide:${id}`)) > Date.now()), payload.map(item => item.id));
  assert.deepEqual(hidden, []);
  await home.goto(`${origin}/news/?branch=second`);
  await home.goto(`${origin}/?branch=second`);
  await observePopupBatch(home, payload);
}
