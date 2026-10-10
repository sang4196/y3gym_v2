export const storagePrefix = 'y3gym.prototype.';

export function isPopupEligible(popup, post, now = Date.now()) {
  if (!popup?.enabled || !post?.published || popup.postId !== post.id) return false;
  const start = Date.parse(popup.startsAt);
  const end = Date.parse(popup.endsAt);
  return Number.isFinite(start) && Number.isFinite(end) && start < end && start <= now && now < end;
}

export function nextKoreanMidnight(now = Date.now()) {
  const day = 24 * 60 * 60 * 1000;
  const koreanOffset = 9 * 60 * 60 * 1000;
  return (Math.floor((now + koreanOffset) / day) + 1) * day - koreanOffset;
}

export function readStorage(name, key) {
  try {
    return { available: true, value: window[name].getItem(storagePrefix + key) };
  } catch {
    return { available: false, value: null };
  }
}

export function writeStorage(name, key, value) {
  try {
    window[name].setItem(storagePrefix + key, String(value));
    return true;
  } catch {
    return false;
  }
}
