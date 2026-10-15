"""Record actual Django collection/results in a private directory at execution."""

import json
import os
from pathlib import Path
from unittest import TextTestResult

from django.test.runner import DiscoverRunner


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
    def get_resultclass(self):
        return Result

    def run_suite(self, suite, **kwargs):
        collected = suite.countTestCases()
        result = super().run_suite(suite, **kwargs)
        value = {
            "collected": collected,
            "run": result.testsRun,
            "pass": len(result.passed),
            "fail": [t.id() for t, _ in result.failures],
            "error": [t.id() for t, _ in result.errors],
            "skip": [{"id": t.id(), "reason": reason} for t, reason in result.skipped],
            "expected_failure": [t.id() for t, _ in result.expectedFailures],
            "unexpected_success": [t.id() for t in result.unexpectedSuccesses],
            "executed_ids": result.ids,
        }
        with (Path(os.environ["Y3GYM_INTEGRATION_WORK"]) / "suite-result.json").open(
            "x"
        ) as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
        return result
