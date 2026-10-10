// Carry an explicit selection through the common announcement and back to home.
export function withBranchContext(href) {
  const branch = new URLSearchParams(location.search).get('branch');
  if (!branch) return href;
  const url = new URL(href, location.href);
  url.searchParams.set('branch', branch);
  return url.href;
}
