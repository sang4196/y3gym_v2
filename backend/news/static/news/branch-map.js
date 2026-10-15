// Only the selected panel requests an address. A failed request is not retried
// automatically, and no guessed/default coordinate is ever used.
const config = JSON.parse(document.getElementById('branch-map-config')?.textContent || '{}');
const key = typeof config?.key === 'string' ? config.key.trim() : '';
const elements = [...document.querySelectorAll('[data-branch-map]')];
const states = elements.map(element => ({
  element,
  address: element.dataset.mapAddress.trim(),
  name: element.dataset.mapName,
  canvas: element.querySelector('[data-map-canvas]'),
  fallback: element.querySelector('[data-map-fallback]'),
  status: element.querySelector('[data-map-status]'),
  link: element.querySelector('[data-map-link]'),
  started: false,
}));
let sdkPromise;
let geocoder;
const addressRequests = new Map();

function loadSDK() {
  if (sdkPromise) return sdkPromise;
  sdkPromise = new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('SDK unavailable')), 12000);
    const fail = () => { clearTimeout(timer); reject(new Error('SDK unavailable')); };
    const script = document.createElement('script');
    const url = new URL('https://dapi.kakao.com/v2/maps/sdk.js');
    url.searchParams.set('appkey', key);
    url.searchParams.set('libraries', 'services');
    url.searchParams.set('autoload', 'false');
    script.id = 'branch-kakao-sdk';
    script.src = url.href;
    script.async = true;
    script.onerror = fail;
    script.onload = () => {
      try {
        if (!window.kakao?.maps?.load) return fail();
        window.kakao.maps.load(() => {
          const sdk = window.kakao.maps;
          if (!sdk.Map || !sdk.Marker || !sdk.LatLng || !sdk.services?.Geocoder) return fail();
          clearTimeout(timer);
          resolve(sdk);
        });
      } catch { fail(); }
    };
    document.head.append(script);
  });
  return sdkPromise;
}

function locate(sdk, address) {
  if (addressRequests.has(address)) return addressRequests.get(address);
  const request = new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Address unavailable')), 12000);
    const fail = () => { clearTimeout(timer); reject(new Error('Address unavailable')); };
    try {
      geocoder ||= new sdk.services.Geocoder();
      // EXACT excludes similar-name matches. Two results reveal ambiguity;
      // region/road-only matches do not establish an individual address.
      geocoder.addressSearch(address, (rows, status, pagination) => {
        if (status !== sdk.services.Status.OK || !Array.isArray(rows) || rows.length !== 1
          || pagination?.hasNextPage || Number(pagination?.totalCount || 1) > 1) return fail();
        const row = rows[0];
        if (!['ROAD_ADDR', 'REGION_ADDR'].includes(row.address_type)
          || typeof row.x !== 'string' || !row.x.trim()
          || typeof row.y !== 'string' || !row.y.trim()) return fail();
        const latitude = Number(row.y);
        const longitude = Number(row.x);
        if (!Number.isFinite(latitude) || !Number.isFinite(longitude)
          || Math.abs(latitude) > 90 || Math.abs(longitude) > 180) return fail();
        clearTimeout(timer);
        resolve({ latitude, longitude });
      }, { analyze_type: sdk.services.AnalyzeType.EXACT, size: 2, page: 1 });
    } catch { fail(); }
  });
  addressRequests.set(address, request);
  return request;
}

function visible(state) {
  const panel = state.element.closest('[data-branch-panel]');
  const selected = panel && document.getElementById(`tab-${panel.dataset.branchId}`);
  return selected?.getAttribute('aria-selected') === 'true'
    && state.element.getBoundingClientRect().width > 0
    && state.element.getBoundingClientRect().height > 0;
}

function fallback(state, message) {
  state.canvas.hidden = true;
  state.fallback.hidden = false;
  state.status.textContent = message;
  state.element.dataset.mapState = 'fallback';
}

function draw(state) {
  if (!visible(state) || !state.coordinates) return;
  try {
    if (!state.map) {
      const { latitude, longitude } = state.coordinates;
      state.center = new state.sdk.LatLng(latitude, longitude); // y, x (WGS84)
      state.canvas.hidden = false;
      state.map = new state.sdk.Map(state.canvas, { center: state.center, level: 3 });
      state.marker = new state.sdk.Marker({ map: state.map, position: state.center, title: state.name });
      state.fallback.hidden = true;
      state.link.href = `https://map.kakao.com/link/map/${encodeURIComponent(state.name)},${latitude},${longitude}`;
      state.status.textContent = '주소 검색 결과 위치를 표시했습니다. 방문 전 주소를 확인하세요.';
      state.element.dataset.mapState = 'ready';
    }
    state.map.relayout();
    state.map.setCenter(state.center);
  } catch {
    state.coordinates = null;
    fallback(state, '지도를 표시할 수 없습니다. 카카오맵에서 주소를 확인하세요.');
  }
}

async function start(state) {
  state.started = true;
  state.element.dataset.mapState = 'loading';
  state.status.textContent = '주소로 지도 위치를 확인하고 있습니다.';
  try {
    state.sdk = await loadSDK();
    state.coordinates = await locate(state.sdk, state.address);
    draw(state);
  } catch {
    fallback(state, '주소의 정확한 지도 위치를 확인하지 못했습니다. 카카오맵에서 주소를 검색하세요.');
  }
}

let frame;
function schedule() {
  if (frame) return;
  frame = requestAnimationFrame(() => {
    frame = null;
    for (const state of states) {
      if (!visible(state)) continue;
      if (state.map && state.coordinates) draw(state);
      else if (state.coordinates) draw(state);
      else if (!state.started && key && state.address) start(state);
    }
  });
}

if (key && states.length) {
  for (const panel of document.querySelectorAll('[data-branch-panel]')) {
    new MutationObserver(schedule).observe(panel, { attributes: true, attributeFilter: ['hidden'] });
  }
  const resize = new ResizeObserver(schedule);
  for (const state of states) resize.observe(state.element);
  window.addEventListener('resize', schedule);
  schedule();
}
