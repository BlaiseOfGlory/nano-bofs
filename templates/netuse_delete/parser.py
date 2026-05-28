from __future__ import annotations

import argparse
from pathlib import Path

from nano_bofs.input_validation import normalize_optional_boolish


NAME = "netuse_delete"
DESCRIPTION = "Delete a network-use connection."
VARIABLES = [
    {
        "name": "target",
        "required": True,
        "description": "Drive letter or UNC target to delete.",
        "shape": "Drive letter or UNC path.",
        "example": "\\\\192.0.2.10\\MissingShare",
        "validation": [
            "Pass a drive letter like Z: or a UNC path.",
        ],
        "modal_display_name": "Target",
        "placeholder": "\\\\192.0.2.10\\MissingShare",
    },
    {
        "name": "persist",
        "required": False,
        "description": "Delete a persisted mapping.",
        "shape": "Boolean flag.",
        "example": "true",
        "validation": [
            "Accepted true values: 1, true, yes, y, on.",
            "Accepted false values: empty, 0, false, no, n, off.",
        ],
        "modal_display_name": "Persist",
        "placeholder": "true",
    },
    {
        "name": "force",
        "required": False,
        "description": "Force deletion.",
        "shape": "Boolean flag.",
        "example": "true",
        "validation": [
            "Accepted true values: 1, true, yes, y, on.",
            "Accepted false values: empty, 0, false, no, n, off.",
        ],
        "modal_display_name": "Force",
        "placeholder": "true",
    }
]
DEFAULT_TEMPLATE = Path(__file__).resolve().parents[1] / "netuse" / "entry.c"
COMMON_INCLUDE_DIR = (
    Path(__file__).resolve().parents[2]
    / "shared" / "common"
)


def ensure_no_nul(value: str, label: str) -> str:
    if "\x00" in value:
        raise ValueError(f"{label} contains a NUL byte, which cannot be embedded into the BOF source.")
    return value


def ensure_ascii(value: str, label: str) -> str:
    try:
        value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{label} must be ASCII for this BOF.") from exc
    return value


def normalize_target(value: str) -> str:
    target = ensure_ascii(ensure_no_nul(value, "target").strip(), "target")
    if not target:
        raise ValueError("target is required.")
    if len(target) == 1:
        if not target.isalpha():
            raise ValueError("single-character targets must be drive letters.")
        return target.upper() + ":"
    if len(target) == 2 and target[0].isalpha() and target[1] == ":":
        return target.upper()
    if len(target) > 2:
        return target if target.startswith("\\\\") else "\\\\" + target
    return target


def c_wide_string_literal(value: str) -> str:
    escaped: list[str] = []
    for ch in value:
        if ch == "\\":
            escaped.append("\\\\")
        elif ch == '"':
            escaped.append('\\"')
        elif 32 <= ord(ch) <= 126:
            escaped.append(ch)
        else:
            escaped.append(f"\\x{ord(ch):04x}")
    return "".join(escaped)


def render_source(template: str, placeholders: dict[str, str]) -> str:
    rendered = template
    for key, value in placeholders.items():
        if key not in rendered:
            raise ValueError(f"template is missing the required placeholder {key}.")
        rendered = rendered.replace(key, value)
    return rendered


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("target", help="Drive letter or UNC target to delete.")
    parser.add_argument("persist", nargs="?", default="", help="Optional persist flag.")
    parser.add_argument("force", nargs="?", default="", help="Optional force flag.")


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    target = normalize_target(args.target)
    persist = normalize_optional_boolish(args.persist, label="persist")
    force = normalize_optional_boolish(args.force, label="force")

    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_CMD__": "3",
            "__NANO_TARGET__": c_wide_string_literal(target),
            "__NANO_SHARE_NAME__": "",
            "__NANO_USERNAME__": "",
            "__NANO_PASSWORD__": "",
            "__NANO_DEVICE_NAME__": "",
            "__NANO_PERSIST__": "1" if persist else "0",
            "__NANO_REQUIRE_PRIVACY__": "0",
            "__NANO_FORCE__": "1" if force else "0",
        },
        "metadata": {
            "target": target,
            "persist": persist,
            "force": force,
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
        print(f"target={plan['metadata']['target']}")
        print(f"persist={plan['metadata']['persist']}")
        print(f"force={plan['metadata']['force']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
