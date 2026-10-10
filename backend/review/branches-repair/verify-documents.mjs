import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../../', import.meta.url));
const output = new URL('./document-checks.json', import.meta.url);
const documents = ['README.md', 'backend/README.md', 'docs/PRD.md', 'docs/IMPLEMENTATION-PLAN.md', 'docs/WORKFLOW.md', 'prototype/DESIGN.md', 'backend/review/branches-repair/README.md'];
const report = { run: new Date().toISOString(), status: 'RUNNING', documents, localLinks: 0, markdownAnchors: 0, checks: [], errors: [] };
const slug = text => text.toLowerCase().replace(/<[^>]*>/g, '').replace(/[^\p{L}\p{N}_\-\s]/gu, '').replace(/\s/g, '-');
try {
  for (const name of documents) {
    const source = await fs.readFile(path.join(root, name), 'utf8');
    for (const match of source.matchAll(/(?<!!)\[[^\]]+\]\(([^\s)]+)\)/g)) {
      const target = match[1];
      if (/^[a-z][a-z0-9+.-]*:/i.test(target)) continue;
      const [relative, anchor] = target.split('#');
      const resolved = relative ? path.resolve(root, path.dirname(name), decodeURIComponent(relative)) : path.join(root, name);
      const stat = await fs.stat(resolved);
      assert(stat.isFile() || stat.isDirectory(), `${name}: missing ${target}`);
      report.localLinks++;
      if (anchor && resolved.endsWith('.md')) {
        const destination = await fs.readFile(resolved, 'utf8');
        const headings = [...destination.matchAll(/^#{1,6}\s+(.+)$/gm)].map(match => slug(match[1]));
        assert(headings.includes(decodeURIComponent(anchor)), `${name}: missing anchor ${target}`);
        report.markdownAnchors++;
      }
    }
  }
  report.checks.push({ name: 'Current document local files and Markdown anchors', result: 'PASS' });
  const inventory = JSON.parse(await fs.readFile(new URL('./changed-files.json', import.meta.url), 'utf8'));
  const changed = [...inventory.modifiedExisting, ...inventory.addedImplementation];
  for (const name of changed) {
    const source = await fs.readFile(path.join(root, name), 'utf8');
    assert(!source.split('\n').some(line => /[\t ]+$/.test(line)), `Trailing whitespace: ${name}`);
    assert(!source.includes('<<<<<<<') && !source.includes('>>>>>>>'), `Conflict marker: ${name}`);
  }
  report.checks.push({ name: 'Modified and new implementation files: whitespace and conflict markers', files: changed.length, result: 'PASS' });
  const required = ['backend/manage.py', 'backend/news/management/commands/bootstrap_branch_review.py', 'backend/news/tests/test_branch_browser.py', 'backend/news/tests/test_branches.py', 'backend/scripts/review-branches.mjs', 'backend/scripts/review-popup-position.mjs', 'backend/scripts/review-popup-sizing.mjs', 'backend/scripts/review-popup-revisit.mjs', 'backend/scripts/review-popup-edges.mjs', 'backend/review/branches-repair/run_checks.py', 'backend/news/tests/review_fixtures.py', 'backend/news/tests/test_withdrawal_concurrency.py'];
  for (const name of required) assert((await fs.stat(path.join(root, name))).isFile(), name);
  const tests = await fs.readFile(path.join(root, 'backend/news/tests/test_branches.py'), 'utf8');
  assert(tests.includes('def test_withdraw_and_republish_restore_only_the_requested_revision_and_media('));
  const browserTest = await fs.readFile(path.join(root, 'backend/news/tests/test_branch_browser.py'), 'utf8');
  assert(browserTest.includes('Y3GYM_RUN_BRANCH_BROWSER') && browserTest.includes('StaticLiveServerTestCase'));
  const urls = await fs.readFile(path.join(root, 'backend/config/urls.py'), 'utf8');
  assert(urls.includes('path("branches/",'));
  report.checks.push({ name: 'New documented commands, test names, opt-in environment and route definitions exist', result: 'PASS' });
  const prd = await fs.readFile(path.join(root, 'docs/PRD.md'), 'utf8');
  assert(prd.includes('본점 1곳·공개 본점 우선/새 방문 기본값') && !prd.includes('| Google 지도, 본점/삭제/복원 등의 과거 운영 정책 | 새 프로젝트 확정 근거 없음.'));
  report.checks.push({ name: 'PRD section 7 distinguishes newly confirmed branch policy from unresolved legacy policy', result: 'PASS' });
  for (const route of ['/?branch=main', '/?branch=second', '/branches/?branch=second', '/news/?branch=second', '/branches/?branch=unknown']) {
    const response = await fetch('http://localhost:8768' + route);
    assert.equal(response.status, 200, route);
    const html = await response.text();
    assert(html.includes('branch-navigation-data') && !html.includes('http://localhost:8767'), route);
    report.checks.push({ name: 'Read-only public route', route, status: response.status, result: 'PASS' });
  }
  const admin = await fetch('http://localhost:8768/admin/snippets/news/branch/', { redirect: 'manual' });
  assert.equal(admin.status, 302);
  assert(admin.headers.get('location').startsWith('/admin/login/'));
  report.checks.push({ name: 'Administrator branch route requires login', status: admin.status, result: 'PASS' });
  report.status = 'PASS';
} catch (error) {
  report.status = 'FAIL';
  report.errors.push(error.stack);
  process.exitCode = 1;
} finally {
  await fs.writeFile(output, JSON.stringify(report, null, 2) + '\n');
}
console.log(`${report.status}: ${report.localLinks} local links, ${report.markdownAnchors} Markdown anchors, ${report.checks.length} checks`);
