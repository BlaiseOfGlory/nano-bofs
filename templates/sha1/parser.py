from __future__ import annotations

import argparse
from pathlib import Path


NAME = "sha1"
DESCRIPTION = "Compute the SHA1 hash of a file."
VARIABLES = [
    {
        "name": "path",
        "required": True,
        "description": "File path to hash.",
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


def normalize_path(value: str) -> str:
    path = ensure_no_nul(value, "path").strip()
    if not path:
        raise ValueError("path must not be empty. Pass a file path to hash.")
    return path


def c_string_literal(value: str) -> str:
    escaped = []
    for ch in value:
        if ch == "\\":
            escaped.append("\\\\")
        elif ch == '"':
            escaped.append('\\"')
        elif 32 <= ord(ch) <= 126:
            escaped.append(ch)
        else:
            raise ValueError("path must be ASCII-safe for this template.")
    return "".join(escaped)


def render_source(template: str, placeholders: dict[str, str]) -> str:
    rendered = template
    for key, value in placeholders.items():
        if key not in rendered:
            raise ValueError(f"template is missing the required placeholder {key}.")
        rendered = rendered.replace(key, c_string_literal(value))
    return rendered


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", help="File path to hash.")


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    path = normalize_path(args.path)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_PATH__": path,
        },
        "metadata": {
            "final_path": path,
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
        print(f"final_path={plan['metadata']['final_path']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
