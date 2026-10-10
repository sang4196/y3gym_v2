(() => {
  const browser = document.querySelector('[data-branch-browser]');
  const tabList = browser?.querySelector('[data-branch-tabs]');
  const tabs = [...(tabList?.querySelectorAll('[data-branch-tab]') || [])];
  const panels = tabs.map(tab => document.getElementById(tab.hash.slice(1)));
  if (tabs.length && panels.every(Boolean)) {
    const storageKey = 'y3gym.prototype.selected-branch';
    let selected = 0;
    tabList.setAttribute('role', 'tablist');
    tabs.forEach((tab, index) => {
      tab.setAttribute('role', 'tab');
      tab.setAttribute('aria-controls', panels[index].id);
      panels[index].setAttribute('role', 'tabpanel');
      panels[index].setAttribute('aria-labelledby', tab.id);
      panels[index].tabIndex = 0;
    });

    function select(index, { updateURL = false, focus = false } = {}) {
      selected = index;
      tabs.forEach((tab, tabIndex) => {
        const active = tabIndex === index;
        tab.setAttribute('aria-selected', String(active));
        tab.tabIndex = active ? 0 : -1;
        panels[tabIndex].hidden = !active;
      });
      const id = panels[index].dataset.branchId;
      browser.querySelectorAll('[data-facility-gallery]').forEach(gallery => {
        gallery.dispatchEvent(new Event('gallery-selection-change'));
      });
      try { sessionStorage.setItem(storageKey, id); } catch { /* Selection still works without storage. */ }
      const url = new URL(location.href);
      if (updateURL || index !== 0 || url.searchParams.has('branch')) url.searchParams.set('branch', id);
      if (updateURL) url.hash = 'branch';
      history.replaceState(null, '', url);
      document.querySelectorAll('[data-branch-jump]').forEach(link => {
        const section = panels[index].querySelector(`[data-branch-section="${link.dataset.branchJump}"]`);
        link.setAttribute('href', section ? `#${section.id}` : '#branch');
      });
      document.querySelectorAll('[data-branch-page]').forEach(link => {
        link.dataset.originalHref ||= link.getAttribute('href');
        const destination = new URL(link.dataset.originalHref, location.href);
        destination.searchParams.set('branch', id);
        if (destination.hash === '#contact') destination.hash = `contact-${id}`;
        link.href = destination.href;
      });
      document.querySelectorAll('[data-selected-branch-name]').forEach(element => {
        element.textContent = panels[index].dataset.branchName;
      });
      const contactBar = document.querySelector('.mobile-contact-bar');
      if (contactBar) contactBar.setAttribute('aria-label', `${panels[index].dataset.branchName} 문의 안내`);
      document.querySelectorAll('.mobile-contact-bar .button').forEach(link => {
        link.setAttribute('aria-label', `${panels[index].dataset.branchName} ${link.textContent.trim()}`);
      });
      document.querySelectorAll('.news-title-link').forEach(link => {
        link.dataset.originalHref ||= link.getAttribute('href');
        if (url.searchParams.has('branch')) {
          const postURL = new URL(link.dataset.originalHref, location.href);
          postURL.searchParams.set('branch', id);
          link.href = postURL.href;
        }
      });
      if (focus) {
        tabs[index].focus({ preventScroll: true });
        tabs[index].scrollIntoView({ block: 'nearest', inline: 'nearest' });
      }
    }

    function readLocation() {
      let hash = '';
      try { hash = decodeURIComponent(location.hash.slice(1)); } catch { /* Ignore malformed fragments. */ }
      const target = document.getElementById(hash);
      const targetPanel = target?.closest('[data-branch-panel]');
      let saved = null;
      try { saved = sessionStorage.getItem(storageKey); } catch { /* Use URL or first branch. */ }
      const requested = targetPanel?.dataset.branchId || new URLSearchParams(location.search).get('branch') || saved;
      const index = panels.findIndex(panel => panel.dataset.branchId === requested);
      select(index >= 0 ? index : 0);
      if (['contact', 'facilities', 'trainers'].includes(hash)) {
        const section = panels[selected].querySelector(`[data-branch-section="${hash}"]`);
        if (section) requestAnimationFrame(() => section.scrollIntoView());
      } else if (targetPanel) requestAnimationFrame(() => target.scrollIntoView());
    }

    tabs.forEach((tab, index) => {
      tab.addEventListener('click', event => {
        if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        select(index, { updateURL: true, focus: true });
      });
      tab.addEventListener('keydown', event => {
        let next;
        if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
        if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
        if (event.key === 'Home') next = 0;
        if (event.key === 'End') next = tabs.length - 1;
        if (event.key === ' ' || event.key === 'Enter') next = index;
        if (next === undefined) return;
        event.preventDefault();
        select(next, { updateURL: true, focus: true });
      });
    });
    window.addEventListener('hashchange', readLocation);
    window.addEventListener('popstate', readLocation);
    readLocation();
  }

  const toggle = document.querySelector('.menu-toggle');
  const navigation = document.querySelector('#primary-navigation');
  const toggleLabel = document.querySelector('.menu-toggle-label');

  if (toggle && navigation && toggleLabel) {
    const narrowScreen = window.matchMedia('(max-width: 1023px)');

    function setMenu(open, returnFocus = false) {
      navigation.hidden = narrowScreen.matches && !open;
      toggle.setAttribute('aria-expanded', String(narrowScreen.matches && open));
      toggleLabel.textContent = open && narrowScreen.matches ? '닫기' : '메뉴';
      if (returnFocus && narrowScreen.matches) toggle.focus();
    }

    function synchronizeLayout() {
      toggle.hidden = !narrowScreen.matches;
      setMenu(false);
    }

    toggle.addEventListener('click', () => {
      setMenu(toggle.getAttribute('aria-expanded') !== 'true');
    });

    navigation.addEventListener('click', event => {
      if (event.target.closest('a') && narrowScreen.matches) setMenu(false);
    });

    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
        setMenu(false, true);
      }
    });

    narrowScreen.addEventListener('change', synchronizeLayout);
    synchronizeLayout();
  }

  document.querySelectorAll('[data-preview-contact]').forEach(button => {
    button.addEventListener('click', () => {
      const channel = button.dataset.previewContact;
      const group = button.closest('[data-contact-group]');
      const branch = group?.dataset.branchName;
      const message = branch
        ? `${branch} ${channel} 문의 예시입니다. 실제 서비스로 연결되지 않습니다.`
        : '문의할 지점을 먼저 선택해주세요.';
      const feedback = group?.querySelector('[data-contact-feedback]');
      if (feedback) feedback.textContent = message;
    });
  });

  document.querySelectorAll('img').forEach(image => {
    const fallback = document.createElement('span');
    fallback.className = 'image-fallback';
    fallback.hidden = true;
    fallback.textContent = '사진을 불러오지 못했습니다.';
    image.after(fallback);
    function showFallback() {
      image.hidden = true;
      fallback.hidden = false;
      image.parentElement.classList.add('image-unavailable');
    }
    image.addEventListener('error', showFallback);
    if (image.complete && image.naturalWidth === 0) showFallback();
  });
})();
