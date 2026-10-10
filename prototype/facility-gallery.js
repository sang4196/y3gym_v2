(() => {
  // Home and branch details share the same approved gallery behavior.
  const interval = 4500;
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');

  document.querySelectorAll('[data-facility-gallery]').forEach(gallery => {
    const viewport = gallery.querySelector('[data-gallery-viewport]');
    const track = gallery.querySelector('[data-gallery-track]');
    const slides = [...gallery.querySelectorAll('[data-gallery-slide]')];
    const status = gallery.querySelector('[data-gallery-status]');
    if (!viewport || !track || !status || slides.length < 2) return;

    let current = 0;
    let step = 0;
    let lastWidth = 0;
    let timer;
    let settlement;
    let moving = false;
    let inView = false;
    let hovered = false;
    let touching = false;
    let touchStart = null;

    // Copies make the last-to-first movement continuous. They are decorative;
    // assistive technology reads each original photo and description once.
    function copy(slide) {
      const clone = slide.cloneNode(true);
      clone.removeAttribute('data-gallery-slide');
      clone.setAttribute('data-gallery-clone', '');
      clone.setAttribute('aria-hidden', 'true');
      clone.inert = true;
      clone.querySelectorAll('img').forEach(image => {
        image.alt = '';
        const failed = () => {
          image.hidden = true;
          const fallback = image.parentElement.querySelector('.image-fallback');
          if (fallback) fallback.hidden = false;
          image.parentElement.classList.add('image-unavailable');
        };
        image.addEventListener('error', failed);
        if (image.complete && !image.naturalWidth) failed();
      });
      return clone;
    }
    track.prepend(...slides.map(copy));
    track.append(...slides.map(copy));
    gallery.classList.add('is-ready');
    gallery.setAttribute('role', 'region');
    gallery.setAttribute('aria-roledescription', '슬라이드');
    viewport.tabIndex = 0;
    viewport.setAttribute('role', 'group');
    viewport.setAttribute('aria-label', '시설 사진 · 왼쪽·오른쪽 방향키로 넘기기');

    function stopTimer() { clearTimeout(timer); }
    function canPlay() {
      return !reducedMotion.matches && !hovered && !touching && !document.hidden && inView && step > 0 &&
        !document.documentElement.classList.contains('mobile-popup-open') &&
        !gallery.closest('[hidden]') && !gallery.contains(document.activeElement);
    }
    function schedule() {
      stopTimer();
      if (!moving && canPlay()) timer = setTimeout(() => {
        if (canPlay()) advance(1, true);
      }, interval);
    }
    function position(animate) {
      track.classList.toggle('is-positioning', !animate);
      track.style.transform = `translate3d(${-step * (slides.length + current)}px, 0, 0)`;
      if (!animate) void track.offsetWidth;
    }
    function settle() {
      clearTimeout(settlement);
      current = (current + slides.length) % slides.length;
      moving = false;
      position(false);
      schedule();
    }
    function advance(direction, automatic = false) {
      if (moving || !step) return;
      stopTimer();
      current += direction;
      moving = true;
      position(!reducedMotion.matches);
      if (!automatic) {
        const index = (current + slides.length) % slides.length;
        status.textContent = `시설 사진 ${index + 1} / ${slides.length} · ${slides[index].querySelector('h4').textContent}`;
      }
      if (reducedMotion.matches) settle();
      // Also settle when a tab/viewport change prevents transitionend.
      else settlement = setTimeout(settle, 650);
    }
    function layout() {
      const width = viewport.clientWidth;
      if (!width || width === lastWidth) return;
      lastWidth = width;
      clearTimeout(settlement);
      moving = false;
      current = (current + slides.length) % slides.length;
      const css = getComputedStyle(gallery);
      const columns = Math.min(slides.length, Number(css.getPropertyValue('--gallery-columns')));
      const gap = parseFloat(css.getPropertyValue('--gallery-gap'));
      const cardWidth = (width - gap * (columns - 1)) / columns;
      gallery.style.setProperty('--gallery-card-width', `${cardWidth}px`);
      step = cardWidth + gap;
      position(false);
      schedule();
    }
    track.addEventListener('transitionend', event => {
      if (event.target === track && event.propertyName === 'transform' && moving) settle();
    });
    viewport.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
      event.preventDefault();
      advance(event.key === 'ArrowRight' ? 1 : -1);
    });
    gallery.addEventListener('pointerenter', event => {
      if (event.pointerType === 'mouse') { hovered = true; stopTimer(); }
    });
    gallery.addEventListener('pointerleave', event => {
      if (event.pointerType === 'mouse') { hovered = false; schedule(); }
    });
    gallery.addEventListener('focusin', stopTimer);
    gallery.addEventListener('focusout', () => queueMicrotask(schedule));
    viewport.addEventListener('touchstart', event => {
      touching = true;
      stopTimer();
      touchStart = event.touches.length === 1 ? { x: event.touches[0].clientX, y: event.touches[0].clientY } : null;
    }, { passive: true });
    viewport.addEventListener('touchmove', event => {
      if (event.touches.length !== 1) touchStart = null;
    }, { passive: true });
    viewport.addEventListener('touchend', event => {
      const start = touchStart;
      touchStart = null;
      touching = event.touches.length > 0;
      if (start && !touching && event.changedTouches.length === 1) {
        const dx = event.changedTouches[0].clientX - start.x;
        const dy = event.changedTouches[0].clientY - start.y;
        if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy) * 1.3) advance(dx < 0 ? 1 : -1);
      }
      schedule();
    }, { passive: true });
    viewport.addEventListener('touchcancel', () => { touching = false; touchStart = null; schedule(); }, { passive: true });
    gallery.addEventListener('gallery-selection-change', () => {
      stopTimer();
      if (!gallery.closest('[hidden]')) {
        current = 0;
        clearTimeout(settlement);
        moving = false;
        layout();
        position(false);
        status.textContent = '';
        schedule();
      }
    });
    document.addEventListener('visibilitychange', schedule);
    new MutationObserver(schedule).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    reducedMotion.addEventListener('change', () => {
      if (reducedMotion.matches) settle();
      schedule();
    });
    new ResizeObserver(layout).observe(viewport);
    new IntersectionObserver(entries => {
      inView = entries[0].isIntersecting && entries[0].intersectionRatio >= 0.15;
      if (inView) track.querySelectorAll('img[loading="lazy"]').forEach(image => { image.loading = 'eager'; });
      schedule();
    }, { threshold: 0.15 }).observe(viewport);
    layout();
  });
})();
