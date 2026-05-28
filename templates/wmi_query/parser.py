from __future__ import annotations

import argparse
from pathlib import Path

from nano_bofs.input_validation import normalize_host_like
from nano_bofs.input_validation import normalize_wmi_namespace
from nano_bofs.input_validation import normalize_wql_query


NAME = "wmi_query"
DESCRIPTION = "Run a general WMI query."
VARIABLES = [
    {
        "name": "query",
        "required": True,
        "description": "WQL query to run.",
        "shape": "Single ASCII WQL query string.",
        "example": "SELECT Name FROM Win32_ComputerSystem",
        "modal_display_name": "Query",
        "mythic_parameter_type": "String",
        "placeholder": "SELECT Name FROM Win32_ComputerSystem",
        "validation": [
            "Rejects empty values and NUL bytes.",
        ],
    },
    {
        "name": "server",
        "required": False,
        "description": "Optional remote system. Defaults to local '.'.",
        "shape": "Single host value or '.'.",
        "example": "DC01",
        "modal_display_name": "Server",
        "mythic_parameter_type": "String",
        "placeholder": "DC01",
        "validation": [
            "Rejects URLs, paths, ports, spaces, and overlong values.",
        ],
    },
    {
        "name": "namespace",
        "required": False,
        "description": r"Optional namespace. Defaults to root\cimv2.",
        "shape": "Single WMI namespace path.",
        "example": r"root\cimv2",
        "modal_display_name": "Namespace",
        "mythic_parameter_type": "String",
        "placeholder": r"root\cimv2",
        "validation": [
            "Rejects NUL bytes and forward-slash path shapes.",
        ],
    },
]
VALIDATION_RULES = [
    "Inputs are validated at build time before BOF source rendering.",
    "The generated BOF takes no runtime arguments.",
    r"The final resource string is rendered as \\<server>\<namespace>.",
]
INPUT_NOTES = [
    "Use '.' for the local host.",
    "Pass a bare host like DC01, not a UNC path or URL.",
]
DEFAULT_TEMPLATE = Path(__file__).with_name("entry.c")
COMMON_INCLUDE_DIR = (
    Path(__file__).resolve().parents[2]
    / "shared" / "common"
)
DEFAULT_SERVER = "."
DEFAULT_NAMESPACE = r"root\cimv2"


def normalize_query(value: str) -> str:
    return normalize_wql_query(value, label="query")


def normalize_server(value: str | None) -> str:
    if value is None:
        return DEFAULT_SERVER
    server = normalize_host_like(value, label="server", allow_empty=True, default=DEFAULT_SERVER, allow_dot=True)
    return server or DEFAULT_SERVER


def normalize_namespace(value: str | None) -> str:
    return normalize_wmi_namespace(value, label="namespace", default=DEFAULT_NAMESPACE)


def build_resource(server: str, namespace: str) -> str:
    return f"\\\\{server}\\{namespace}"


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
    parser.add_argument("query", help="WQL query to run.")
    parser.add_argument("server", nargs="?", default=DEFAULT_SERVER, help="Optional remote system. Defaults to local '.'.")
    parser.add_argument(
        "namespace",
        nargs="?",
        default=DEFAULT_NAMESPACE,
        help=r"Optional namespace. Defaults to root\cimv2.",
    )


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    query = normalize_query(args.query)
    server = normalize_server(args.server)
    namespace = normalize_namespace(args.namespace)
    resource = build_resource(server, namespace)

    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_SERVER__": c_wide_string_literal(server),
            "__NANO_NAMESPACE__": c_wide_string_literal(namespace),
            "__NANO_QUERY__": c_wide_string_literal(query),
            "__NANO_RESOURCE__": c_wide_string_literal(resource),
        },
        "metadata": {
            "server": server,
            "namespace": namespace,
            "query": query,
            "resource": resource,
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
        for key, value in plan["metadata"].items():
            print(f"{key}={value}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
