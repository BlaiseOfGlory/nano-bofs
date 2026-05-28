from __future__ import annotations

import argparse
from pathlib import Path


NAME = "netuse_list"
DESCRIPTION = "List current network-use connections."
VARIABLES = [
    {
        "name": "target",
        "required": False,
        "description": "Optional drive letter or remote target.",
    }
]
DEFAULT_TEMPLATE = Path(__file__).with_name("entry.c")
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
        return ""
    if len(target) == 1:
        if not target.isalpha():
            raise ValueError("single-character targets must be drive letters.")
        return target.upper() + ":"
    if len(target) == 2 and target[0].isalpha() and target[1] == ":":
        return target.upper()
    return target if target.startswith("\\\\") else "\\\\" + target


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
    parser.add_argument("target", nargs="?", default="", help="Optional drive letter or remote target.")


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    target = normalize_target(args.target)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_TARGET__": c_wide_string_literal(target),
        },
        "metadata": {
            "target": target,
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
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
