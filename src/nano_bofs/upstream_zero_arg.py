from __future__ import annotations

import argparse
from pathlib import Path

from nano_bofs.pathing import shared_root


COMMON_INCLUDE_DIR = shared_root() / "common"


def add_no_arguments(parser: argparse.ArgumentParser) -> None:
    return None


def zero_arg_build_plan(
    name: str,
    source_path: Path,
    *,
    include_dirs: list[Path] | None = None,
    cflags: list[str] | None = None,
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "template_path": source_path,
        "source_name": f"{name}.c",
        "artifact_basename": name,
        "placeholders": {},
        "metadata": metadata or {},
        "build": {
            "include_dirs": [str(item) for item in (include_dirs or [COMMON_INCLUDE_DIR])],
            "cflags": cflags or ["-Os", "-c", "-DBOF"],
        },
    }


def render_upstream_plan(plan: dict[str, object]) -> str:
    return Path(plan["template_path"]).read_text(encoding="utf-8")


def parse_no_args(description: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    add_no_arguments(parser)
    return parser.parse_args()
