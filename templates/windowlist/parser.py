from __future__ import annotations

import argparse
from pathlib import Path


NAME = "windowlist"
DESCRIPTION = "List visible windows in the current user session, or all windows if requested."
VARIABLES = [
    {
        "name": "scope",
        "required": False,
        "description": 'Optional literal "all" to include hidden windows.',
    }
]
DEFAULT_TEMPLATE = Path(__file__).with_name("entry.c")
COMMON_INCLUDE_DIR = (
    Path(__file__).resolve().parents[2]
    / "shared" / "common"
)


def normalize_scope(value: str) -> tuple[str, int]:
    raw = value.strip().lower()
    if raw == "":
        return ("visible", 0)
    if raw == "all":
        return ("all", 1)
    raise ValueError('scope must be empty or the literal "all".')


def render_source(template: str, placeholders: dict[str, str]) -> str:
    rendered = template
    for key, value in placeholders.items():
        if key not in rendered:
            raise ValueError(f"template is missing the required placeholder {key}.")
        rendered = rendered.replace(key, value)
    return rendered


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "scope",
        nargs="?",
        default="",
        help='Optional literal "all" to include hidden windows.',
    )


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    scope_label, include_all = normalize_scope(args.scope)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_ALL__": str(include_all),
        },
        "metadata": {
            "scope": scope_label,
            "include_hidden_windows": include_all == 1,
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
        print(f"scope={plan['metadata']['scope']}")
        print(f"include_hidden_windows={plan['metadata']['include_hidden_windows']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
