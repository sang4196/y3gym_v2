"""Hash public repository files; protected runtime and secret files use stat only."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[3]
own = 'backend/review/contact-visibility-independent/'
exclude = {'.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache', '.ruff_cache', '.private-media'}


def stat_files(base):
    records = {}
    for current, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if not (Path(current) / d).is_symlink())
        for name in sorted(files):
            p = Path(current) / name
            s = p.lstat()
            records[str(p.relative_to(base))] = {'bytes': s.st_size, 'mtime_ns': s.st_mtime_ns, 'mode': s.st_mode, 'inode': s.st_ino}
    return records


repository, sensitive_stat = {}, {}
for current, dirs, files in os.walk(root):
    dirs[:] = sorted(d for d in dirs if d not in exclude and not (Path(current) / d).is_symlink())
    for name in sorted(files):
        p = Path(current) / name
        if p.is_symlink():
            continue
        relative = str(p.relative_to(root))
        if len(sys.argv) > 1 and sys.argv[1] == 'baseline' and relative.startswith(own):
            continue
        if name.startswith('.env') or 'credentials' in name or name.endswith('.pem'):
            s = p.stat()
            sensitive_stat[relative] = {'bytes': s.st_size, 'mtime_ns': s.st_mtime_ns, 'mode': s.st_mode, 'inode': s.st_ino}
        else:
            data = p.read_bytes()
            repository[relative] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}

reference = json.loads((root / 'backend/review/contact-visibility/verification.json').read_text())
protected = [row['path'] for row in reference['static_and_preservation']['protected_metadata']]
protected += ['/tmp/y3gym-contact-visibility-jtpih5er']
index = root / subprocess.check_output(['git', 'rev-parse', '--git-path', 'index'], cwd=root, text=True).strip()
vendor = root / 'backend/.venv/lib/python3.13/site-packages/wagtail'
vendor_files = ['images/templates/wagtailimages/chooser/confirm_duplicate_upload.html',
                'admin/templates/wagtailadmin/generic/chooser/chooser.html',
                'admin/static/wagtailadmin/js/core.js', 'images/static/wagtailimages/js/image-chooser-modal.js']
print(json.dumps({
    'repository': repository, 'sensitive_stat': sensitive_stat,
    'protected_stat': {p: stat_files(Path(p)) for p in dict.fromkeys(protected)},
    'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
    'index_sha256': hashlib.sha256(index.read_bytes()).hexdigest(),
    'vendor': {p: hashlib.sha256((vendor / p).read_bytes()).hexdigest() for p in vendor_files},
}))
