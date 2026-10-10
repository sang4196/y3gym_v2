const CONTENT_WIDTH = 480;
const INITIAL_HEIGHT = 520;
const SCREEN_MARGIN = 48;
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

export function popupWorkArea(display = screen) {
  const width = display.availWidth || CONTENT_WIDTH;
  const height = display.availHeight || INITIAL_HEIGHT;
  return {
    left: Number.isFinite(display.availLeft) ? display.availLeft : 0,
    top: Number.isFinite(display.availTop) ? display.availTop : 0,
    width, height,
    marginX: Math.min(SCREEN_MARGIN, Math.max(0, (width - 200) / 2)),
    marginY: Math.min(SCREEN_MARGIN, Math.max(0, (height - 200) / 2)),
  };
}

// Sample different central cells without replacement before starting a new
// shuffled set. Jitter keeps the result random rather than a fixed cascade.
export function createPopupPlacementPlanner() {
  let cells = [];
  return () => {
    if (!cells.length) {
      cells = [-1, 0, 1].flatMap(y => [-1, 0, 1].map(x => ({ x, y })));
      for (let i = cells.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [cells[i], cells[j]] = [cells[j], cells[i]];
      }
    }
    const cell = cells.pop();
    return { x: cell.x * 0.72 + (Math.random() - 0.5) * 0.5,
      y: cell.y * 0.72 + (Math.random() - 0.5) * 0.5 };
  };
}

export function popupPosition(placement, width, height, display = screen) {
  const area = popupWorkArea(display);
  const roomX = Math.max(0, (area.width - width) / 2 - area.marginX);
  const roomY = Math.max(0, (area.height - height) / 2 - area.marginY);
  const offsetX = Math.min(180, area.width * 0.12, roomX) * placement.x;
  const offsetY = Math.min(100, area.height * 0.1, roomY) * placement.y;
  return {
    left: Math.round(area.left + (area.width - width) / 2 + offsetX),
    top: Math.round(area.top + (area.height - height) / 2 + offsetY),
  };
}

export function popupWindowFeatures(placement = { x: 0, y: 0 }) {
  const area = popupWorkArea(placement.display);
  // Reserve browser chrome before its real dimensions can be measured.
  const width = Math.min(CONTENT_WIDTH, area.width - area.marginX * 2 - 16);
  const height = Math.min(INITIAL_HEIGHT, area.height - area.marginY * 2 - 88);
  const { left, top } = popupPosition(placement, width + 16, height + 88, placement.display);
  return `popup=yes,width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`;
}

// Native window creation and resizeTo are asynchronous. In particular, a new
// window can initially report its opener's width or zero outer dimensions.
// Request an explicit content width, then measure again after the browser has
// applied it; never preserve that transient outerWidth as the desired width.
export function createPopupWindowSizer(frame, placement = { x: 0, y: 0 }) {
  let generation = 0;
  return async function fit() {
    const current = ++generation;
    if (!window.opener || window.opener.closed) return;
    const started = performance.now();
    const deadline = started + 4500;
    let stable = 0;
    let lastMove = null;
    let moveOffsetX = 0, moveOffsetY = 0;
    for (let attempt = 0; attempt < 12 && performance.now() < deadline; attempt++) {
      if (current !== generation || !frame.isConnected || window.closed) return;
      const borderWidth = window.outerWidth - window.innerWidth;
      const borderHeight = window.outerHeight - window.innerHeight;
      // Ignore impossible/stale chrome measurements while the native window
      // is being created. A later pass measures the settled browser chrome.
      const chromeWidth = borderWidth >= 0 && borderWidth <= 100 ? borderWidth : 0;
      const chromeHeight = borderHeight >= 0 && borderHeight <= 160 ? borderHeight : 0;
      // Some browsers open on their default monitor despite the opener's
      // requested coordinates. Center within the child's actual work area
      // rather than repeatedly attempting a restricted cross-monitor move.
      const area = popupWorkArea();
      const width = Math.min(CONTENT_WIDTH, area.width - area.marginX * 2 - chromeWidth);
      const height = Math.min(Math.ceil(frame.getBoundingClientRect().height),
        Math.max(1, area.height - area.marginY * 2 - chromeHeight));
      const fits = Math.abs(window.innerWidth - width) <= 1 &&
        Math.abs(window.innerHeight - height) <= 1;
      const position = popupPosition(placement, width + chromeWidth, height + chromeHeight);
      const positioned = Math.abs(window.screenX - position.left) <= 1 &&
        Math.abs(window.screenY - position.top) <= 1;
      stable = fits && positioned ? stable + 1 : 0;
      // New native windows can briefly echo requested bounds before the OS
      // applies its frame. Do not finish during that initial creation phase.
      if (stable >= 2 && performance.now() - started >= 750) return;
      if (!fits) {
        try { window.resizeTo(width + chromeWidth, height + chromeHeight); }
        catch { return; /* The compact document still works in a restricted tab. */ }
      }
      // Keep the same random anchor while content sizing settles. Do not move
      // on later viewport events or continuously override a user's dragging.
      if (fits && !positioned) {
        if (lastMove && lastMove.width === width && lastMove.height === height &&
            Math.abs(window.screenX - lastMove.left) <= 100 &&
            Math.abs(window.screenY - lastMove.top) <= 100) {
          // Some window managers add their frame offset to moveTo's request.
          // Learn only small, acknowledged offsets; an ignored move must not
          // turn into ever larger requests or a jump to another screen.
          moveOffsetX = window.screenX - lastMove.left;
          moveOffsetY = window.screenY - lastMove.top;
        }
        const left = position.left - moveOffsetX, top = position.top - moveOffsetY;
        try { window.moveTo(left, top); }
        catch { /* Position restrictions must not prevent reading/closing. */ }
        lastMove = { left, top, width, height };
      }
      await sleep(200);
    }
    // Stop retrying rather than fighting a browser restriction or later user
    // resizing. Long content remains scrollable within the available screen.
  };
}
