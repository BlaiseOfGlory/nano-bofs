from __future__ import annotations

import argparse
from pathlib import Path

from nano_bofs.input_validation import normalize_host_like, normalize_service_name


NAME = "sc_query"
DESCRIPTION = "Query a specific service or enumerate all services on the local or a remote host."
MYTHIC_ENABLED = False
VARIABLES = [
    {
        "name": "service_name",
        "required": False,
        "description": "Optional service name to query. Leave empty to enumerate all services.",
        "shape": "Single Windows service key name.",
        "example": "wuauserv",
        "validation": [
            "Leave empty to enumerate all services.",
            "Pass the service key name, not a display name or WMI query.",
        ],
        "modal_display_name": "Service Name",
        "placeholder": "wuauserv",
    },
    {
        "name": "server",
        "required": False,
        "description": "Optional target server host name.",
        "shape": "Single NetBIOS host name or FQDN.",
        "example": "DC01",
        "validation": [
            "Leave empty to target the local host.",
            "Pass only a host name, not a UNC path, URL, or port.",
        ],
        "modal_display_name": "Server",
        "placeholder": "DC01",
    },
]
DEFAULT_TEMPLATE = Path(__file__).with_name("entry.c")
COMMON_INCLUDE_DIR = (
    Path(__file__).resolve().parents[2]
    / "shared" / "common"
)

def normalize_server(value: str) -> str:
    server = normalize_host_like(value, label="server", allow_empty=True)
    if not server:
        return ""
    return f"\\\\{server}"


def c_string_literal(value: str) -> str:
    escaped: list[str] = []
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


def render_source(template: str, placeholders: dict[str, str]) -> str:
    rendered = template
    for key, value in placeholders.items():
        if key not in rendered:
            raise ValueError(f"template is missing the required placeholder {key}.")
        rendered = rendered.replace(key, value)
    return rendered


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "service_name",
        nargs="?",
        default="",
        help="Optional service name. Leave empty to enumerate all services.",
    )
    parser.add_argument(
        "server",
        nargs="?",
        default="",
        help="Optional server name. Leave empty to target the local host.",
    )


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    service_name = normalize_service_name(args.service_name, allow_empty=True)
    server = normalize_server(args.server)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_SERVICE_NAME__": c_string_literal(service_name),
            "__NANO_SERVER__": c_string_literal(server),
        },
        "metadata": {
            "final_service_name": service_name,
            "final_server": server,
            "enumerates_all_services": service_name == "",
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
        print(f"final_service_name={plan['metadata']['final_service_name']}")
        print(f"final_server={plan['metadata']['final_server']}")
        print(f"enumerates_all_services={plan['metadata']['enumerates_all_services']}")
        print(f"targets_local_host={plan['metadata']['targets_local_host']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
