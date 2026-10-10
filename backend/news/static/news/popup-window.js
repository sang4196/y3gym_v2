import { nextKoreanMidnight, writeStorage } from '/static/prototype/popup-policy.js';
import { createPopupWindowSizer } from './popup-sizing.js';

const popup = JSON.parse(document.getElementById('popup-data').textContent);

// The opener supplies the same anchor and requested monitor as the initial
// left/top. Fitting uses the actual screen if the browser opens elsewhere.
// A standalone popup URL has no placement provider and falls back to center.
const placement = new Promise(resolve => {
  if (!window.opener || window.opener.closed) { resolve({ x: 0, y: 0 }); return; }
  const finish = value => {
    clearTimeout(timeout);
    window.removeEventListener('message', receive);
    resolve(value);
  };
  const receive = event => {
    const value = event.data?.placement;
    const display = value?.display;
    if (event.origin !== location.origin || event.source !== window.opener ||
        event.data?.type !== 'y3gym-popup-placement' || event.data.id !== popup.id ||
        !value || ![value.x, value.y].every(number => Number.isFinite(number) && Math.abs(number) <= 1) ||
        !display || ![display.availLeft, display.availTop].every(Number.isFinite) ||
        ![display.availWidth, display.availHeight].every(number => Number.isFinite(number) && number > 0)) return;
    finish(value);
  };
  const timeout = setTimeout(() => finish({ x: 0, y: 0 }), 500);
  window.addEventListener('message', receive);
  window.opener.postMessage({ type: 'y3gym-popup-placement-request', id: popup.id }, location.origin);
});
const sizer = placement.then(value => createPopupWindowSizer(
  document.querySelector('.popup-document'), value));
const fitPopupToContent = async () => {
  const fit = await sizer;
  return fit();
};

async function announceReady() {
  await document.fonts.ready;
  const image = document.querySelector('[data-popup-image]');
  if (image) {
    try { await image.decode(); }
    catch {
      image.hidden = true;
      document.querySelector('[data-popup-image-fallback]').hidden = false;
      document.querySelector('[data-popup-image-frame]').classList.add('image-unavailable');
    }
  }
  await fitPopupToContent();
  window.opener?.postMessage({ type: 'y3gym-popup-ready', id: popup.id }, location.origin);
}
announceReady();

const checkbox = document.querySelector('[data-hide-today]');
const feedback = document.querySelector('[data-popup-feedback]');
document.querySelector('[data-close-popup]').addEventListener('click', () => {
  if (checkbox.checked && !writeStorage('localStorage', `hide:${popup.id}`, nextKoreanMidnight())) {
    checkbox.checked = false;
    feedback.textContent = '오늘 숨김 설정을 저장하지 못했습니다. 닫기를 다시 누르면 이번 창을 닫습니다.';
    fitPopupToContent();
    return;
  }
  window.close();
  setTimeout(() => { feedback.textContent = '브라우저의 창 또는 탭 닫기 버튼으로 닫아주세요.'; }, 200);
});
