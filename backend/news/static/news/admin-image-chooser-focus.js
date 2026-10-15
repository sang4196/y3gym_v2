// Bootstrap's modal transition completion calls the dialog's focus() before
// shown.bs.modal. Keep a user's existing focus inside an opening image chooser.
// Scope the guard to that DOM node; leave tabs, focus trapping and other dialogs
// alone. Opening adds no timers or corrective focus moves. Closing can restore
// the original control when ModalWorkflow's temporary opener has disappeared.
(() => {
  const $ = window.jQuery;
  const openings = new WeakMap();
  const origins = new WeakMap();
  let currentModal;
  let lastEditor;

  document.addEventListener('focusin', event => {
    const editor = event.target.closest?.('.public-DraftEditor-content');
    if (editor) lastEditor = editor;
  }, true);

  // A selected image opens from a temporary dropdown button. Remember its
  // persistent widget after the chooser's click handler creates the modal.
  document.addEventListener('click', event => {
    const action = event.target.closest?.('[data-chooser-action-choose]');
    const widget = action?.closest('.image-chooser');
    const modal = document.querySelector('body > .modal');
    if (widget && modal && !$(modal).data('bs.modal')?.isShown) {
      origins.set(modal, { widgetId: widget.id });
    }
  });

  const restore = (modal, opening) => {
    if (modal.focus === opening.focus) {
      if (opening.descriptor) Object.defineProperty(modal, 'focus', opening.descriptor);
      else delete modal.focus;
    }
    openings.delete(modal);
  };

  $(document).on('show.bs.modal.y3gymImageFocus', '.modal', function () {
    const modal = this;
    // ModalWorkflow removes an earlier container immediately. If it was still
    // fading out, its transition handler was removed with it: remove only that
    // image chooser's recorded backdrop, never another dialog's backdrop.
    if (currentModal && currentModal !== modal && !currentModal.isConnected) {
      const previous = openings.get(currentModal);
      if (previous?.phase === 'closing') previous.backdrop?.remove();
    }
    if ($(modal).data('bs.modal')?.isShown) return;
    if (!modal.querySelector('#id_image-chooser-upload-file, .duplicate-upload')) return;
    currentModal = modal;
    // Draftail temporarily makes its source editor read-only while its chooser
    // is open. Its original trigger can be body after the block menu unmounts.
    if (!origins.has(modal) && lastEditor?.isConnected && lastEditor.getAttribute('contenteditable') === 'false') {
      const wrapper = lastEditor.closest('[data-draftail-editor-wrapper]');
      const field = [...(wrapper?.parentElement.children || [])].find(element => element.draftailEditor);
      if (field) origins.set(modal, { editor: lastEditor, controller: field.draftailEditor });
    }
    const previous = openings.get(modal);
    if (previous) restore(modal, previous);
    const originalFocus = modal.focus;
    const opening = {
      descriptor: Object.getOwnPropertyDescriptor(modal, 'focus'),
      phase: 'opening',
      interacted: false,
    };
    opening.focus = function (...args) {
      if (!modal.isConnected || opening.phase === 'closing' || !$(modal).data('bs.modal')?.isShown) return;
      const active = document.activeElement;
      if (opening.phase === 'opening' && opening.interacted && active !== modal && modal.contains(active)) return;
      return originalFocus.apply(this, args);
    };
    modal.focus = opening.focus;
    openings.set(modal, opening);
  });

  const noteInteraction = event => {
    if (!event.isTrusted) return;
    const modal = event.target.closest?.('.modal');
    // The first Tab can originate on body/opener and move into the chooser.
    const candidates = modal ? [modal] : event.type === 'keydown' && event.key === 'Tab'
      ? document.querySelectorAll('body > .modal') : [];
    for (const candidate of candidates) {
      const opening = openings.get(candidate);
      if (opening?.phase === 'opening') opening.interacted = true;
    }
  };
  document.addEventListener('keydown', noteInteraction, true);
  document.addEventListener('pointerdown', noteInteraction, true);

  $(document).on('shown.bs.modal.y3gymImageFocus', '.modal', function () {
    const opening = openings.get(this);
    if (opening?.phase === 'opening') opening.phase = 'open';
  });
  $(document).on('hide.bs.modal.y3gymImageFocus', '.modal', function () {
    const opening = openings.get(this);
    if (opening) {
      opening.phase = 'closing';
      opening.backdrop = $(this).data('bs.modal')?.$backdrop?.[0];
    }
  });
  $(document).on('hidden.bs.modal.y3gymImageFocus', '.modal', function () {
    const opening = openings.get(this);
    if (opening && !$(this).data('bs.modal')?.isShown) restore(this, opening);
    if (currentModal === this) currentModal = null;
    const origin = origins.get(this);
    origins.delete(this);
    // ModalWorkflow already tried the original opener. Fall back only when it
    // left focus on body, and never restore an old opener over a newer modal.
    if (!origin || document.querySelector('body > .modal') || document.activeElement !== document.body) return;
    const widget = origin.widgetId && document.getElementById(origin.widgetId);
    const target = origin.editor?.isConnected && origin.editor.isContentEditable
      ? origin.editor
      : widget && [...widget.querySelectorAll('[data-w-dropdown-target="toggle"], [data-chooser-action-choose]')]
        .find(element => !element.disabled && element.getClientRects().length);
    if (origin.editor && target === origin.editor) origin.controller.focus();
    else target?.focus();
  });
})();
