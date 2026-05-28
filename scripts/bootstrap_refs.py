#!/usr/bin/env python3
"""Clone or refresh top-level reference repos from refs/manifest.json."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "refs" / "manifest.json"


def run_git(*args: str, cwd: Path | None = None) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True)


def load_manifest() -> dict[str, object]:
    with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_repo(entry: dict[str, str]) -> None:
    repo_path = REPO_ROOT / entry["path"]
    remote_url = entry["remote_url"]
    commit = entry["commit"]

    if not repo_path.exists():
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        run_git("clone", remote_url, str(repo_path))
    elif not (repo_path / ".git").exists():
        raise RuntimeError(f"{repo_path} exists but is not a Git repository")

    run_git("fetch", "origin", cwd=repo_path)
    run_git("-c", "advice.detachedHead=false", "checkout", commit, cwd=repo_path)


def main() -> int:
    manifest = load_manifest()
    repositories = manifest.get("repositories", [])
    if not isinstance(repositories, list):
        raise RuntimeError("refs/manifest.json must contain a 'repositories' list")

    for raw_entry in repositories:
        if not isinstance(raw_entry, dict):
            raise RuntimeError("Each manifest entry must be an object")
        for field in ("name", "path", "remote_url", "commit"):
            if field not in raw_entry or not isinstance(raw_entry[field], str) or not raw_entry[field]:
                raise RuntimeError(f"Manifest entry is missing required field '{field}'")
        print(f"==> {raw_entry['name']}: {raw_entry['remote_url']} @ {raw_entry['commit']}")
        ensure_repo(raw_entry)

    print("refs bootstrap complete")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"git command failed with exit code {exc.returncode}", file=sys.stderr)
        raise
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
