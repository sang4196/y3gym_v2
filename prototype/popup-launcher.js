import { getPopupExample } from './demo-content.js';
import { isPopupEligible, readStorage, writeStorage } from './popup-policy.js';
import { createMobilePopup } from './mobile-popup.js';
import { withBranchContext } from './branch-context.js';

const entry = document.querySelector('[data-popup-entry]');
const link = entry?.querySelector('[data-open-popup]');
const status = entry?.querySelector('[data-popup-status]');
const { popup, post } = getPopupExample(document.body.dataset.demoState);

if (entry && link && status) {
  if (!isPopupEligible(popup, post)) {
    entry.hidden = true;
  } else {
    const basePopupURL = new URL(link.dataset.popupUrl, location.href).href;
    const mobile = window.matchMedia('(max-width: 767px)');
    link.href = post.url;
    const mobilePopup = createMobilePopup({ popup, post, onReady() {
      writeStorage('sessionStorage', `shown:${popup.id}`, Date.now());
      status.textContent = '알림을 페이지 안에서 열었습니다. ‘알림 보기’에서 다시 확인할 수 있습니다.';
    } });

    function updatePresentation() {
      link.querySelector('[data-popup-link-hint]').textContent = mobile.matches ? '페이지 안에서 열기' : '별도 창으로 열기';
      link.querySelector('[data-popup-link-icon]').textContent = mobile.matches ? '→' : '↗';
      if (mobile.matches && mobilePopup) link.setAttribute('aria-haspopup', 'dialog');
      else link.removeAttribute('aria-haspopup');
    }
    updatePresentation();
    mobile.addEventListener('change', () => {
      mobilePopup?.close();
      updatePresentation();
      status.textContent = mobile.matches ? '알림은 같은 페이지 안에서 열립니다.' : '알림은 별도 창으로 열립니다.';
    });
    let popupWindow = null;
    let ready = false;
    let attempt = 0;
    const name = `y3gym-${popup.id}`;

    function openPopup(source = null) {
      const popupURL = withBranchContext(basePopupURL);
      if (!isPopupEligible(popup, post)) {
        entry.hidden = true;
        return;
      }
      if (mobile.matches) {
        if (!mobilePopup) {
          status.textContent = '이 브라우저에서는 ‘알림 보기’로 관련 소식 글을 확인해주세요.';
          return;
        }
        mobilePopup.open(source).then(opened => {
          if (!opened) {
            status.textContent = '알림을 열지 못했습니다. 관련 소식 글에서 확인해주세요.';
            if (source) location.assign(link.href);
          }
        });
        return;
      }
      if (popupWindow && !popupWindow.closed && ready) {
        try {
          if (popupWindow.location.href === popupURL) {
            popupWindow.focus();
            return;
          }
        } catch {
          // Reuse the named window even after a navigation or loading failure.
        }
      }
      const currentAttempt = ++attempt;
      ready = false;
      try {
        popupWindow = window.open(popupURL, name, 'popup=yes,width=480,height=700,resizable=yes,scrollbars=yes');
      } catch {
        popupWindow = null;
      }
      if (!popupWindow) {
        status.textContent = '자동 열기가 차단되었거나 창을 열지 못했습니다. ‘알림 보기’를 눌러 열어주세요.';
        return;
      }
      status.textContent = '알림 창을 여는 중입니다. 표시되지 않으면 ‘알림 보기’를 다시 눌러주세요.';
      setTimeout(() => {
        if (currentAttempt === attempt && !ready) {
          status.textContent = '알림 창을 표시하지 못했습니다. ‘알림 보기’에서 다시 열 수 있습니다.';
        }
      }, 3000);
    }

    window.addEventListener('message', event => {
      if (event.origin !== location.origin || event.source !== popupWindow ||
          event.data?.type !== 'y3gym-popup-ready' || event.data.id !== popup.id) return;
      ready = true;
      writeStorage('sessionStorage', `shown:${popup.id}`, Date.now());
      status.textContent = '알림을 별도 창으로 열었습니다. ‘알림 보기’에서 다시 확인할 수 있습니다.';
    });

    link.addEventListener('click', event => {
      // The native same-tab post link survives module failure, including on mobile.
      link.href = withBranchContext(post.url);
      if (mobile.matches && !mobilePopup) return;
      event.preventDefault();
      openPopup(link);
    });

    const hiddenUntil = readStorage('localStorage', `hide:${popup.id}`);
    const automaticAttempt = readStorage('sessionStorage', 'auto-attempt');
    if (!hiddenUntil.available || !automaticAttempt.available) {
      status.textContent = '자동 알림을 사용할 수 없습니다. ‘알림 보기’에서 직접 확인해주세요.';
    } else if (Number(hiddenUntil.value) > Date.now()) {
      status.textContent = '오늘 자동 알림을 숨겼습니다. ‘알림 보기’에서 직접 확인할 수 있습니다.';
    } else if (!automaticAttempt.value) {
      // Attempt and successful display are deliberately separate records.
      if (writeStorage('sessionStorage', 'auto-attempt', '1')) {
        openPopup();
      } else {
        status.textContent = '자동 알림을 사용할 수 없습니다. ‘알림 보기’에서 직접 확인해주세요.';
      }
    }
  }
}
