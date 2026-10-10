import { publicNews, renderNewsItems } from './render-news.mjs';

const escape = value => String(value).replace(/[&<>"']/g, character => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
})[character]);

function renderFacilityGallery(branch, gallery, { home = false, heading = '' } = {}) {
  if (!gallery) return '';
  const id = escape(branch.id);
  return `<div class="facility-gallery${home ? ' facility-gallery--preview' : ''}"${home ? ` id="${id}-facilities" data-branch-section="facilities"` : ''} data-facility-gallery aria-label="${escape(branch.name)} 시설 사진">
    ${heading}
    <div class="facility-gallery-viewport" data-gallery-viewport><div class="facility-grid" id="${id}-gallery-track" data-gallery-track>${gallery}</div></div>
    <p class="sr-only" role="status" aria-live="polite" data-gallery-status></p>
  </div>`;
}

function renderHomePreview(branch, gallery, detailHref) {
  const id = escape(branch.id);
  return `<div class="container branch-preview">
    <div class="branch-preview-heading"><div>
      <h3 class="branch-panel-name" id="${id}-branch-name">${escape(branch.name)}</h3>
      <p class="content-example">${escape(gallery ? branch.facilityNote : '등록된 시설 사진이 없습니다.')}</p>
    </div><a class="text-link" href="${escape(detailHref)}?branch=${id}">${escape(branch.label)} 자세히 보기 <span aria-hidden="true">→</span></a></div>
    ${renderFacilityGallery(branch, gallery, { home: true })}
  </div>`;
}

export function renderBranchBrowser(branches, { empty = false, failures = false, view = 'detail', detailHref = 'branches.html' } = {}) {
  const isHome = view === 'home';
  const ids = branches.map(branch => branch.id);
  if (ids.some(id => !/^[a-z][a-z0-9-]*$/.test(id)) || new Set(ids).size !== ids.length) throw new Error('Branch ids must be unique lowercase slugs.');
  if (!branches.length) return '<section class="branch-browser" id="branch"><div class="container" id="contact"><h2>지점 안내</h2><p class="empty-message">등록된 지점이 없습니다.</p></div></section>';
  const tabs = branches.map(branch => `<a class="branch-tab" id="tab-${escape(branch.id)}" href="#branch-${escape(branch.id)}" data-branch-tab>${escape(branch.name)}</a>`).join('\n');
  const panels = branches.map((branch, index) => {
    const id = escape(branch.id);
    const contactId = `contact-${id}`;
    const gallery = empty ? '' : branch.facilities.map((facility, facilityIndex) => `
      <figure class="facility" data-gallery-slide><div class="facility-image-frame"><img src="assets/images/${escape(failures && index === 0 && facilityIndex === 0 ? 'missing-strength.png' : facility.image)}" alt="${escape(branch.name)} · ${escape(facility.alt)}" width="1536" height="1024" loading="lazy" decoding="async"></div>
        <figcaption><p class="image-note">임시·합성 이미지</p><h4>${escape(facility.title)}</h4><p class="facility-description">${escape(facility.description)}</p></figcaption>
      </figure>`).join('');
    const trainers = empty || isHome ? '' : branch.trainers.map((trainer, trainerIndex) => `
      <article class="trainer" aria-labelledby="${id}-trainer-${escape(trainer.id)}-name">
        <figure class="trainer-portrait"><div class="profile-image-frame"><img src="assets/images/${escape(failures && index === 0 && trainerIndex === 0 ? 'missing-trainer.png' : trainer.image)}" alt="${escape(trainer.alt)}" width="1122" height="1402" loading="lazy" decoding="async"></div><figcaption class="image-note">임시·합성 인물</figcaption></figure>
        <div class="trainer-copy"><p class="eyebrow">${escape(branch.name)}</p><h4 id="${id}-trainer-${escape(trainer.id)}-name">${escape(trainer.name)} <span class="inline-example">예시</span></h4><p class="trainer-description">${escape(trainer.description)}</p><a class="text-link" href="#${contactId}">${escape(branch.label)} 문의 <span aria-hidden="true">→</span></a></div>
      </article>`).join('');
    return `<article class="branch-panel" id="branch-${id}" data-branch-panel data-branch-id="${id}" data-branch-name="${escape(branch.name)}" aria-labelledby="${id}-branch-name">
      ${isHome ? renderHomePreview(branch, gallery, detailHref) : `<div class="branch-panel-summary"><div class="container">
        <p class="eyebrow">지점 정보 · 예시</p><h3 class="branch-panel-name" id="${id}-branch-name">${escape(branch.name)}</h3>
        <dl class="branch-information">
          <div class="branch-information-item"><dt>위치</dt><dd>${escape(branch.address)}</dd><dd class="branch-detail">실제 주소가 아닌 예시입니다.</dd></div>
          <div class="branch-information-item"><dt>운영시간 <span class="example-label">예시</span></dt><dd>평일 ${escape(branch.weekday)}</dd><dd class="branch-detail">주말 ${escape(branch.weekend)}</dd></div>
          <div class="branch-information-item"><dt>문의</dt><dd><a class="text-link" href="#${contactId}">${escape(branch.label)} 위치와 문의 <span aria-hidden="true">→</span></a></dd><dd class="branch-detail">해당 지점의 문의 정보를 확인하세요.</dd></div>
        </dl>
      </div></div>`}
      ${gallery && !isHome ? `<section class="facilities" id="${id}-facilities" data-branch-section="facilities" aria-labelledby="${id}-facilities-title"><div class="container">
        ${renderFacilityGallery(branch, gallery, { heading: `<div class="section-heading"><div><h3 class="branch-section-title" id="${id}-facilities-title">시설 둘러보기</h3><p class="section-description">${escape(branch.facilityNote)}</p></div></div>` })}
      </div></section>` : ''}
      ${trainers ? `<section class="trainers surface-section" id="${id}-trainers" data-branch-section="trainers" aria-labelledby="${id}-trainers-title"><div class="container">
        <div class="section-heading"><div><h3 class="branch-section-title" id="${id}-trainers-title">함께할 트레이너</h3><p class="section-description">${escape(branch.name)} 소속 트레이너입니다.</p><p class="content-example">사진과 이름, 소개는 배치 확인용 예시입니다.</p></div></div><div class="trainer-grid${branch.trainers.length === 1 ? ' trainer-grid--single' : ''}">${trainers}</div>
      </div></section>` : ''}
      ${isHome ? '' : `<section class="location" id="${contactId}" data-branch-section="contact" aria-labelledby="${id}-location-title"><div class="container">
        <div class="section-heading"><div><h3 class="branch-section-title" id="${id}-location-title">위치와 문의</h3><p class="section-description">${escape(branch.name)}의 주소와 운영시간을 확인하세요.</p></div></div>
        <div class="location-layout branch-contact">
          <div class="map-placeholder" role="img" aria-label="실제 지도가 연결되지 않은 지도 배치 예시">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M19 10c0 5-7 10-7 10S5 15 5 10a7 7 0 1 1 14 0Z" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="10" r="2.5" stroke="currentColor" stroke-width="1.5"/></svg>
            <span class="map-label">${failures ? '지도를 표시할 수 없습니다.' : '지도 표시 영역'}</span><span class="map-note">${failures ? '모의 실패 상태입니다. 주소와 문의 정보는 그대로 확인할 수 있습니다.' : '실제 지도는 연결하지 않았습니다.'}</span>
          </div>
          <div class="location-information" data-contact-group data-branch-name="${escape(branch.name)}"><p class="eyebrow">문의 대상 지점</p><h4>${escape(branch.name)}</h4>
            <dl class="location-details"><div><dt>주소</dt><dd>${escape(branch.address)}<span class="detail-note">실제 주소가 아닌 예시입니다.</span></dd></div><div><dt>운영시간</dt><dd>평일 ${escape(branch.weekday)}<br>주말 ${escape(branch.weekend)}<span class="detail-note">운영시간 예시입니다.</span></dd></div><div><dt>연락처</dt><dd>전화번호 예시: ${escape(branch.phone)}<span class="detail-note">카카오톡: ${escape(branch.channel)} · 실제 연결 없음</span></dd></div></dl>
            <div class="contact-buttons location-contact-buttons"><button class="button button--primary" type="button" data-preview-contact="전화">전화 문의</button><button class="button button--secondary" type="button" data-preview-contact="카카오톡">카카오톡 문의</button></div>
            <p class="contact-note" id="${id}-contact-status" role="status" aria-live="polite" data-contact-feedback>시제품에서는 실제 문의로 연결되지 않습니다.</p>
            <a class="text-link" href="#branch">지점 선택으로 돌아가기 <span aria-hidden="true">↑</span></a>
          </div>
        </div>
      </div></section>`}
    </article>`;
  }).join('\n');
  return `<section class="branch-browser${isHome ? ' branch-browser--preview' : ''}" id="branch" aria-labelledby="branch-title" data-branch-browser>
    <div class="branch-browser-heading"><div class="container" id="contact"><h2 id="branch-title">${isHome ? '지점 둘러보기' : '지점 선택'}</h2><p class="section-description">${isHome ? '지점을 선택해 운동 공간을 살펴보세요.' : '지점을 선택하면 시설과 트레이너, 위치와 문의 정보를 함께 확인할 수 있습니다.'}</p><p class="content-example">지점 정보는 예시입니다.</p><nav class="branch-tab-list" aria-label="지점 선택" data-branch-tabs>${tabs}</nav></div></div>
    ${panels}
  </section>`;
}

export function renderHome(template, branches, state = 'two-branches') {
  const empty = state === 'empty';
  const failures = state === 'failures';
  const first = branches[0];
  let html = template.replace('<body>', `<body data-demo-state="${state}">`)
    .replace('<!-- NEWS_ITEMS -->', renderNewsItems(publicNews().slice(0, 3), { preview: true }))
    .replace('<!-- BRANCH_BROWSER -->', renderBranchBrowser(branches, { empty, failures, view: 'home', detailHref: detailPage(state) }))
    .replaceAll('branches.html', detailPage(state))
    .replaceAll('{{facilitiesHref}}', first && !empty ? `${first.id}-facilities` : 'branch')
    .replaceAll('{{trainersHref}}', first && !empty ? `${first.id}-trainers` : 'branch')
    .replaceAll('{{contactHref}}', first ? `contact-${first.id}` : 'branch');
  if (empty) {
    html = html.replaceAll('news.html', 'news-empty.html')
      .replace(/<figure class="hero-figure">[^]*?<\/figure>/, '')
      .replace('class="hero-layout"', 'class="hero-layout hero-layout--text-only"')
      .replaceAll(/<a[^>]*data-branch-jump="(?:facilities|trainers)"[^>]*>[^]*?<\/a>/g, '')
      .replace(/<div class="popup-entry"[^]*?<\/div>/, '')
      .replace(/<div class="news-list">[^]*?<\/article>\s*<\/div>/, '<p class="empty-message">등록된 소식이 없습니다.</p>')
      .replace('아래 제목·내용·날짜는 화면 검토용 예시입니다.', '소식이 등록되면 이곳에서 확인할 수 있습니다.');
  }
  if (failures) html = html.replace('assets/images/gym-hero.png', 'assets/images/missing-hero.png');
  return html;
}

function detailPage(state) {
  return state === 'empty' ? 'branches-empty.html' : state === 'failures' ? 'branches-failures.html' : 'branches.html';
}

export function renderDetails(template, branches, state = 'two-branches') {
  const empty = state === 'empty';
  return template.replace('<body>', `<body data-demo-state="${state}" data-page="branches">`)
    .replaceAll('news.html', empty ? 'news-empty.html' : 'news.html')
    .replace('<!-- BRANCH_BROWSER -->', renderBranchBrowser(branches, { empty, failures: state === 'failures' }))
    .replaceAll('{{facilitiesHref}}', branches[0] && !empty ? `${branches[0].id}-facilities` : 'branch')
    .replaceAll('{{contactHref}}', branches[0] ? `contact-${branches[0].id}` : 'branch');
}
