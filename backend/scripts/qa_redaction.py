"""Redact known run/config secrets plus credential-shaped diagnostics."""

import json
import os
import re
from pathlib import Path

from dotenv import dotenv_values


def secrets_for(run, project, include_project=True):
    values = []
    for key, value in os.environ.items():
        if re.search(r"PASSWORD|SECRET|TOKEN|COOKIE|AUTH|API_KEY", key, re.I):
            values.append(value)
    donor = (
        dotenv_values(Path(project) / "backend/.env.local") if include_project else {}
    )
    values.extend(
        v
        for k, v in donor.items()
        if v and re.search(r"PASSWORD|SECRET|TOKEN|KEY", k, re.I)
    )
    for name in ["secret-key", "owner.json"]:
        path = Path(run) / name
        if path.is_file() and not path.is_symlink():
            if name == "owner.json":
                values.append(json.loads(path.read_text())["token"])
            else:
                values.append(path.read_text())
    for path in Path(run).rglob(".local-credentials"):
        if (
            not path.is_symlink()
            and path.is_file()
            and path.stat().st_size < 1024 * 1024
        ):
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                values.extend(v for v in data.values() if isinstance(v, str))
    return sorted({v for v in values if v}, key=len, reverse=True)


def redact(text, known):
    for value in known:
        text = text.replace(value, "[REDACTED]")
    text = re.sub(
        r"(?im)^(\s*(?:set-cookie|cookie|authorization)\s*:).*$", r"\1 [REDACTED]", text
    )
    text = re.sub(
        r"(?i)((?:password|secret|token|sessionid|csrftoken|api[_-]?key)[\w-]*[\"\']?\s*[:=]\s*)[^\n,;}]+",
        r"\1[REDACTED]",
        text,
    )
    text = re.sub(
        r"(?<![\w])(?:[A-Za-z0-9_=-]{28,})(?![\w])", "[OPAQUE REDACTED]", text
    )
    return text
