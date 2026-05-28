from __future__ import annotations

import argparse
from pathlib import Path


NAME = "netuserenum"
DESCRIPTION = "Enumerate local or domain user accounts with an optional filter."
VARIABLES = [
    {
        "name": "scope",
        "required": True,
        "description": "Enumeration scope: local or domain.",
        "shape": "Choose one fixed scope value.",
        "example": "domain",
        "validation": [
            "Must be exactly one of: local, domain.",
        ],
        "choices": ["local", "domain"],
        "modal_display_name": "Scope",
        "placeholder": "domain",
    },
    {
        "name": "filter",
        "required": False,
        "description": "Optional account filter: all, active, locked, or disabled.",
        "shape": "Optional fixed filter value.",
        "example": "all",
        "validation": [
            "When supplied, must be one of: all, active, locked, disabled.",
        ],
        "choices": ["all", "active", "locked", "disabled"],
        "modal_display_name": "Filter",
        "placeholder": "all",
        "mythic_default_value": "all",
    },
]
DEFAULT_TEMPLATE = Path(__file__).with_name("entry.c")
COMMON_INCLUDE_DIR = (
    Path(__file__).resolve().parents[2]
    / "shared" / "common"
)

SCOPES: dict[str, int] = {
    "local": 0,
    "domain": 1,
}
FILTERS: dict[str, int] = {
    "all": 1,
    "locked": 2,
    "disabled": 3,
    "active": 4,
}


def normalize_scope(value: str) -> tuple[str, int]:
    cleaned = value.strip().lower()
    if cleaned not in SCOPES:
        valid = ", ".join(SCOPES)
        raise ValueError(f"scope must be one of {valid}.")
    return cleaned, SCOPES[cleaned]


def normalize_filter(value: str | None) -> tuple[str, int]:
    if value is None:
        return "all", FILTERS["all"]

    cleaned = value.strip().lower()
    if not cleaned:
        return "all", FILTERS["all"]
    if cleaned not in FILTERS:
        valid = ", ".join(FILTERS)
        raise ValueError(f"filter must be one of {valid}.")
    return cleaned, FILTERS[cleaned]


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
        choices=tuple(SCOPES),
        help="Enumeration scope: local or domain.",
    )
    parser.add_argument(
        "filter",
        nargs="?",
        help="Optional filter: all, active, locked, or disabled.",
    )


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    scope_name, usedomain = normalize_scope(args.scope)
    filter_name, filter_value = normalize_filter(args.filter)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_USEDOMAIN__": str(usedomain),
            "__NANO_USERFILTER__": str(filter_value),
        },
        "metadata": {
            "final_scope": scope_name,
            "final_filter": filter_name,
            "final_filter_value": filter_value,
            "usedomain": usedomain,
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
        rendered = render_plan(plan)
        print(rendered)
        print(f"final_scope={plan['metadata']['final_scope']}")
        print(f"final_filter={plan['metadata']['final_filter']}")
        print(f"final_filter_value={plan['metadata']['final_filter_value']}")
        print(f"usedomain={plan['metadata']['usedomain']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
