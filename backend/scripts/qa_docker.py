"""Exact managed Docker resource ownership; no global pruning or adoption."""

import json
import subprocess

RUN_LABEL = "com.y3gym.qa.run"
OWNER_LABEL = "com.y3gym.qa.owner"


def project_name(value):
    return "y3gymqa-" + value["id"].rsplit("-", 1)[1]


def inspect_resources(value):
    projects = [project_name(value), project_name(value) + "-restore"]
    resources = []
    for kind, listing in [
        ("container", ["ps", "-aq"]),
        ("network", ["network", "ls", "-q"]),
        ("volume", ["volume", "ls", "-q"]),
    ]:
        ids = []
        for project in projects:
            ids += subprocess.check_output(
                [
                    "docker",
                    *listing,
                    "--filter",
                    "label=com.docker.compose.project=" + project,
                ],
                text=True,
            ).split()
        ids += subprocess.check_output(
            ["docker", *listing, "--filter", "label=" + RUN_LABEL + "=" + value["id"]],
            text=True,
        ).split()
        ids = sorted(set(ids))
        if not ids:
            continue
        objects = json.loads(subprocess.check_output(["docker", kind, "inspect", *ids]))
        for obj in objects:
            labels = (
                obj.get("Config", {}).get("Labels", {})
                if kind == "container"
                else obj.get("Labels", {})
            )
            if (
                labels.get(RUN_LABEL) != value["id"]
                or labels.get(OWNER_LABEL) != value["owner_hash"]
            ):
                raise ValueError(
                    "Docker resource owner labels mismatch; preserve resources"
                )
            if labels.get("com.docker.compose.project") not in projects:
                if not (
                    kind == "volume"
                    and obj["Name"] == projects[1] + "_database"
                    and labels.get("com.y3gym.qa.fixture") == "restore-collision"
                ):
                    raise ValueError(
                        "Unexpected resource namespace; preserve resources"
                    )
            resources.append(
                {
                    "kind": kind,
                    "id": obj.get("Id") or obj["Name"],
                    "name": obj.get("Name"),
                    "labels": labels,
                }
            )
    return sorted(resources, key=lambda r: (r["kind"], r["id"]))


def remove_resources(value, expected):
    if inspect_resources(value) != expected:
        raise ValueError("Docker resources changed after cleanup plan")
    for kind in ["container", "network", "volume"]:
        for resource in expected:
            if resource["kind"] != kind:
                continue
            command = ["docker", kind, "rm"]
            if kind == "container":
                subprocess.run(
                    ["docker", "stop", "--time", "30", resource["id"]],
                    check=True,
                    capture_output=True,
                )
            subprocess.run([*command, resource["id"]], check=True, capture_output=True)
    # Remove only this run's image tags. Shared pinned bases/build cache stay intact.
    for suffix in ["app", "app-next", "browser"]:
        tag = project_name(value) + ":" + suffix
        found = subprocess.run(["docker", "image", "inspect", tag], capture_output=True)
        if found.returncode:
            continue
        image = json.loads(found.stdout)[0]
        labels = image["Config"].get("Labels", {})
        if (
            labels.get(RUN_LABEL) != value["id"]
            or labels.get(OWNER_LABEL) != value["owner_hash"]
        ):
            raise ValueError("Docker image owner mismatch; preserve image")
        subprocess.run(["docker", "image", "rm", tag], check=True, capture_output=True)
    if inspect_resources(value):
        raise ValueError("Owned Docker resources remain")
