// Draftail 7.4.3 writes its hidden form value after a 250ms debounce. Flush
// before Wagtail serializes a submitted form so a rapid save keeps the last
// typed characters. This changes no editor layout or publication policy.
document.addEventListener('submit', event => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) return;
  for (const field of form.querySelectorAll('input[type="hidden"]')) {
    if (field.draftailEditor?.saveState) field.draftailEditor.saveState();
  }
}, true);
