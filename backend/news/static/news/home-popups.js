import { readStorage, writeStorage } from '/static/prototype/popup-policy.js';
import { withBranchContext } from '/static/prototype/branch-context.js';
import { createMobilePopup } from './mobile-popup.js';
import { createPopupPlacementPlanner, popupWindowFeatures, popupWorkArea } from './popup-sizing.js';

const data = document.getElementById('home-popup-data');
const popups = data ? JSON.parse(data.textContent) : [];
const entry = document.querySelector('[data-live-popup-entry]');
const status = entry?.querySelector('[data-popup-status]');
const recovery = entry?.querySelector('[data-popup-recovery]');
const mobile = matchMedia('(max-width: 767px)');
const windows = new Map();
const placements = new Map();
const nextPlacement = createPopupPlacementPlanner();
const failures = new Map();
let queue = Promise.resolve();
let activeLayer = null;

window.addEventListener('message', event => {
  const id = event.data?.id;
  if (event.origin !== location.origin || event.source !== windows.get(id) ||
      event.data?.type !== 'y3gym-popup-placement-request') return;
  event.source.postMessage({ type: 'y3gym-popup-placement', id,
    placement: placements.get(id) }, location.origin);
});

function hiddenToday(popup) {
  const stored = readStorage('localStorage', `hide:${popup.id}`);
  return Number(stored.value) > Date.now();
}

function recover(popup, message) {
  failures.set(popup.id, popup);
  writeStorage('sessionStorage', 'cms-popup-recovery', JSON.stringify([...failures.keys()]));
  entry.hidden = false;
  status.textContent = message;
  recovery.hidden = false;
  recovery.replaceChildren();
  for (const item of failures.values()) {
    const line = document.createElement('p');
    const link = document.createElement('a');
    link.className = 'text-link';
    link.href = withBranchContext(item.url);
    link.textContent = `${item.title} · 직접 열기`;
    link.addEventListener('click', event => {
      event.preventDefault();
      if (mobile.matches) queueMobile(item, link);
      else openWindow(item);
    });
    line.append(link);
    recovery.append(line);
  }
}

function ready(popup) {
  writeStorage('sessionStorage', `shown:${popup.id}`, '1');
  failures.delete(popup.id);
  writeStorage('sessionStorage', 'cms-popup-recovery', JSON.stringify([...failures.keys()]));
  if (!failures.size) {
    recovery.hidden = true;
    status.textContent = '';
  }
}

function openWindow(popup) {
  const existing = windows.get(popup.id);
  if (existing && !existing.closed && !failures.has(popup.id)) {
    existing.focus();
    return;
  }
  // Keep this synchronous: manual recovery must retain the user's click gesture.
  const area = popupWorkArea();
  const placement = { ...nextPlacement(), display: {
    availLeft: area.left, availTop: area.top, availWidth: area.width, availHeight: area.height,
  } };
  const opened = window.open(withBranchContext(popup.url), `y3gym-${popup.id}`,
    popupWindowFeatures(placement));
  if (!opened) {
    recover(popup, '브라우저가 알림 창을 차단했습니다. 아래 링크에서 직접 열어주세요.');
    return;
  }
  windows.set(popup.id, opened);
  placements.set(popup.id, placement);
  const timeout = setTimeout(() => {
    window.removeEventListener('message', acknowledge);
    recover(popup, '알림 창을 확인하지 못했습니다. 아래 링크에서 다시 확인해 주세요.');
  }, 6000);
  const acknowledge = event => {
    if (event.origin !== location.origin || event.source !== opened ||
        event.data?.type !== 'y3gym-popup-ready' || event.data.id !== popup.id) return;
    clearTimeout(timeout);
    window.removeEventListener('message', acknowledge);
    ready(popup);
  };
  window.addEventListener('message', acknowledge);
}

async function openMobile(popup, source) {
  if (!source && hiddenToday(popup)) return;
  if (!mobile.matches) {
    recover(popup, '화면 크기가 바뀌었습니다. 남은 알림은 아래 링크에서 직접 열어주세요.');
    return;
  }
  // A queued layer can open much later than the home response. Recheck the
  // server's current publication/period verdict before showing each one.
  let current;
  try {
    const response = await fetch(popup.dataUrl, { cache: 'no-store' });
    if (response.status === 404) {
      failures.delete(popup.id);
      writeStorage('sessionStorage', 'cms-popup-recovery', JSON.stringify([...failures.keys()]));
      if (!failures.size) { recovery.hidden = true; status.textContent = ''; }
      return;
    }
    if (!response.ok) throw new Error('popup unavailable');
    current = await response.json();
  } catch {
    recover(popup, '알림을 불러오지 못했습니다. 아래 링크에서 다시 확인해 주세요.');
    return;
  }
  await new Promise(resolve => {
    const layer = createMobilePopup({
      popup: current, post: current.post,
      onReady: () => ready(popup),
      onClose: () => { activeLayer = null; layer.destroy(); resolve(); },
    });
    if (!layer) {
      // Unsupported dialog: use the approved separate document as a fallback.
      recover(popup, '이 브라우저에서는 알림 창을 직접 열어주세요.');
      const link = recovery.querySelector(`a[href="${withBranchContext(popup.url)}"]`);
      if (link) link.addEventListener('click', () => location.assign(link.href), { once: true });
      resolve();
      return;
    }
    activeLayer = layer;
    layer.open(source).then(opened => {
      if (opened) return;
      layer.destroy();
      activeLayer = null;
      recover(popup, '알림을 열지 못했습니다. 아래 링크에서 다시 확인해 주세요.');
      resolve();
    });
  });
}

function queueMobile(popup, source) {
  queue = queue.then(() => openMobile(popup, source));
}

mobile.addEventListener('change', () => { if (!mobile.matches) activeLayer?.close(); });

// Attempt the eligible batch on every home load. Previous tab-level attempt /
// shown records are diagnostics only; only the explicit hide-today value can
// suppress an eligible popup. Named windows still prevent duplicate PC windows.
for (const popup of popups.filter(item => !hiddenToday(item))) {
  if (mobile.matches) queueMobile(popup);
  else openWindow(popup);
}

// A cached back/forward restoration does not execute this module again.
// Reload it for a fresh server period/publication verdict and one fresh batch.
window.addEventListener('pageshow', event => {
  if (event.persisted) location.reload();
});
