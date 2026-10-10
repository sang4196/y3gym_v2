// Read only public branch revisions, or the authorized preview's metadata.
// The approved prototype controller continues to own tabs and menus.
const branches = JSON.parse(document.getElementById('branch-navigation-data')?.textContent || '[]');
const storageKey = 'y3gym.prototype.selected-branch';
function synchronize() {
  const params = new URLSearchParams(location.search);
  let saved;
  try { saved = sessionStorage.getItem(storageKey); } catch { /* URL still works. */ }
  const requested = params.has('branch') ? params.get('branch') : saved;
  const selected = branches.find(branch => branch.id === requested) || branches[0];
  const pageURL = new URL(location.href);
  if (selected) {
    pageURL.searchParams.set('branch', selected.id);
    try { sessionStorage.setItem(storageKey, selected.id); } catch { /* No storage required. */ }
  } else {
    pageURL.searchParams.delete('branch');
    try { sessionStorage.removeItem(storageKey); } catch { /* No storage required. */ }
  }
  history.replaceState(null, '', pageURL);
  document.querySelectorAll('[data-branch-page], [data-news-link], [data-news-return], [data-popup-post]').forEach(link => {
    const url = new URL(link.getAttribute('href'), location.href);
    if (selected) url.searchParams.set('branch', selected.id);
    else url.searchParams.delete('branch');
    if (url.hash === '#contact' || url.hash.startsWith('#contact-')) url.hash = selected ? `contact-${selected.id}` : 'branch';
    link.href = url.href;
  });
  document.querySelectorAll('[data-inquiry]').forEach(element => {
    const channel = element.dataset.inquiry;
    element.hidden = !selected || !(channel === 'any' ? selected.phone || selected.channel : selected[channel]);
    if (selected && element.matches('a, .mobile-contact-bar')) element.setAttribute('aria-label', `${selected.name} ${element.matches('a') ? element.textContent.trim() : '문의 안내'}`);
  });
  document.querySelectorAll('[data-selected-branch-name]').forEach(element => { element.textContent = selected?.name || '준비 중인 지점'; });
  const tab = selected && document.getElementById(`tab-${selected.id}`);
  const tabList = tab?.closest('[data-branch-tabs]');
  if (tabList) {
    const outer = tabList.getBoundingClientRect();
    const inner = tab.getBoundingClientRect();
    // Keep the selected tab visible without moving the page vertically.
    if (inner.left < outer.left) tabList.scrollLeft += inner.left - outer.left;
    else if (inner.right > outer.right) tabList.scrollLeft += inner.right - outer.right;
  }
  // Without tab enhancement, keep all server-rendered address/hours readable.
  if (document.querySelector('[data-branch-tab][role="tab"]')) document.querySelectorAll('[data-branch-fallback]').forEach(element => { element.hidden = true; });
}
const preview = document.body.dataset.previewBranch;
if (preview) document.querySelector(`#tab-${CSS.escape(preview)}`)?.click();
synchronize();
document.querySelector('[data-branch-tabs]')?.addEventListener('click', synchronize);
document.querySelector('[data-branch-tabs]')?.addEventListener('keydown', synchronize);
window.addEventListener('popstate', synchronize);
window.addEventListener('hashchange', synchronize);
