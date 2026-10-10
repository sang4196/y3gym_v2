// Adapted from the approved mobile layer. Eligibility is checked by the server before creation.
import { nextKoreanMidnight, writeStorage } from '/static/prototype/popup-policy.js';
import { withBranchContext } from '/static/prototype/branch-context.js';

// Native dialog keeps keyboard focus and background interaction inside the layer.
export function createMobilePopup({ popup, post, onReady, onClose }) {
  const dialog = document.createElement('dialog');
  if (typeof dialog.showModal !== 'function') return null;
  dialog.className = 'mobile-popup';
  dialog.setAttribute('aria-labelledby', 'mobile-popup-title');
  dialog.setAttribute('aria-describedby', 'mobile-popup-description');
  dialog.innerHTML = `
    <div class="mobile-popup-body">
      <p class="content-example">로컬 CMS 검토용 · 테스트 자료입니다.</p>
      <p class="eyebrow">공지 · 브랜드 공통 안내</p>
      <h2 id="mobile-popup-title"></h2>
      <div class="popup-image-frame" data-mobile-popup-image-frame hidden>
        <img alt="가상의 헬스장 시설 전경 — 임시 합성 이미지" data-mobile-popup-image>
        <span class="image-fallback" data-mobile-popup-image-fallback hidden>사진을 불러오지 못했습니다.</span>
      </div>
      <p id="mobile-popup-description"></p>
      <a class="button button--primary" data-mobile-popup-post>소식 글 보기</a>
    </div>
    <div class="popup-controls">
      <label class="checkbox-label"><input type="checkbox" data-mobile-hide-today>오늘 하루 보지 않기</label>
      <button class="popup-close" type="button" aria-label="알림 닫기" data-mobile-close-popup autofocus>닫기 <span aria-hidden="true">×</span></button>
    </div>
    <p class="content-example" role="status" data-mobile-popup-feedback></p>`;
  dialog.querySelector('.eyebrow').textContent = `${popup.category} · 브랜드 공통 안내`;
  dialog.querySelector('#mobile-popup-title').textContent = popup.title;
  dialog.querySelector('#mobile-popup-description').textContent = popup.description;
  dialog.querySelector('[data-mobile-popup-post]').href = post.url;
  document.body.append(dialog);

  const checkbox = dialog.querySelector('[data-mobile-hide-today]');
  const closeButton = dialog.querySelector('[data-mobile-close-popup]');
  const feedback = dialog.querySelector('[data-mobile-popup-feedback]');
  let trigger = null;
  let contentReady = null;

  function loadContent() {
    if (contentReady) return contentReady;
    const image = dialog.querySelector('[data-mobile-popup-image]');
    const imageReady = popup.image ? new Promise(resolve => {
      image.addEventListener('load', resolve, { once: true });
      image.addEventListener('error', () => {
        image.hidden = true;
        dialog.querySelector('[data-mobile-popup-image-fallback]').hidden = false;
        dialog.querySelector('[data-mobile-popup-image-frame]').classList.add('image-unavailable');
        resolve();
      }, { once: true });
      dialog.querySelector('[data-mobile-popup-image-frame]').hidden = false;
      image.src = popup.image;
    }) : Promise.resolve();
    contentReady = Promise.all([imageReady, document.fonts.ready]);
    return contentReady;
  }

  function dismiss() {
    if (checkbox.checked && !writeStorage('localStorage', `hide:${popup.id}`, nextKoreanMidnight())) {
      checkbox.checked = false;
      feedback.textContent = '오늘 숨김 설정을 저장하지 못했습니다. 닫기를 다시 누르면 이번 알림을 닫습니다.';
      return;
    }
    dialog.close();
  }

  closeButton.addEventListener('click', dismiss);
  dialog.addEventListener('keydown', event => {
    if (event.key !== 'Tab') return;
    const controls = [...dialog.querySelectorAll('a[href], button:not(:disabled), input:not(:disabled)')]
      .filter(element => element.getClientRects().length);
    const first = controls[0];
    const last = controls.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });
  dialog.addEventListener('cancel', event => {
    event.preventDefault();
    dismiss();
  });
  dialog.addEventListener('click', event => {
    const bounds = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right ||
        event.clientY < bounds.top || event.clientY > bounds.bottom)) dismiss();
  });
  dialog.addEventListener('close', () => {
    document.documentElement.classList.remove('mobile-popup-open');
    trigger?.focus({ preventScroll: true });
    onClose?.();
  });

  return {
    async open(source) {
      dialog.querySelector('[data-mobile-popup-post]').href = withBranchContext(post.url);
      if (dialog.open) {
        closeButton.focus({ preventScroll: true });
        return true;
      }
      trigger = source || document.activeElement;
      checkbox.checked = false;
      feedback.textContent = '';
      try {
        dialog.showModal();
      } catch {
        return false;
      }
      document.documentElement.classList.add('mobile-popup-open');
      await loadContent();
      if (dialog.open) onReady();
      return true;
    },
    close() { if (dialog.open) dialog.close(); },
    destroy() { dialog.remove(); },
  };
}
