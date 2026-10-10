import { branches } from './branch-data.js';
import { newsPosts, newsPageSize } from './news-data.js';

const params = new URLSearchParams(location.search);
let saved = null;
try { saved = sessionStorage.getItem('y3gym.prototype.selected-branch'); } catch { /* Explicit URL still works. */ }
const requested = params.has('branch') ? params.get('branch') : saved;
const selected = branches.find(branch => branch.id === requested);
const root = document.body.dataset.siteRoot || '../';
const category = ['notices', 'events'].includes(params.get('category')) ? params.get('category') : 'all';
const count = newsPosts.filter(post => post.published && (category === 'all' || post.category === category)).length;
const requestedPage = Number(params.get('listPage'));
const page = Number.isInteger(requestedPage) && requestedPage > 0 && requestedPage <= Math.ceil(count / newsPageSize) ? requestedPage : 1;
const returnPath = `${root}news${category === 'all' ? '' : '-' + category}${page === 1 ? '' : '-page-' + page}.html`;

document.querySelectorAll('[data-branch-page], [data-news-link], [data-news-return]').forEach(link => {
  const href = link.hasAttribute('data-news-return') ? returnPath : link.getAttribute('href');
  const url = new URL(href, location.href);
  if (selected) url.searchParams.set('branch', selected.id);
  else if (url.hash === '#contact') url.hash = 'branch';
  link.href = url.href;
});

const contactBar = document.querySelector('.mobile-contact-bar');
if (contactBar) contactBar.setAttribute('aria-label', selected ? `${selected.name} 문의 안내` : '문의할 지점 선택');
document.querySelectorAll('.mobile-contact-bar .button').forEach(link => {
  link.setAttribute('aria-label', selected ? `${selected.name} ${link.textContent.trim()}` : `${link.textContent.trim()} · 지점 선택`);
});
