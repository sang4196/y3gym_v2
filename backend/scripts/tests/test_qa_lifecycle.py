"""Destructive checks use only freshly marked .local/qa disposable runs."""

import ctypes
import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from psycopg import sql

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend/scripts"))
import qa_lifecycle as q  # noqa: E402 - canonical helper path is deliberately selected above

BASELINE = os.environ["Y3GYM_LIFECYCLE_TEST_RUN"]


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.runs = []
        self.children = []

    def make(self):
        run_id = q.create("manual", "disposable QA-LIFECYCLE-01 fixture")
        self.runs.append(run_id)
        return q.load(run_id)

    def tearDown(self):
        for child in self.children:
            if child.poll() is None:
                child.terminate()
            child.wait(timeout=10)
        for run_id in self.runs:
            run, value, token = q.load(run_id)
            if token:
                q.stop(run_id)
                q.complete(run_id, "fixture inspection complete and unused")
                plan = q.cleanup(run_id, True)
                self.assertTrue(plan.get("eligible"), plan)
                q.cleanup(run_id, False, plan["plan_id"])

    def worker(self, run, value, token):
        child = subprocess.Popen(
            [str(q.PYTHON), "-B", "-c", "import time; time.sleep(60)"],
            cwd=run / "source/backend",
            env=q.environment(run, value, token),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            umask=0o077,
        )
        self.children.append(child)
        return child

    def track_auto(self, *args, **kwargs):
        before = {p.stem for p in (q.RUNS / ".registry").glob("qa-*.json")}
        purpose = args[0] + " fixture-" + q.uuid.uuid4().hex[:8]
        try:
            return q.auto(purpose, *args[1:], **kwargs)
        finally:
            self.runs.extend(
                p.stem
                for p in (q.RUNS / ".registry").glob("qa-*.json")
                if p.stem not in before and q.private_read(p)["purpose"] == purpose
            )

    def test_manual_gate_plan_change_exact_cleanup_and_duplicate(self):
        run, value, token = self.make()
        self.assertFalse(q.cleanup(value["id"], True)["eligible"])
        copied = json.loads((run / "source-manifest.json").read_text())
        self.assertEqual(
            copied["backend/news/content_images.py"],
            q.file_sha(ROOT / "backend/news/content_images.py"),
        )
        for p in [
            run / "source/.git",
            run / "source/.local",
            run / "source/backend/.env.local",
            run / "source/backend/.private-media",
            run / "source/prototype/node_modules",
        ]:
            self.assertFalse(p.exists())
        q.complete(value["id"], "review completed")
        plan = q.cleanup(value["id"], True)
        (run / "output/new.txt").write_text("changes plan")
        with self.assertRaises(q.Refused):
            q.cleanup(value["id"], False, plan["plan_id"])
        self.assertTrue(run.exists())
        plan = q.cleanup(value["id"], True)
        done = q.cleanup(value["id"], False, plan["plan_id"])
        self.assertEqual(done["plan_id"], plan["plan_id"])
        self.assertFalse(run.exists())
        self.assertTrue(q.cleanup(value["id"])["already_cleaned"])
        frozen = q.dt.datetime.strptime(
            value["id"].split("-")[1], "%Y%m%dT%H%M%SZ"
        ).replace(tzinfo=q.dt.timezone.utc)
        with (
            patch.object(q.dt, "datetime", wraps=q.dt.datetime) as clock,
            patch.object(q.uuid, "uuid4") as nonce,
        ):
            clock.now.return_value = frozen
            nonce.return_value.hex = value["id"][-12:] + "0" * 20
            with self.assertRaises(q.Refused):
                q.create("manual", "duplicate-id fixture")
        self.assertFalse(run.exists())

    def test_external_root_nested_symlink_and_other_run_protection(self):
        a, av, at = self.make()
        b, bv, bt = self.make()
        sentinel = b / "output/original.txt"
        sentinel.write_text("other run retained")
        for invalid in ["..", str(ROOT), str(q.RUNS), str(b / "../..")]:
            with self.assertRaises(q.Refused):
                q.cleanup(invalid, True)
        q.complete(av["id"], "fixture done")
        link = a / "output/escape"
        link.symlink_to(b, target_is_directory=True)
        self.assertFalse(q.cleanup(av["id"], True)["eligible"])
        self.assertEqual(sentinel.read_text(), "other run retained")
        link.unlink()
        held = a.with_name(a.name + ".held")
        a.rename(held)
        a.symlink_to(b, target_is_directory=True)
        try:
            self.assertEqual(
                q.status(av["id"])["runs"][0]["state"], "UNKNOWN_PROTECTED"
            )
            with self.assertRaises(q.Refused):
                q.cleanup(av["id"])
            self.assertTrue(sentinel.exists())
        finally:
            a.unlink()
            held.rename(a)

    def test_create_before_comment_registration_gap_fails_closed(self):
        run, value, token = self.make()
        name = value["database_names"][0]
        with q.db_connect() as c, c.cursor() as cur:
            self.assertIsNone(q.db_state(cur, name))
            cur.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(
                    sql.Identifier(name)
                )
            )
            oid = q.db_state(cur, name)[0]
        try:
            self.assertEqual(value["databases"], {})
            q.complete(value["id"], "interrupted CREATE fixture")
            self.assertFalse(q.cleanup(value["id"], True)["eligible"])
            with self.assertRaises(q.Refused):
                q.cleanup(value["id"], False, "not-a-plan")
            self.assertTrue(run.exists())
            with q.db_connect() as c, c.cursor() as cur:
                self.assertEqual(q.db_state(cur, name)[0], oid)
        finally:
            # Test-only removal of the exact newly-created disposable DB whose OID this harness captured.
            with q.db_connect() as c, c.cursor() as cur:
                self.assertEqual(q.db_state(cur, name)[0], oid)
                cur.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))

    def test_wrong_database_oid_and_other_run_name_refused(self):
        a, av, at = self.make()
        b, bv, bt = self.make()
        q.provision(a, av, at)
        saved = dict(av["databases"])
        av["databases"][av["database_names"][0]] += 1
        q.save(a, av)
        q.complete(av["id"], "fixture done")
        self.assertFalse(q.cleanup(av["id"], True)["eligible"])
        av = q.load(av["id"])[1]
        av["databases"] = saved
        q.save(a, av)
        original = list(av["database_names"])
        av["database_names"] = list(bv["database_names"])
        q.save(a, av)
        with self.assertRaises(q.Refused):
            q.cleanup(av["id"], True)
        av["database_names"] = original
        q.save(a, av)
        self.assertTrue(b.exists())

    def test_wrong_process_token_and_reused_pid_starttime_refused(self):
        a, av, at = self.make()
        b, bv, bt = self.make()
        child = self.worker(b, bv, bt)
        av["processes"] = [q.identity(q.proc_info(child.pid, strict=True))]
        q.save(a, av)
        with self.assertRaises(q.Refused):
            q.stop(av["id"])
        self.assertIsNone(child.poll())
        av["processes"] = []
        q.save(a, av)
        info = q.identity(q.proc_info(child.pid, strict=True))
        bad = {**info, "start_ticks": info["start_ticks"] + 1}
        bv["processes"] = [bad]
        q.save(b, bv)
        with self.assertRaises(q.Refused):
            q.stop(bv["id"])
        self.assertIsNone(child.poll())
        bv["processes"] = [info]
        q.save(b, bv)
        q.stop(bv["id"])
        child.wait(timeout=10)

    def test_live_recorded_pid_lookup_error_is_unknown_not_dead(self):
        run, value, token = self.make()
        child = self.worker(run, value, token)
        value["processes"] = [q.identity(q.proc_info(child.pid, strict=True))]
        q.save(run, value)
        original = Path.read_bytes

        def deny(path):
            if path == Path("/proc") / str(child.pid) / "environ":
                raise PermissionError("fixture read denied")
            return original(path)

        with patch.object(Path, "read_bytes", deny):
            self.assertEqual(
                q.status(value["id"])["runs"][0]["state"], "UNKNOWN_PROTECTED"
            )
            with self.assertRaises(q.Refused):
                q.stop(value["id"])
            with self.assertRaises(q.Refused):
                q.complete(value["id"], "must not classify as exited")
        self.assertIsNone(child.poll())
        record = q.identity(q.proc_info(child.pid, strict=True))
        payload = json.dumps(
            {"event": "spawn", "record": record}, separators=(",", ":")
        )
        signature = q.hmac.new(
            token.encode(), payload.encode(), q.hashlib.sha256
        ).hexdigest()
        birth = run / "output/browser-processes.jsonl"
        birth.write_text(
            json.dumps({"payload_json": payload, "signature": "0" * 64}) + "\n"
        )
        with self.assertRaises(q.Refused):
            q.stop(value["id"])
        self.assertIsNone(child.poll())
        birth.write_text(
            json.dumps({"payload_json": payload, "signature": signature}) + "\n"
        )
        q.stop(value["id"])
        child.wait(timeout=10)

    def test_partial_db_drop_folder_failure_report_and_recovery(self):
        run, value, token = self.make()
        q.provision(run, value, token)
        q.complete(value["id"], "fixture done")
        plan = q.cleanup(value["id"], True)
        with patch.object(
            q.shutil, "rmtree", side_effect=OSError("fixture deletion failure")
        ):
            with self.assertRaises(OSError):
                q.cleanup(value["id"], False, plan["plan_id"])
        current = q.load(value["id"])[1]
        self.assertEqual(current["state"], "CLEANUP_BLOCKED")
        self.assertTrue(run.exists())
        self.assertTrue(
            all(not v.get("exists") for v in current["remaining_databases"])
        )
        evidence = ROOT / "backend/review/qa-lifecycle/runs" / value["id"]
        self.assertTrue(list(evidence.glob("cleanup-failed-*.json")))

    def test_auto_success_failure_diagnostics_redaction_exception(self):
        success, code = self.track_auto(
            "disposable auto success",
            command=[str(q.PYTHON), "-B", "-c", 'print("NORMAL lifecycle fixture")'],
        )
        self.assertEqual(code, 0)
        self.assertEqual(success["cleanup"]["state"], "DELETED")
        run, _, _ = q.load(BASELINE)
        secret = json.loads((run / ".local-credentials").read_text())[
            "redaction-fixture"
        ]
        program = 'import os,sys,traceback\ntry: raise RuntimeError(os.environ["Y3GYM_TEST_SECRET"])\nexcept: traceback.print_exc()\nprint("Authorization: Bearer "+os.environ["Y3GYM_TEST_SECRET"])\nsys.exit(7)'
        with patch.dict(os.environ, {"Y3GYM_TEST_SECRET": secret}):
            failure, code = self.track_auto(
                "disposable auto failure", command=[str(q.PYTHON), "-B", "-c", program]
            )
        self.assertEqual(code, 7)
        self.assertEqual(failure["cleanup"]["state"], "DELETED")
        text = "".join(p.read_text() for p in Path(failure["evidence"]).glob("*.json"))
        self.assertNotIn(secret, text)
        self.assertIn("RuntimeError", text)
        self.assertIn("Traceback", text)
        self.assertIn("[REDACTED]", text)
        for p in Path(failure["evidence"]).glob("*.json"):
            json.loads(p.read_text())
        error, code = self.track_auto(
            "disposable auto launch exception",
            command=["/nonexistent-managed-qa-fixture"],
        )
        self.assertEqual(code, 1)
        self.assertEqual(error["cleanup"]["state"], "DELETED")

    def test_auto_reproduction_retention_policy(self):
        program = 'import os,pathlib,sys; pathlib.Path(os.environ["Y3GYM_QA_RUN_DIR"],"output/reproduction.txt").write_text("retain me"); sys.exit(9)'
        result, code = self.track_auto(
            "retain disposable reproduction",
            command=[str(q.PYTHON), "-B", "-c", program],
            retain_reason="fixture requires environment reproduction",
            cleanup_condition="inspect fixture, complete, confirm unused, cleanup",
        )
        self.assertEqual(code, 9)
        run, value, token = q.load(result["run_id"])
        self.assertEqual(value["state"], "RETAINED")
        self.assertTrue((run / "output/reproduction.txt").exists())
        self.assertFalse(q.cleanup(value["id"], True)["eligible"])

    def test_cleanup_failure_is_separate_and_preserves_command_exit(self):
        real = q.cleanup

        def blocked(run_id, dry_run=False, expected_plan=None):
            if not dry_run:
                raise q.Refused("fixture cleanup failure")
            return real(run_id, dry_run, expected_plan)

        with patch.object(q, "cleanup", blocked):
            result, code = self.track_auto(
                "failed command and cleanup",
                command=[str(q.PYTHON), "-B", "-c", "import sys; sys.exit(7)"],
            )
        self.assertEqual(code, 7)
        self.assertIsNotNone(result["cleanup_error"])
        self.assertEqual(q.load(result["run_id"])[1]["state"], "CLEANUP_BLOCKED")
        self.assertTrue(Path(result["evidence"]).is_dir())
        with patch.object(q, "cleanup", blocked):
            success, code = self.track_auto(
                "successful command cleanup failure",
                command=[str(q.PYTHON), "-B", "-c", 'print("fixture")'],
            )
        self.assertEqual(success["command_exit_code"], 0)
        self.assertEqual(code, 3)
        self.assertIsNotNone(success["cleanup_error"])

    def test_forced_controller_interruption_discovers_and_stops_only_owned_orphan(self):
        ctypes.CDLL(None).prctl(
            36, 1, 0, 0, 0
        )  # Linux child subreaper for this fixture driver only.
        before = {p.stem for p in (q.RUNS / ".registry").glob("qa-*.json")}
        baseline = q.RUNS / BASELINE
        program = 'import os,pathlib,time; pathlib.Path(os.environ["Y3GYM_QA_RUN_DIR"],"output/started.pid").write_text(str(os.getpid())); time.sleep(60)'
        with (baseline / "logs/forced-controller.log").open("ab") as log:
            driver = subprocess.Popen(
                [
                    str(q.PYTHON),
                    "-B",
                    str(ROOT / "backend/scripts/qa_lifecycle.py"),
                    "auto",
                    "--purpose",
                    "disposable forced interruption",
                    "--command",
                    str(q.PYTHON),
                    "-B",
                    "-c",
                    program,
                ],
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            self.children.append(driver)
            deadline = time.monotonic() + 15
            run_id = None
            while time.monotonic() < deadline:
                new = {
                    p.stem for p in (q.RUNS / ".registry").glob("qa-*.json")
                } - before
                for candidate in new:
                    entry = q.private_read(q.registry_path(candidate))
                    if entry.get("driver") and entry["driver"]["pid"] == driver.pid:
                        run_id = candidate
                        if (q.RUNS / run_id / "output/started.pid").exists():
                            break
                if run_id and (q.RUNS / run_id / "output/started.pid").exists():
                    break
                time.sleep(0.05)
            self.assertIsNotNone(run_id)
            self.runs.append(run_id)
            worker = int((q.RUNS / run_id / "output/started.pid").read_text())
            driver.kill()
            driver.wait(timeout=10)
            run, value, token = q.load(run_id)
            actual = q.proc_info(worker, strict=True)
            q.private_json(
                baseline / "output" / f"forced-identity-{run_id}.json",
                {
                    "recorded": value["processes"],
                    "actual": q.identity(actual) if actual else None,
                    "token_match": bool(actual and actual["run_token"] == token),
                    "run_id_match": bool(actual and actual["run_id"] == run_id),
                },
            )
            observed = q.status(run_id)["runs"][0]
            self.assertTrue(observed["interrupted_driver"])
            self.assertTrue(observed["orphaned_owned_processes"])
            self.assertFalse(q.cleanup(run_id, True)["eligible"])
            q.stop(run_id)
            try:
                os.waitpid(worker, 0)
            except ChildProcessError:
                pass
            self.assertIsNone(q.proc_info(worker, strict=True))
            q.complete(run_id, "forced fixture resolved; owned child stopped")

    def test_evidence_destination_symlink_and_secret_modes(self):
        run, value, token = self.make()
        q.complete(value["id"], "fixture done")
        plan = q.cleanup(value["id"], True)
        for path in [run, run / "tmp", run / "output"]:
            self.assertEqual(path.stat().st_mode & 0o777, 0o700)
        for path in [
            run / "owner.json",
            run / "manifest.json",
            run / "qa_settings.py",
            run / "secret-key",
        ]:
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        other, _, _ = self.make()
        destination = ROOT / "backend/review/qa-lifecycle/runs" / value["id"]
        destination.symlink_to(other, target_is_directory=True)
        try:
            with self.assertRaises(q.Refused):
                q.cleanup(value["id"], False, plan["plan_id"])
            self.assertTrue(run.exists())
            self.assertTrue(other.exists())
        finally:
            destination.unlink()
