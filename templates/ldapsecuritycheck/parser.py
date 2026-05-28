from __future__ import annotations

import argparse
from pathlib import Path


NAME = "ldapsecuritycheck"
DESCRIPTION = "Check LDAP signing and LDAPS channel binding requirements on domain controllers. Performs authentication tests to detect security configurations."
VARIABLES = [
    {
        "name": "dc",
        "required": True,
        "description": "Domain controller hostname or FQDN.",
        "shape": "Single hostname or FQDN.",
        "example": "dc01.example.test",
        "validation": [
            "Pass only the hostname or FQDN.",
            "Do not include an LDAP scheme, path, or port.",
        ],
        "modal_display_name": "Domain Controller",
        "placeholder": "dc01.example.test",
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


def normalize_dc(value: str) -> str:
    dc = ensure_no_nul(value, "domain controller").strip()
    if dc.startswith("\\\\"):
        dc = dc[2:]
    dc = dc.rstrip("\\/")
    if not dc:
        raise ValueError("domain controller value is required. Provide a hostname or FQDN such as dc01.corp.local.")
    lower = dc.lower()
    if lower.startswith("ldap://") or lower.startswith("ldaps://"):
        raise ValueError("domain controller should be a hostname or FQDN, not an LDAP URL. Try something like dc01.corp.local.")
    if "/" in dc or "\\" in dc:
        raise ValueError("domain controller must be a single host value. Do not pass an SPN, UNC path, or URL.")
    if ":" in dc:
        raise ValueError("domain controller should not include a port. Pass just the host name and the parser will build the SPN.")
    if any(ch.isspace() for ch in dc):
        raise ValueError("domain controller must not contain spaces. Pass a hostname or FQDN only.")
    if len(dc) > 255:
        raise ValueError("domain controller is too long to be a viable host name. Keep it to 255 characters or fewer.")
    return dc


def build_spn(dc: str) -> str:
    spn = f"ldap/{dc}"
    if len(spn) > 255:
        raise ValueError("generated SPN is longer than 255 characters. Use a shorter domain controller name.")
    return spn


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
    parser.add_argument("dc", help="Domain controller hostname or FQDN")


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    dc = normalize_dc(args.dc)
    spn = build_spn(dc)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_FINAL_DC__": dc,
            "__NANO_FINAL_SPN__": spn,
        },
        "metadata": {
            "final_dc": dc,
            "final_spn": spn,
        },
        "build": {
            "include_dirs": [str(COMMON_INCLUDE_DIR)],
            "cflags": ["-Os", "-c", "-DBOF"],
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
        print(f"final_dc={plan['metadata']['final_dc']}")
        print(f"final_spn={plan['metadata']['final_spn']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
