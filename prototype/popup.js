import { getPopupExample } from './demo-content.js';
import { isPopupEligible, nextKoreanMidnight, writeStorage } from './popup-policy.js';
import { withBranchContext } from './branch-context.js';

const example = new URLSearchParams(location.search).get('case') || 'default';
const { popup, post } = getPopupExample(example);
const content = document.querySelector('[data-popup-content]');

function fitPopupToContent() {
  if (!window.opener || window.opener.closed) return;
  const documentFrame = document.querySelector('.popup-document');
  // Measure the natural height without the full-tab footer alignment.
  const previousMinHeight = documentFrame.style.minHeight;
  documentFrame.style.minHeight = '0';
  const contentHeight = Math.ceil(documentFrame.getBoundingClientRect().height);
  documentFrame.style.minHeight = previousMinHeight;
  const browserFrame = Math.max(0, window.outerHeight - window.innerHeight);
  const availableHeight = Math.max(0, window.screen.availHeight - browserFrame);
  const requestedHeight = Math.min(contentHeight, availableHeight || contentHeight);
  try {
    window.resizeTo(window.outerWidth, requestedHeight + browserFrame);
  } catch {
    // Browsers may keep a full-size tab; CSS keeps its controls at the bottom.
  }
}

if (isPopupEligible(popup, post)) {
  document.querySelector('[data-popup-title]').textContent = popup.title;
  document.querySelector('[data-popup-description]').textContent = popup.description;
  document.querySelector('[data-popup-post]').href = withBranchContext(post.url);
  document.querySelector('[data-popup-unavailable]').hidden = true;
  content.hidden = false;

  async function announceReady() {
    await document.fonts.ready;
    fitPopupToContent();
    if (window.opener && !window.opener.closed) {
      window.opener.postMessage({ type: 'y3gym-popup-ready', id: popup.id }, location.origin);
    }
  }

  if (popup.image) {
    const image = document.querySelector('[data-popup-image]');
    document.querySelector('[data-popup-image-frame]').hidden = false;
    image.addEventListener('load', announceReady, { once: true });
    image.addEventListener('error', () => {
      image.hidden = true;
      document.querySelector('[data-popup-image-fallback]').hidden = false;
      document.querySelector('[data-popup-image-frame]').classList.add('image-unavailable');
      announceReady();
    }, { once: true });
    image.src = popup.image;
  } else {
    announceReady();
  }

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
    setTimeout(() => {
      feedback.textContent = '브라우저의 창 또는 탭 닫기 버튼으로 닫아주세요.';
    }, 200);
  });
}
