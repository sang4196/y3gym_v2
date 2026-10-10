// Public, fictional fixtures only. This is not a content API or publication boundary.
export function getPopupExample(example = 'default') {
  const post = {
    id: 'visit', published: true, title: '방문 전 확인해주세요', url: 'news/visit.html',
  };
  const popup = {
    id: 'visit-notice', enabled: true, postId: 'visit',
    title: '방문 전 확인해주세요',
    description: '운영시간과 위치를 살펴보고, 궁금한 점은 해당 지점으로 문의해주세요.',
    image: 'assets/images/gym-hero.png',
    startsAt: '2026-10-01T00:00:00+09:00',
    endsAt: '2026-11-01T00:00:00+09:00',
  };
  // All current examples return to the default two-branch home through this post.
  if (example === 'empty') return { popup: null, post: null };
  if (example === 'expired') popup.endsAt = '2026-10-01T00:00:00+09:00';
  if (example === 'future') popup.startsAt = '2026-10-20T00:00:00+09:00';
  if (example === 'disabled') popup.enabled = false;
  if (example === 'unpublished') post.published = false;
  if (example === 'missing-post') return { popup, post: null };
  if (example === 'no-image') popup.image = null;
  if (example === 'image-failure') popup.image = 'assets/images/missing-popup.png';
  return { popup, post };
}
