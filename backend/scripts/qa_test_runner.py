"""Managed Django test results; private traces and sanitized public diagnostics."""

import json
import os
import re
import tempfile
from pathlib import Path
from unittest import TextTestResult

from django.conf import settings
from django.test.runner import DiscoverRunner
from qa_redaction import redact, secrets_for


class Result(TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ids = []
        self.passed = []

    def startTest(self, test):
        self.ids.append(test.id())
        super().startTest(test)

    def addSuccess(self, test):
        self.passed.append(test.id())
        super().addSuccess(test)


class Runner(DiscoverRunner):
    def __init__(self, *args, **kwargs):
        kwargs["keepdb"] = (
            True  # Both precreated DBs carry lifecycle ownership comments.
        )
        super().__init__(*args, **kwargs)

    def get_resultclass(self):
        return Result

    def run_suite(self, suite, **kwargs):
        run = Path(os.environ["Y3GYM_QA_RUN_DIR"])
        assert Path(tempfile.gettempdir()) == run / "tmp"
        assert settings.BASE_DIR == run and Path(settings.MEDIA_ROOT).is_relative_to(
            run
        )
        collected = suite.countTestCases()
        result = super().run_suite(suite, **kwargs)
        failures = []
        known = secrets_for(
            Path(os.environ["Y3GYM_QA_RUN_DIR"]),
            Path(os.environ["Y3GYM_QA_PROJECT_ROOT"]),
        )
        for test, trace in result.failures + result.errors:
            locations = re.findall(r'File "([^"]+\.py)", line (\d+)', trace)
            failures.append(
                {
                    "id": test.id(),
                    "locations": [
                        {"file": str(Path(p).name), "line": int(n)}
                        for p, n in locations
                    ],
                    "diagnostic": redact(trace, known),
                }
            )
        value = {
            "collected": collected,
            "run": result.testsRun,
            "pass": len(result.passed),
            "fail": [t.id() for t, _ in result.failures],
            "error": [t.id() for t, _ in result.errors],
            "skip": [t.id() for t, _ in result.skipped],
            "executed_ids": result.ids,
            "failure_locations": failures,
            "runtime_scope": {
                "BASE_DIR": str(settings.BASE_DIR),
                "MEDIA_ROOT": str(settings.MEDIA_ROOT),
                "TMPDIR": tempfile.gettempdir(),
            },
        }
        path = Path(os.environ["Y3GYM_QA_RUN_DIR"]) / "output/suite-result.json"
        with path.open("x") as stream:
            json.dump(value, stream, indent=2)
        return result
