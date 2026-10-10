import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { branches } from '../branch-data.js';
import { renderHome, renderDetails } from './render-branches.mjs';
import { newsPosts } from '../news-data.js';
import { renderNewsPage, renderPostPage, newsCategories, publicNews, newsPageSize, newsFilename } from './render-news.mjs';

const directory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const template = await readFile(path.join(directory, 'templates', 'home.html'), 'utf8');
for (const [filename, state] of Object.entries({
  'index.html': 'two-branches',
  'preview-two-branches.html': 'two-branches',
  'preview-empty.html': 'empty',
  'preview-failures.html': 'failures',
})) await writeFile(path.join(directory, filename), renderHome(template, branches, state));

const details = await readFile(path.join(directory, 'templates', 'branches.html'), 'utf8');
for (const [filename, state] of Object.entries({
  'branches.html': 'two-branches',
  'branches-empty.html': 'empty',
  'branches-failures.html': 'failures',
})) await writeFile(path.join(directory, filename), renderDetails(details, branches, state));

const content = await readFile(path.join(directory, 'templates', 'content.html'), 'utf8');
for (const category of Object.keys(newsCategories)) {
  const count = Math.max(1, Math.ceil(publicNews(newsPosts, category).length / newsPageSize));
  for (let page = 1; page <= count; page++) await writeFile(path.join(directory, newsFilename(category, page)), renderNewsPage(content, newsPosts, { category, page }));
  await writeFile(path.join(directory, newsFilename(category, 1, 'news-empty')), renderNewsPage(content, [], { category, family: 'news-empty' }));
}
for (const post of publicNews(newsPosts)) await writeFile(path.join(directory, 'news', `${post.id}.html`), renderPostPage(content, post));

const post = await readFile(path.join(directory, 'news', 'visit.html'), 'utf8');
await writeFile(path.join(directory, 'news', 'visit-two-branches.html'),
  post.replaceAll('../index.html', '../preview-two-branches.html'));
console.log(`Built home, branch details, news lists/posts and state previews from ${branches.length} branches and ${publicNews(newsPosts).length} example posts.`);
