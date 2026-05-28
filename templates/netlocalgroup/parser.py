from __future__ import annotations

import argparse
from pathlib import Path

from nano_bofs.input_validation import normalize_host_like


NAME = "netlocalgroup"
DESCRIPTION = "List members of the specified local group from the local or a remote server."
VARIABLES = [
    {
        "name": "groupname",
        "required": True,
        "description": "Local group name to enumerate.",
        "shape": "Single local group name.",
        "example": "Administrators",
        "validation": [
            "Must not be empty.",
            "Keep it to 255 characters or fewer.",
        ],
        "modal_display_name": "Group Name",
        "placeholder": "Administrators",
    },
    {
        "name": "server",
        "required": False,
        "description": "Optional target server host name.",
        "shape": "Single bare host name or IPv4 literal.",
        "example": "workstation",
        "validation": [
            "Leave empty to target the local host.",
            "Must not be a URL or UNC path.",
        ],
        "modal_display_name": "Server",
        "placeholder": "workstation",
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


def normalize_groupname(value: str) -> str:
    groupname = ensure_no_nul(value, "groupname").strip()
    if not groupname:
        raise ValueError("groupname is required. Pass a local group like \"Administrators\".")
    if len(groupname) > 255:
        raise ValueError("groupname is too long. Keep it to 255 characters or fewer.")
    return groupname


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
    parser.add_argument("groupname", help="Local group name to enumerate.")
    parser.add_argument(
        "server",
        nargs="?",
        default="",
        help="Optional server name. Leave empty to target the local host.",
    )


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    groupname = normalize_groupname(args.groupname)
    server = normalize_server(args.server)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_GROUP__": groupname,
            "__NANO_SERVER__": server,
        },
        "metadata": {
            "final_groupname": groupname,
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
        print(f"final_groupname={plan['metadata']['final_groupname']}")
        print(f"final_server={plan['metadata']['final_server']}")
        print(f"targets_local_host={plan['metadata']['targets_local_host']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
