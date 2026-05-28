from __future__ import annotations

import argparse
from pathlib import Path


NAME = "listmods"
DESCRIPTION = "List the modules loaded by the current or specified process."
VARIABLES = [
    {
        "name": "pid",
        "required": False,
        "description": "Optional process ID. Leave empty to inspect the current process.",
    }
]
DEFAULT_TEMPLATE = Path(__file__).with_name("entry.c")
COMMON_INCLUDE_DIR = (
    Path(__file__).resolve().parents[2]
    / "shared" / "common"
)


def normalize_pid(value: str) -> int:
    raw = value.strip()
    if raw == "":
        return 0
    if any(ch.isspace() for ch in raw):
        raise ValueError("pid must not contain spaces. Pass a decimal process ID or leave it empty.")
    try:
        pid = int(raw, 10)
    except ValueError as exc:
        raise ValueError("pid must be a decimal integer.") from exc
    if pid < 0:
        raise ValueError("pid must be zero or greater.")
    if pid > 0xFFFFFFFF:
        raise ValueError("pid must fit in a 32-bit unsigned integer.")
    return pid


def render_source(template: str, placeholders: dict[str, str]) -> str:
    rendered = template
    for key, value in placeholders.items():
        if key not in rendered:
            raise ValueError(f"template is missing the required placeholder {key}.")
        rendered = rendered.replace(key, value)
    return rendered


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "pid",
        nargs="?",
        default="",
        help="Optional process ID. Leave empty to inspect the current process.",
    )


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    pid = normalize_pid(args.pid)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_PID__": str(pid),
        },
        "metadata": {
            "final_pid": pid,
            "targets_current_process": pid == 0,
        },
        "build": {
            "include_dirs": [str(COMMON_INCLUDE_DIR)],
            "cflags": ["-Os", "-c", "-DBOF"],
        },
    }


def render_plan(plan: dict[str, object]) -> str:
    template = Path(plan["template_path"]).read_text(encoding="utf-8")
    return render_source(template, dict(plan["placeholders"]))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    add_arguments(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        plan = build_plan(args)
        print(render_plan(plan))
        print(f"final_pid={plan['metadata']['final_pid']}")
        print(f"targets_current_process={plan['metadata']['targets_current_process']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
