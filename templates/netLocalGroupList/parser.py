from __future__ import annotations

import argparse
from pathlib import Path

from nano_bofs.input_validation import normalize_host_like


NAME = "netLocalGroupList"
DESCRIPTION = "List local groups from the local or specified computer."
VARIABLES = [
    {
        "name": "server",
        "required": False,
        "description": "Optional server host name.",
        "shape": "Single bare host name or IPv4 literal.",
        "example": "workstation",
        "validation": [
            "Leave empty to target the local host.",
            "Must not be a URL or UNC path.",
        ],
        "modal_display_name": "Server",
        "placeholder": "workstation",
    }
]
DEFAULT_TEMPLATE = Path(__file__).with_name("entry.c")
COMMON_INCLUDE_DIR = (
    Path(__file__).resolve().parents[2]
    / "shared" / "common"
)

def normalize_server(value: str) -> str:
    bare_server = normalize_host_like(value, label="server", allow_empty=True)
    if not bare_server:
        return ""
    return f"\\\\{bare_server}"


def c_wide_string_literal(value: str) -> str:
    escaped = []
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
        rendered = rendered.replace(key, c_wide_string_literal(value))
    return rendered


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "server",
        nargs="?",
        default="",
        help="Optional server name. Leave empty to target the local host.",
    )


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    server = normalize_server(args.server)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_SERVER__": server,
        },
        "metadata": {
            "final_server": server,
            "targets_local_host": server == "",
        },
        "build": {
            "include_dirs": [str(COMMON_INCLUDE_DIR)],
            "cflags": ["-fno-jump-tables", "-Os", "-c", "-DBOF"],
        },
    }


def render_plan(plan: dict[str, object]) -> str:
    template = Path(plan["template_path"]).read_text(encoding="utf-8")
    placeholders = dict(plan["placeholders"])
    return render_source(template, placeholders)


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
        print(f"final_server={plan['metadata']['final_server']}")
        print(f"targets_local_host={plan['metadata']['targets_local_host']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
