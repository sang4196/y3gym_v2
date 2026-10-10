import { newsPosts, newsPageSize } from '../news-data.js';
export { newsPageSize };

const escape = value => String(value).replace(/[&<>"']/g, character => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
})[character]);
export const newsCategories = { all: '전체', notices: '공지', events: '이벤트' };
export const publicNews = (posts = newsPosts, category = 'all') => posts
  .filter(post => post.published && (category === 'all' || post.category === category))
  .sort((a, b) => b.publishedAt.localeCompare(a.publishedAt) || a.id.localeCompare(b.id));

export function newsFilename(category = 'all', page = 1, family = 'news') {
  if (!Object.hasOwn(newsCategories, category) || !Number.isInteger(page) || page < 1) throw new Error('Invalid news page.');
  return `${family}${category === 'all' ? '' : '-' + category}${page === 1 ? '' : '-page-' + page}.html`;
}

export function renderNewsItems(posts = publicNews(), { preview = false, category = 'all', page = 1 } = {}) {
  return posts.map(post => {
    if (!/^[a-z][a-z0-9-]*$/.test(post.id)) throw new Error('News ids must be lowercase slugs.');
    const heading = preview ? 'h3' : 'h2';
    const query = preview ? '' : `?category=${category}&listPage=${page}`;
    return `<article class="news-item" aria-labelledby="news-${escape(post.id)}-title">
      <span class="news-category">${escape(newsCategories[post.category])}</span>
      <div class="news-copy"><${heading} id="news-${escape(post.id)}-title"><a class="news-title-link" href="news/${escape(post.id)}.html${query}" data-news-link>${escape(post.title)}</a></${heading}><p>${escape(post.summary)}</p></div>
      <time datetime="${escape(post.publishedAt)}">${escape(post.publishedAt.replaceAll('-', '.'))}<span class="sr-only"> 날짜 예시</span></time>
    </article>`;
  }).join('\n');
}

function fill(template, values) {
  return template.replace(/\{\{(title|root|page|content)\}\}/g, (_, key) => values[key]);
}

export function renderNewsPage(template, posts = newsPosts, { category = 'all', page = 1, family = 'news' } = {}) {
  if (!Object.hasOwn(newsCategories, category)) throw new Error('Unknown news category.');
  const filtered = publicNews(posts, category);
  const pageCount = Math.max(1, Math.ceil(filtered.length / newsPageSize));
  const current = Number.isInteger(page) ? Math.min(pageCount, Math.max(1, page)) : 1;
  const visible = filtered.slice((current - 1) * newsPageSize, current * newsPageSize);
  const filters = Object.entries(newsCategories).map(([key, label]) => `<a class="news-filter" href="${newsFilename(key, 1, family)}" data-news-link${category === key ? ' aria-current="page"' : ''}>${label}</a>`).join('');
  const pagination = pageCount > 1 ? `<nav class="news-pagination" aria-label="소식 페이지">${Array.from({ length: pageCount }, (_, index) => `<a class="news-page-link" href="${newsFilename(category, index + 1, family)}" data-news-link aria-label="${index + 1}페이지"${index + 1 === current ? ' aria-current="page"' : ''}>${index + 1}</a>`).join('')}</nav>` : '';
  const content = `<section class="page-intro" aria-labelledby="page-title"><div class="container">
      <nav class="breadcrumb" aria-label="현재 위치"><a href="index.html" data-branch-page>홈</a><span aria-hidden="true">/</span><span aria-current="page">소식</span></nav>
      <h1 id="page-title">소식</h1><p class="section-description">모든 지점의 공지와 이벤트를 확인하세요.</p><p class="content-example">시각 검토용 · 제목·내용·날짜는 모두 임시 예시입니다.</p>
    </div></section>
    <section class="news-index container" aria-label="소식 목록">
      <nav class="news-filters" aria-label="소식 분류">${filters}</nav>
      <p class="news-result-count">${escape(newsCategories[category])} ${filtered.length}건</p>
      ${visible.length ? `<div class="news-list">${renderNewsItems(visible, { category, page: current })}</div>` : `<div class="news-empty-state"><h2>등록된 ${category === 'all' ? '소식이' : newsCategories[category] + '가'} 없습니다.</h2><p>새로운 소식이 등록되면 이곳에서 확인할 수 있습니다.</p></div>`}
      ${pagination}
    </section>`;
  return fill(template, { title: '소식', root: '', page: 'news-list', content }).replaceAll('news.html', newsFilename('all', 1, family));
}

export function renderPostPage(template, post) {
  const content = `<article class="post-document container" aria-labelledby="post-title">
    <nav class="breadcrumb" aria-label="현재 위치"><a href="../index.html" data-branch-page>홈</a><span aria-hidden="true">/</span><a href="../news.html" data-news-return>소식</a><span aria-hidden="true">/</span><span aria-current="page">${escape(newsCategories[post.category])}</span></nav>
    <header class="post-header"><p class="eyebrow">${escape(newsCategories[post.category])} · 전체 지점 공통</p><h1 id="post-title">${escape(post.title)}</h1><p class="post-meta">등록일 <time datetime="${escape(post.publishedAt)}">${escape(post.publishedAt.replaceAll('-', '.'))}</time></p><p class="content-example">시각 검토용 · 제목·본문·날짜는 임시 예시입니다.</p></header>
    <div class="post-body">${post.body}</div>
  </article>`;
  return fill(template, { title: escape(post.title), root: '../', page: 'news-post', content });
}
