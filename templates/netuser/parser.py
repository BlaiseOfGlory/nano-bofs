from __future__ import annotations

import argparse
from pathlib import Path


NAME = "netuser"
DESCRIPTION = "List account details for a user on the local computer or specified domain."
VARIABLES = [
    {
        "name": "username",
        "required": True,
        "description": "Target user name.",
        "shape": "Single SAM-compatible user name.",
        "example": "domainadmin",
        "validation": [
            "Must not be empty.",
            "Pass only the user name, not domain\\user or a UPN.",
        ],
        "modal_display_name": "Username",
        "placeholder": "domainadmin",
    },
    {
        "name": "domain",
        "required": False,
        "description": "Optional DNS or NetBIOS domain name. Leave empty to query the local host.",
        "shape": "Single DNS or NetBIOS domain value.",
        "example": "example.test",
        "validation": [
            "Leave empty to query the local host.",
            "Must not be a URL, UNC path, or include a port.",
        ],
        "modal_display_name": "Domain",
        "placeholder": "example.test",
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


def normalize_username(value: str) -> str:
    username = ensure_no_nul(value, "username").strip()
    if not username:
        raise ValueError("username is required.")
    return username


def normalize_domain(value: str) -> str:
    domain = ensure_no_nul(value, "domain").strip()
    if not domain:
        return ""
    if domain.startswith("\\\\"):
        domain = domain[2:]
    if not domain:
        return ""
    lower = domain.lower()
    if lower.startswith("ldap://") or lower.startswith("ldaps://"):
        raise ValueError("domain should be a DNS or NetBIOS value, not an LDAP URL.")
    if "/" in domain or "\\" in domain:
        raise ValueError("domain must be a single domain value, not a path or UNC string.")
    if ":" in domain:
        raise ValueError("domain should not include a port.")
    if any(ch.isspace() for ch in domain):
        raise ValueError("domain must not contain spaces. Pass a DNS or NetBIOS domain value only.")
    if len(domain) > 255:
        raise ValueError("domain is too long to be a viable DNS or NetBIOS value.")
    return domain


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
        "username",
        help="Target user name.",
    )
    parser.add_argument(
        "domain",
        nargs="?",
        default="",
        help="Optional DNS or NetBIOS domain name. Leave empty to query the local host.",
    )


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    username = normalize_username(args.username)
    domain = normalize_domain(args.domain)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_USERNAME__": username,
            "__NANO_DOMAIN__": domain,
        },
        "metadata": {
            "final_username": username,
            "final_domain": domain,
            "targets_local_host": domain == "",
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
        print(f"final_username={plan['metadata']['final_username']}")
        print(f"final_domain={plan['metadata']['final_domain']}")
        print(f"targets_local_host={plan['metadata']['targets_local_host']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
