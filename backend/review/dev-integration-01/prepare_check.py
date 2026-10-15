"""Only syntax, source adaptation, and output routing; no product regression."""

import ast
import json
import subprocess

from prepare import BACKEND, HERE, ROOT, SCRIPTS, prepare, sha


def main():
    work = prepare()
    proofs = json.loads((work / "adaptations.json").read_text())
    coverage = []
    for path in sorted((BACKEND / "news/tests").glob("test_*.py")):
        tree = ast.parse(path.read_text())
        coverage.append(
            {
                "module": path.name,
                "defined_methods": [
                    f"{node.name}.{method.name}"
                    for node in tree.body
                    if isinstance(node, ast.ClassDef)
                    for method in node.body
                    if isinstance(method, ast.FunctionDef)
                    and method.name.startswith("test_")
                ],
            }
        )
    for proof in proofs:
        assert sha((BACKEND / proof["source"]).read_text()) == proof["source_sha256"]
    for path in [
        *HERE.glob("*.py"),
        work / "sandbox.py",
        work / "snapshot_functions.py",
    ]:
        ast.parse(path.read_text(), filename=str(path))
    scripts = [
        HERE / "guarded-playwright.mjs",
        *[work / "source/backend" / name for name in SCRIPTS],
    ]
    for path in scripts:
        subprocess.run(["node", "--check", str(path)], capture_output=True, check=True)
    for name in SCRIPTS:
        text = (work / "source/backend" / name).read_text()
        assert str(HERE / "guarded-playwright.mjs") in text
        if name in SCRIPTS[6:10]:
            assert "const origin = 'http://localhost:8768';" not in text
            assert "const origin = 'http://localhost:8772';" in text
        if name == "scripts/review-cms.mjs":
            assert str(work / "evidence/cms") in text
            assert str(work / ".local-credentials") in text
        if name == "scripts/review-popups.mjs":
            assert str(work / "evidence/popups") in text
            assert str(work / ".local-credentials") in text
        if "focus-independent/" in name:
            assert "test_y3gym_dev_integration_" in text
            assert "work,'evidence'" in text or "work, 'evidence'" in text
    assert not (work / "instance.json").exists()
    assert not (work / "execution-started").exists()
    assert not (work / ".local-credentials").exists()
    assert all((BACKEND / ".venv/bin" / name).exists() for name in ("python", "ruff"))
    public = {
        "status": "PREPARATION_CHECK_PASS_EXECUTION_PENDING",
        "private_prepared_work": str(work),
        "python_ast": "PASS",
        "javascript_syntax": len(scripts),
        "test_modules_static": coverage,
        "runtime_collected_pass_fail_skip": "NOT_RUN",
        "product_db_http_browser_executions": 0,
        "source_adaptation_proof": proofs,
        "root": str(ROOT),
    }
    with (HERE / "preparation.json").open("x") as stream:
        json.dump(public, stream, ensure_ascii=False, indent=2)
    print(
        json.dumps(
            {
                key: public[key]
                for key in (
                    "status",
                    "private_prepared_work",
                    "python_ast",
                    "javascript_syntax",
                    "product_db_http_browser_executions",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
