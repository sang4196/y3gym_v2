"""Prepare private copies only. No Django import, DB, HTTP, or browser execution."""

import ast
import difflib
import hashlib
import json
import os
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BACKEND = ROOT / "backend"
FLAGS = ("BRAND", "BRANCH", "TRAINER", "HOME_NEWS")
SCRIPTS = (
    "scripts/review-brand-home.mjs",
    "scripts/review-branches.mjs",
    "scripts/review-trainers.mjs",
    "scripts/review-home-news.mjs",
    "review/home-news/popup-revisit.mjs",
    "review/home-news/popup-edges.mjs",
    "scripts/review-cms.mjs",
    "scripts/review-popups.mjs",
    "scripts/review-popup-sizing.mjs",
    "scripts/review-popup-position.mjs",
    "review/image-chooser-focus-independent/reproduce.mjs",
    "review/image-chooser-focus-independent/edges.mjs",
    "review/image-chooser-focus-independent/supplement.mjs",
    "review/image-chooser-focus-independent/body-close.mjs",
)


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def replace(source, old, new, count=1):
    assert source.count(old) == count, f"Source changed: {old[:70]}"
    return source.replace(old, new)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(value)


def prepare():
    os.umask(0o077)
    work = Path(tempfile.mkdtemp(prefix="y3gym-dev-integration-"))
    mirror = work / "source"
    (mirror / "backend").mkdir(parents=True)
    (mirror / "prototype").symlink_to(ROOT / "prototype", target_is_directory=True)
    (work / "evidence").mkdir()
    proof = []
    for name in SCRIPTS:
        source = (BACKEND / name).read_text()
        adapted = source
        # Import adaptation installs a transport guard; all test bodies stay intact.
        import_path = (
            "../../../prototype/" if name.startswith("review/") else "../../prototype/"
        )
        adapted = replace(
            adapted,
            import_path + "node_modules/@playwright/test/index.mjs",
            str(HERE / "guarded-playwright.mjs"),
        )
        if "focus-independent/" in name:
            adapted = replace(
                adapted,
                "/tmp/y3gym-image-focus-independent-",
                "/tmp/y3gym-dev-integration-",
            )
            adapted = replace(adapted, "http://localhost:8770", "http://localhost:8772")
            adapted = replace(
                adapted, "test_y3gym_focus_ind_", "test_y3gym_dev_integration_"
            )
            # Output expression only; label validation, timing, and assertions stay intact.
            if "path.join(here, label)" in adapted:
                adapted = replace(
                    adapted,
                    "path.join(here, label)",
                    "path.join(work, 'evidence', label)",
                )
            elif "path.join(here,process.argv[3])" in adapted:
                adapted = replace(
                    adapted,
                    "path.join(here,process.argv[3])",
                    "path.join(work,'evidence',process.argv[3])",
                )
            else:
                adapted = replace(
                    adapted,
                    "path.join(path.dirname(new URL(import.meta.url).pathname),label)",
                    "path.join(work,'evidence',label)",
                )
        elif name in SCRIPTS[6:10]:
            adapted = replace(
                adapted,
                "const origin = 'http://localhost:8768';",
                "const origin = 'http://localhost:8772';",
            )
            if name.endswith("review-cms.mjs"):
                adapted = replace(
                    adapted,
                    "const output = path.join(root, 'review');",
                    f"const output = {str(work / 'evidence/cms')!r};",
                )
            elif name.endswith("review-popups.mjs"):
                adapted = replace(
                    adapted,
                    "const output = path.join(root, 'review/popups');",
                    f"const output = {str(work / 'evidence/popups')!r};",
                )
                adapted = replace(
                    adapted,
                    "new URL(desktop.page.url()).port, '8768'",
                    "new URL(desktop.page.url()).port, '8772'",
                )
            if "fs.readFile(path.join(root, '.local-credentials')" in adapted:
                adapted = replace(
                    adapted,
                    "fs.readFile(path.join(root, '.local-credentials')",
                    f"fs.readFile({str(work / '.local-credentials')!r}",
                )
        if name in {"scripts/review-popups.mjs", "scripts/review-popup-sizing.mjs"}:
            adapted = replace(
                adapted,
                "'http://localhost:8767/?branch=second'",
                "`${origin}/?branch=second`",
            )
            adapted = (
                f"import {{ installPopupObservation, observePopupBatch, observePopupOne, ordinaryCloseAndRevisit }} from {str(HERE / 'popup-observation.mjs')!r};\n"
                + adapted
            )
            if name.endswith("review-popups.mjs"):
                adapted = replace(
                    adapted,
                    "  const page = await context.newPage();\n  page.setDefaultTimeout(15000);",
                    "  await installPopupObservation(context);\n  const page = await context.newPage();\n  page.setDefaultTimeout(15000);",
                )
                adapted = replace(
                    adapted,
                    "  await desktop.page.waitForFunction(ids => ids.every(id =>\n    sessionStorage.getItem(`y3gym.prototype.shown:${id}`) === '1'), payload.map(popup => popup.id));",
                    "  await observePopupBatch(desktop.page, payload);",
                )
                adapted = replace(
                    adapted,
                    "  await desktop.page.reload();\n  await new Promise(resolve => setTimeout(resolve, 700));",
                    "  await desktop.page.reload();\n  await observePopupBatch(desktop.page, payload);\n  await new Promise(resolve => setTimeout(resolve, 700));",
                )
                adapted = replace(
                    adapted,
                    "  await desktop.context.close();",
                    "  await ordinaryCloseAndRevisit(desktop.page, payload);\n  check('일반 닫기 후 소식 이동·홈 재방문 시 같은 적격 ID/개수/연결 글 재노출', payload.map(item => item.id));\n  await desktop.context.close();",
                )
                adapted = replace(
                    adapted,
                    "실제 홈 리디렉션·전체 PC 자동 노출 순서",
                    "격리 실제 공개 홈·전체 PC 자동 노출 순서",
                )
            else:
                adapted = replace(
                    adapted,
                    "  watch(context);\n  await context.addInitScript",
                    "  watch(context);\n  await installPopupObservation(context);\n  await context.addInitScript",
                )
                adapted = replace(
                    adapted,
                    "  await home.waitForFunction(ids => ids.every(id =>\n    sessionStorage.getItem(`y3gym.prototype.shown:${id}`) === '1'), payload.map(item => item.id));",
                    "  await observePopupBatch(home, payload);",
                )
                adapted = replace(
                    adapted,
                    "    await home.reload();\n    await home.waitForTimeout(400);",
                    "    await home.reload();\n    await observePopupBatch(home, JSON.parse(await home.locator('#home-popup-data').textContent()));\n    await home.waitForTimeout(400);",
                )
                adapted = replace(
                    adapted,
                    "  watch(blocked);\n  const recovery",
                    "  watch(blocked);\n  await installPopupObservation(blocked);\n  const recovery",
                )
                adapted = replace(
                    adapted,
                    "  await recovery.waitForFunction(id => sessionStorage.getItem(`y3gym.prototype.shown:${id}`) === '1', manualId);",
                    "  await observePopupOne(recovery, manual);\n  assert.equal(JSON.parse(await manual.locator('#popup-data').textContent()).id, manualId);",
                )
        target = mirror / "backend" / name
        write(target, adapted)
        diff = "".join(
            difflib.unified_diff(
                source.splitlines(True),
                adapted.splitlines(True),
                fromfile=name,
                tofile="private/" + name,
            )
        )
        proof.append(
            {
                "source": name,
                "source_sha256": sha(source),
                "adapted_sha256": sha(adapted),
                "diff": diff,
            }
        )

    # Reuse the existing sandbox guards. Only instance identities/account name change.
    sandbox_name = "review/image-chooser-focus-independent/sandbox.py"
    sandbox = (BACKEND / sandbox_name).read_text()
    adapted = sandbox.replace(
        "/tmp/y3gym-image-focus-independent-", "/tmp/y3gym-dev-integration-"
    )
    adapted = replace(
        adapted,
        '"y3gym-image-focus-independent-"',
        '"y3gym-dev-integration-"',
    )
    adapted = adapted.replace("test_y3gym_focus_ind_", "test_y3gym_dev_integration_")
    adapted = adapted.replace("image_focus_ind", "dev_integration").replace(
        "8770", "8772"
    )
    adapted = replace(
        adapted,
        "ROOT = Path(__file__).resolve().parents[3]",
        f"ROOT = Path({str(ROOT)!r})",
    )
    adapted = replace(
        adapted,
        'username = "focus-review-" + spec["database"][-6:]',
        'username = "cms-review-editor"',
    )
    adapted = replace(
        adapted,
        "    bootstrap_browser_review()\n    from django.contrib.auth",
        '    bootstrap_browser_review()\n    call_command("bootstrap_trainer_review", verbosity=0)\n    from django.contrib.auth',
    )
    write(work / "sandbox.py", adapted)
    proof.append(
        {
            "source": sandbox_name,
            "source_sha256": sha(sandbox),
            "adapted_sha256": sha(adapted),
            "diff": "".join(
                difflib.unified_diff(
                    sandbox.splitlines(True),
                    adapted.splitlines(True),
                    fromfile=sandbox_name,
                    tofile="private/sandbox.py",
                )
            ),
        }
    )

    # Copy only the read-only functions, never import/execute the old apply entrypoint.
    old_probe = (BACKEND / "review/image-chooser-focus-apply/probe.py").read_text()
    names = {
        "digest",
        "save",
        "stat",
        "metadata",
        "guard",
        "media_inventory",
        "snapshot",
        "summary",
    }
    functions = [
        ast.get_source_segment(old_probe, node)
        for node in ast.parse(old_probe).body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    assert len(functions) == len(names)
    write(work / "snapshot_functions.py", "\n\n".join(functions) + "\n")
    proof.append(
        {
            "source": "review/image-chooser-focus-apply/probe.py",
            "source_sha256": sha(old_probe),
            "copied_read_only_functions": sorted(names),
        }
    )
    write(
        work / "adaptations.json",
        json.dumps(proof, ensure_ascii=False, indent=2) + "\n",
    )
    write(
        work / "plan.json",
        json.dumps(
            {
                "work": str(work),
                "mirror": str(mirror),
                "scripts": SCRIPTS,
                "flags": FLAGS,
                "stage": "PREPARED_NOT_EXECUTED",
            },
            indent=2,
        )
        + "\n",
    )
    return work


if __name__ == "__main__":
    print(prepare())
