// One viewer per document, including a separate PC popup document.
const selector = 'img[data-image-full]';
const probe = document.createElement('dialog');

if (typeof probe.showModal === 'function') {
  const dialog = probe;
  dialog.className = 'content-image-viewer';
  dialog.setAttribute('aria-label', '사진 크게 보기');
  dialog.innerHTML = '<button type="button" class="content-image-close" autofocus aria-label="확대 사진 닫기">닫기 ×</button><div class="content-image-media"></div><p class="content-image-status" role="status" aria-live="polite"></p>';
  document.body.append(dialog);
  const closeButton = dialog.querySelector('button');
  const media = dialog.querySelector('.content-image-media');
  const status = dialog.querySelector('[role="status"]');
  const enhanced = new WeakMap();
  let active = null;
  let backdropStart = false;

  function source(image) {
    try {
      const url = new URL(image.dataset.imageFull, location.href);
      if (url.origin !== location.origin || !url.pathname.startsWith('/media/') ||
          !Number(image.dataset.imageWidth) || !Number(image.dataset.imageHeight)) return null;
      return url.href;
    } catch { return null; }
  }

  function release() {
    const previous = active;
    if (!previous) return;
    active = null;
    previous.events.abort();
    media.replaceChildren();
    status.textContent = '';
    for (const [node, inert] of previous.background) if (node.isConnected) node.inert = inert;
    for (const [node, value, priority] of previous.overflow) {
      if (value) node.style.setProperty('overflow', value, priority);
      else node.style.removeProperty('overflow');
    }
    if (previous.trigger?.isConnected && !previous.trigger.closest('[inert]')) {
      previous.trigger.focus({ preventScroll: true });
    }
    window.scrollTo(previous.x, previous.y);
  }

  function close() {
    if (dialog.open) dialog.close();
    // Synchronous cleanup prevents a queued old close event clearing a reopen.
    release();
  }

  function open(image, trigger = image) {
    const url = source(image);
    if (!url || !image.getAttribute('src') || image.hidden) return;
    if (active) close();
    const picture = new Image();
    picture.alt = image.dataset.imageAlt || image.alt || '콘텐츠 사진';
    picture.width = Number(image.dataset.imageWidth);
    picture.height = Number(image.dataset.imageHeight);
    const state = {
      trigger, events: new AbortController(), x: scrollX, y: scrollY,
      background: new Map(), overflow: [document.documentElement, document.body].map(node =>
        [node, node.style.getPropertyValue('overflow'), node.style.getPropertyPriority('overflow')]),
    };
    active = state;
    media.replaceChildren(picture);
    status.textContent = '사진을 불러오는 중입니다.';
    picture.addEventListener('load', () => {
      if (active === state) status.textContent = '';
    }, { signal: state.events.signal });
    picture.addEventListener('error', () => {
      if (active !== state) return;
      picture.hidden = true;
      status.textContent = '사진을 불러오지 못했습니다. 닫은 뒤 다시 시도해 주세요.';
    }, { signal: state.events.signal });
    try { dialog.showModal(); }
    catch { release(); return; }
    for (const node of document.body.children) {
      if (node === dialog || ['SCRIPT', 'STYLE', 'LINK'].includes(node.tagName)) continue;
      state.background.set(node, node.inert);
      node.inert = true;
    }
    for (const [node] of state.overflow) node.style.setProperty('overflow', 'hidden');
    closeButton.focus({ preventScroll: true });
    picture.src = url;
  }

  function enhance(image) {
    if (!source(image) || !image.getAttribute('src') || image.hidden || image.closest('[data-gallery-clone]')) return;
    if (enhanced.has(image)) return;
    // With JS, the photo expands and its original link remains a separate
    // navigation control. Without JS the original linked image still works.
    const link = image.closest('a');
    if (link) {
      link.before(image);
      if (!link.textContent.trim() && !link.querySelector('img')) {
        link.textContent = `${image.alt || '사진'} · 연결된 페이지로 이동`;
      }
    }
    if (image.closest('button')) return;
    image.tabIndex = 0;
    image.setAttribute('role', 'button');
    image.setAttribute('aria-haspopup', 'dialog');
    image.setAttribute('aria-label', `${image.alt || '콘텐츠 사진'} · 크게 보기`);
    enhanced.set(image, image);
    const unavailable = () => {
      const trigger = enhanced.get(image);
      if (trigger !== image) trigger?.remove();
      else for (const attr of ['tabindex', 'role', 'aria-haspopup', 'aria-label']) image.removeAttribute(attr);
      enhanced.delete(image);
    };
    image.addEventListener('error', unavailable, { once: true });
    if (image.complete && !image.naturalWidth) unavailable();
  }

  function scan() {
    document.querySelectorAll(selector).forEach(enhance);
    // A clone can inherit attributes if a gallery is created after enhancement.
    document.querySelectorAll('[data-gallery-clone] img[role="button"]').forEach(image => {
      for (const attr of ['tabindex', 'role', 'aria-haspopup', 'aria-label']) image.removeAttribute(attr);
    });
  }
  scan();
  const observer = new MutationObserver(() => {
    if (active) for (const node of document.body.children) {
      if (node !== dialog && !active.background.has(node) && !['SCRIPT', 'STYLE', 'LINK'].includes(node.tagName)) {
        active.background.set(node, node.inert);
        node.inert = true;
      }
    }
    scan();
  });
  observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['data-image-full', 'src'] });
  document.addEventListener('load', event => {
    if (event.target.matches?.(selector)) enhance(event.target);
  }, true);

  document.addEventListener('click', event => {
    if (dialog.open) return;
    const image = event.target.closest?.(`${selector}[role="button"]`);
    if (image) { open(image); return; }
    // Gallery clones stay inert/aria-hidden. The viewport handles pointer hits
    // on their photo rectangles, using the same server metadata and viewer.
    const viewport = event.target.closest?.('[data-gallery-viewport]');
    if (!viewport || !event.detail) return;
    const clone = [...viewport.querySelectorAll(`[data-gallery-clone] ${selector}`)].find(node => {
      const b = node.getBoundingClientRect();
      return event.clientX >= b.left && event.clientX <= b.right && event.clientY >= b.top && event.clientY <= b.bottom;
    });
    if (clone) open(clone, viewport);
  });
  document.addEventListener('keydown', event => {
    if (dialog.open || !['Enter', ' '].includes(event.key) || event.repeat) return;
    const image = event.target.matches?.(`${selector}[role="button"]`) ? event.target : null;
    if (image) { event.preventDefault(); open(image); }
  });
  closeButton.addEventListener('click', close);
  dialog.addEventListener('cancel', event => { event.preventDefault(); event.stopPropagation(); close(); });
  dialog.addEventListener('close', () => { if (!dialog.open) release(); });
  dialog.addEventListener('keydown', event => {
    if (event.key === 'Tab') { event.preventDefault(); event.stopPropagation(); closeButton.focus(); }
    if (event.key === 'Escape') event.stopPropagation();
  });
  function background(event) {
    const picture = media.querySelector('img:not([hidden])');
    if (picture) {
      const b = picture.getBoundingClientRect();
      if (event.clientX >= b.left && event.clientX <= b.right && event.clientY >= b.top && event.clientY <= b.bottom) return false;
    }
    return event.target === dialog || event.target === media;
  }
  dialog.addEventListener('pointerdown', event => { backdropStart = background(event); });
  dialog.addEventListener('click', event => {
    event.stopPropagation();
    if (backdropStart && background(event)) close();
    backdropStart = false;
  });
}
