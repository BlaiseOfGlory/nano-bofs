from __future__ import annotations

import argparse
from pathlib import Path


NAME = "dir"
DESCRIPTION = "List a target directory, optionally recursing into subdirectories."
VARIABLES = [
    {
        "name": "directory",
        "required": False,
        "description": "Optional target directory. Defaults to .\\",
    },
    {
        "name": "/s",
        "required": False,
        "description": "Optional recursive listing flag.",
    },
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
            escaped.append(f"\\x{ord(ch):02x}")
    return "".join(escaped)


def normalize_inputs(directory: str, recursive: str) -> tuple[str, bool]:
    final_directory = ensure_no_nul(directory, "directory").strip()
    final_recursive = ensure_no_nul(recursive, "recursive flag").strip()

    if final_directory.lower() == "/s" and not final_recursive:
        final_directory = ""
        final_recursive = "/s"

    if final_recursive and final_recursive.lower() != "/s":
        raise ValueError("the only supported flag is /s.")

    if not final_directory:
        final_directory = ".\\"

    return final_directory, final_recursive.lower() == "/s"


def render_source(template: str, path_value: str, recursive: bool) -> str:
    if "__NANO_PATH__" not in template:
        raise ValueError("template is missing the required placeholder __NANO_PATH__.")
    if "__NANO_SUBDIRS__" not in template:
        raise ValueError("template is missing the required placeholder __NANO_SUBDIRS__.")
    rendered = template.replace("__NANO_PATH__", c_string_literal(path_value))
    rendered = rendered.replace("__NANO_SUBDIRS__", "1" if recursive else "0")
    return rendered


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "directory",
        nargs="?",
        default="",
        help="Optional target directory. Defaults to .\\",
    )
    parser.add_argument(
        "recursive",
        nargs="?",
        default="",
        help="Optional /s flag for recursive enumeration.",
    )


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    directory, recursive = normalize_inputs(args.directory, args.recursive)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "metadata": {
            "final_directory": directory,
            "recursive": recursive,
        },
        "build": {
            "include_dirs": [str(COMMON_INCLUDE_DIR)],
            "cflags": ["-Os", "-c", "-DBOF"],
        },
    }


def render_plan(plan: dict[str, object]) -> str:
    template = Path(plan["template_path"]).read_text(encoding="utf-8")
    metadata = dict(plan["metadata"])
    return render_source(
        template,
        str(metadata["final_directory"]),
        bool(metadata["recursive"]),
    )


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
        print(f"final_directory={plan['metadata']['final_directory']}")
        print(f"recursive={plan['metadata']['recursive']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
