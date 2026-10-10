"""Read-only WORKFLOW-01 document audit. Results are printed to stdout.

Run from the repository root: python3 backend/review/workflow-01/verify.py
The historical developer snapshots must still exist in /tmp.
This script never launches product tests, services, or Git mutations.
"""

import difflib
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = Path('/tmp/y3gym-workflow-01-rgrecg_l')
OUTPUT_PREFIX = 'backend/review/workflow-01/'
TARGETS = ['AGENTS.md', 'README.md', 'docs/WORKFLOW.md']


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path):
    return json.loads(path.read_text())


def strip_fences(text):
    return re.sub(r'^```[^\n]*\n.*?^```\s*$', '', text, flags=re.M | re.S)


def anchors(path):
    found = set()
    counts = {}
    for heading in re.findall(r'^#{1,6}\s+(.+?)\s*#*$', strip_fences(path.read_text()), re.M):
        heading = re.sub(r'[*`_]', '', heading).lower()
        heading = ''.join(c for c in heading if not unicodedata.category(c).startswith(('P', 'S')) or c in '-_')
        slug = heading.replace(' ', '-')
        index = counts.get(slug, 0)
        counts[slug] = index + 1
        found.add(slug + (f'-{index}' if index else ''))
    return found


before = load_json(REFERENCE / 'before.json')
after = load_json(REFERENCE / 'after.json')
policy = load_json(REFERENCE / 'policy-update-checks.json')
evidence = load_json(Path(__file__).with_name('requirements-evidence.json'))
paths = [p for p in git('ls-files', '-z', '--cached', '--others', '--exclude-standard').split('\0') if p and not p.startswith(OUTPUT_PREFIX) and (ROOT / p).is_file()]
current = {p: digest(ROOT / p) for p in sorted(paths)}
changed = sorted(p for p in set(before['files']) | set(current) if before['files'].get(p) != current.get(p))
protected = {p: h for p, h in before['files'].items() if p not in TARGETS}
protected_changes = sorted(p for p, h in protected.items() if current.get(p) != h)
index_path = Path(git('rev-parse', '--git-path', 'index').strip())
if not index_path.is_absolute():
    index_path = ROOT / index_path

checks = []


def check(name, ok, details):
    checks.append({'name': name, 'status': 'PASS' if ok else 'FAIL', 'details': details})


check('scope_preservation', changed == sorted(TARGETS) and not protected_changes,
      {'before_count': len(before['files']), 'current_count_excluding_new_audit': len(current), 'changed_paths': changed, 'protected_file_count': len(protected), 'protected_changes': protected_changes})
check('final_target_hashes', all(current.get(p) == policy['target_hashes'][p]['after_policy_update'] for p in TARGETS),
      {p: current.get(p) for p in TARGETS})
check('git_index_preservation', digest(index_path) == before['index_sha256'] == after['index_sha256'],
      {'current_sha256': digest(index_path), 'baseline_sha256': before['index_sha256']})
baseline_ok = all(digest(REFERENCE / p) == before['files'][p] for p in ['AGENTS.md', 'README.md'])
reconstructed = ''
for p in TARGETS:
    old = (REFERENCE / p).read_text().splitlines(keepends=True) if p in before['files'] else []
    new = (ROOT / p).read_text().splitlines(keepends=True)
    reconstructed += ''.join(difflib.unified_diff(old, new, fromfile=f'before/{p}' if old else '/dev/null', tofile=f'after/{p}'))
check('developer_final_patch_matches_actual_files', baseline_ok and reconstructed == (REFERENCE / 'final-changes.patch').read_text(),
      {'baseline_copies_match': baseline_ok, 'patch_matches': reconstructed == (REFERENCE / 'final-changes.patch').read_text()})

local_links = []
remote_links = []
missing = []
anchor_count = 0
for p in TARGETS:
    for match in re.finditer(r'\[[^\]]*\]\(([^)]+)\)', strip_fences((ROOT / p).read_text())):
        target = match.group(1).strip('<>')
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc:
            remote_links.append({'source': p, 'target': target})
            continue
        file = (ROOT / p).parent / unquote(parsed.path) if parsed.path else ROOT / p
        row = {'source': p, 'target': target, 'exists': file.exists()}
        if parsed.fragment and file.suffix == '.md' and file.exists():
            anchor_count += 1
            row['anchor_exists'] = unquote(parsed.fragment) in anchors(file)
        local_links.append(row)
        if not row['exists'] or row.get('anchor_exists') is False:
            missing.append(row)
check('local_markdown_links_and_anchors', not missing,
      {'local_links_checked': len(local_links), 'markdown_anchors_checked': anchor_count, 'missing': missing, 'remote_urls_not_requested': len(remote_links)})

whitespace = []
for p in TARGETS:
    for n, line in enumerate((ROOT / p).read_text().splitlines(), 1):
        if line.rstrip() != line:
            whitespace.append({'file': p, 'line': n})
diff_check = subprocess.run(['git', 'diff', '--check'], cwd=ROOT, text=True, capture_output=True)
check('whitespace_including_untracked_documents', not whitespace and diff_check.returncode == 0,
      {'explicit_target_issues': whitespace, 'git_diff_check_exit': diff_check.returncode, 'git_diff_check_output': diff_check.stdout + diff_check.stderr})

readme = (ROOT / 'README.md').read_text()
workflow = (ROOT / 'docs/WORKFLOW.md').read_text()
agents = (ROOT / 'AGENTS.md').read_text()
sessions = evidence['sessions']
expected_sessions = {
    '01a1206c-ebde-73b1-8515-c416e54fb20b': '설계',
    '01a12448-6bbd-7003-8671-4eccccb5c977': '개발노예',
    '01a12449-3ac5-7590-81d2-d9ca72bd581d': '테스트노예',
}
session_ok = len(sessions) == 3 and all(s['id'] in expected_sessions and s['title'] == expected_sessions[s['id']] and s['cwd'] == str(ROOT) and s['hostId'] == 'local' and s['id'] in workflow for s in sessions)
check('session_ids_names_and_root', session_ok and str(ROOT) in workflow, sessions)

package = load_json(ROOT / 'prototype/package.json')
script_names = ['start', 'review', 'review:states', 'review:news', 'review:gallery', 'build:scenarios']
command_definitions = {}
for name in script_names:
    definition = package['scripts'].get(name, '')
    refs = re.findall(r'node\s+(scripts/[^\s;&]+)', definition)
    command_definitions[name] = {'definition': definition, 'entry_files_exist': all((ROOT / 'prototype' / ref).is_file() for ref in refs)}
old_blocks = re.findall(r'```bash\n(.*?)```', (REFERENCE / 'README.md').read_text(), re.S)
new_blocks = re.findall(r'```bash\n(.*?)```', readme, re.S)
command_ok = old_blocks == new_blocks and all(row['definition'] and row['entry_files_exist'] for row in command_definitions.values()) and (ROOT / 'backend/manage.py').is_file() and (ROOT / 'backend/scripts/serve-prototype.py').is_file() and (ROOT / 'prototype/package-lock.json').is_file() and '@playwright/test' in package['devDependencies']
check('readme_command_definitions_static_only', command_ok,
      {'bash_blocks_preserved': old_blocks == new_blocks, 'npm_scripts': command_definitions, 'runtime_commands_executed': []})

policy_phrases = ['본점은 1곳', '공개 상태일 때 항상 첫 번째', '기본 선택', '본점 비공개 시 첫 유효 공개 지점', '미완성 초안 저장을 허용', '지점명·주소·운영시간', '사진·트레이너·연락처는 선택', '해당 영역·버튼을 숨긴다', '마지막 공개 지점도 철회', '지점 준비 중 안내', '문의 버튼을 숨긴다', '다음 구현 지시에서 기존 PRD·구현계획에 반영할 예정', '지점·시설 기능은 아직 구현하지 않았다']
check('latest_policy_recorded_and_followup_distinguished', all(s in readme for s in policy_phrases),
      {'missing_phrases': [s for s in policy_phrases if s not in readme], 'requirement_source': evidence['source_thread'], 'PRD_and_plan_unchanged': all(current[p] == before['files'][p] for p in ['docs/PRD.md', 'docs/IMPLEMENTATION-PLAN.md'])})

result = {
    'audit': 'WORKFLOW-01 independent local document verification',
    'root': str(ROOT),
    'scope': TARGETS,
    'status': 'PASS_WITH_WARNINGS' if all(c['status'] == 'PASS' for c in checks) else 'FAIL',
    'checks': checks,
    'current_repository_hashes_excluding_new_audit_files': current,
    'preservation_limits': [
        'Developer snapshots contain Git-tracked and non-ignored untracked files only.',
        'No historical database logical snapshot, .env.local, .local-credentials, or .private-media hashes are present. Their preservation across developer work is unverified.',
        'Historical snapshots are developer-supplied; current hashes and the patch were independently recomputed.',
    ],
    'runtime_tests_executed': [],
    'database_queries_executed': [],
}
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if all(c['status'] == 'PASS' for c in checks) else 1)
