from __future__ import annotations

import argparse
from pathlib import Path

from nano_bofs.input_validation import normalize_host_like
from nano_bofs.input_validation import normalize_int_range
from nano_bofs.input_validation import normalize_ldap_dn
from nano_bofs.input_validation import normalize_ldap_filter
from nano_bofs.input_validation import normalize_ldap_scope
from nano_bofs.input_validation import normalize_optional_ascii_text


NAME = "ldapsearch"
DESCRIPTION = "Execute LDAP searches with embedded query, scope, target, and connection settings."
VARIABLES = [
    {
        "name": "query",
        "required": True,
        "description": "LDAP filter to execute, such as (objectClass=*).",
        "shape": "Single LDAP filter expression.",
        "example": "(objectClass=computer)",
        "validation": [
            "Must be a valid LDAP filter such as (objectClass=*).",
            "Do not pass WMI or SQL-style query text.",
        ],
        "modal_display_name": "LDAP Filter",
        "placeholder": "(objectClass=computer)",
    },
    {
        "name": "attributes",
        "required": False,
        "description": 'Comma-separated attributes to return. Defaults to "*".',
        "shape": "Comma-separated LDAP attribute names.",
        "example": "cn,dNSHostName",
        "validation": [
            'Leave empty to use the default "*".',
            "Do not include spaces between attribute names unless they are part of the attribute itself.",
        ],
        "modal_display_name": "Attributes",
        "placeholder": "cn,dNSHostName",
    },
    {
        "name": "count",
        "required": False,
        "description": "Maximum number of results to return. Defaults to 0 for no explicit limit.",
        "shape": "Unsigned integer.",
        "example": "100",
        "validation": [
            "Use 0 for no explicit limit.",
            "Must be between 0 and 4294967295.",
        ],
        "modal_display_name": "Count",
        "placeholder": "100",
    },
    {
        "name": "scope",
        "required": False,
        "description": "Search scope: 1/base, 2/one, or 3/subtree. Defaults to 3.",
        "shape": "One of 1, 2, or 3.",
        "example": "3",
        "validation": [
            "1=base, 2=one, 3=subtree.",
            "Leave empty to use subtree.",
        ],
        "modal_display_name": "Scope",
        "placeholder": "3",
    },
    {
        "name": "hostname",
        "required": False,
        "description": "Optional LDAP target host. Leave empty to auto-resolve the DC.",
        "shape": "Single hostname or FQDN.",
        "example": "dc01.example.test",
        "validation": [
            "Leave empty to auto-resolve the domain controller.",
            "Do not include an LDAP scheme, path, or port.",
        ],
        "modal_display_name": "Hostname",
        "placeholder": "dc01.example.test",
    },
    {
        "name": "dn",
        "required": False,
        "description": "Optional base DN. Leave empty to derive it from the current logon context.",
        "shape": "LDAP distinguished name.",
        "example": "DC=example,DC=test",
        "validation": [
            "Leave empty to derive the base DN from the current logon context.",
            "Must be a valid LDAP distinguished name.",
        ],
        "modal_display_name": "Base DN",
        "placeholder": "DC=example,DC=test",
    },
    {
        "name": "ldaps",
        "required": False,
        "description": "Use LDAPS on port 636 instead of LDAP on port 389.",
        "shape": "Boolean flag.",
        "example": "true",
        "validation": [
            "Set true to use LDAPS on port 636.",
            "Leave false or empty to use LDAP on port 389.",
        ],
        "modal_display_name": "Use LDAPS",
    },
]
DEFAULT_TEMPLATE = Path(__file__).with_name("entry.c")
COMMON_INCLUDE_DIR = (
    Path(__file__).resolve().parents[2]
    / "shared" / "common"
)

def normalize_query(value: str) -> str:
    return normalize_ldap_filter(value, label="query")


def normalize_attributes(value: str) -> str:
    attributes = normalize_optional_ascii_text(value, "attributes")
    if not attributes:
        raise ValueError('attributes must not be empty. Omit the flag to use the default "*".')
    if attributes == "*":
        return attributes
    if any(ch.isspace() for ch in attributes):
        raise ValueError(
            "attributes must be a comma-separated LDAP attribute list with no spaces, such as cn,dNSHostName."
        )
    parts = attributes.split(",")
    if any(not part for part in parts):
        raise ValueError("attributes must not contain empty attribute names.")
    return attributes


def normalize_count(value: str) -> int:
    return normalize_int_range(value, label="count", minimum=0, maximum=0xFFFFFFFF)


def normalize_scope(value: str) -> int:
    return normalize_ldap_scope(value, label="scope")


def normalize_hostname(value: str) -> str:
    return normalize_host_like(value, label="hostname", allow_empty=True)


def normalize_dn(value: str) -> str:
    return normalize_ldap_dn(value, label="dn", allow_empty=True)


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
            raise ValueError("ldapsearch strings must be ASCII-safe for this template.")
    return "".join(escaped)


def render_source(template: str, placeholders: dict[str, str]) -> str:
    rendered = template
    for key, value in placeholders.items():
        if key not in rendered:
            raise ValueError(f"template is missing the required placeholder {key}.")
        rendered = rendered.replace(key, value)
    return rendered


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("query", help="LDAP filter to execute, such as (objectClass=*).")
    parser.add_argument(
        "--attributes",
        default="*",
        help='Comma-separated attributes to return. Defaults to "*".',
    )
    parser.add_argument(
        "--count",
        default="0",
        help="Maximum number of results to return. Defaults to 0 for no explicit limit.",
    )
    parser.add_argument(
        "--scope",
        default="3",
        help="Search scope: 1/base, 2/one, or 3/subtree. Defaults to 3.",
    )
    parser.add_argument(
        "--hostname",
        default="",
        help="Optional LDAP target host. Leave empty to auto-resolve the DC.",
    )
    parser.add_argument(
        "--dn",
        default="",
        help="Optional base DN. Leave empty to derive it from the current logon context.",
    )
    parser.add_argument(
        "--ldaps",
        action="store_true",
        help="Use LDAPS on port 636 instead of LDAP on port 389.",
    )


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    query = normalize_query(args.query)
    attributes = normalize_attributes(args.attributes)
    count = normalize_count(args.count)
    scope = normalize_scope(args.scope)
    hostname = normalize_hostname(args.hostname)
    dn = normalize_dn(args.dn)
    ldaps = bool(args.ldaps)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_QUERY__": c_string_literal(query),
            "__NANO_ATTRIBUTES__": c_string_literal(attributes),
            "__NANO_HOSTNAME__": c_string_literal(hostname),
            "__NANO_DN__": c_string_literal(dn),
            "__NANO_COUNT__": str(count),
            "__NANO_SCOPE__": str(scope),
            "__NANO_LDAPS__": "1" if ldaps else "0",
        },
        "metadata": {
            "final_query": query,
            "final_attributes": attributes,
            "final_count": count,
            "final_scope": scope,
            "final_hostname": hostname,
            "final_dn": dn,
            "final_ldaps": ldaps,
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
        print(f"final_query={plan['metadata']['final_query']}")
        print(f"final_attributes={plan['metadata']['final_attributes']}")
        print(f"final_count={plan['metadata']['final_count']}")
        print(f"final_scope={plan['metadata']['final_scope']}")
        print(f"final_hostname={plan['metadata']['final_hostname']}")
        print(f"final_dn={plan['metadata']['final_dn']}")
        print(f"final_ldaps={plan['metadata']['final_ldaps']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
