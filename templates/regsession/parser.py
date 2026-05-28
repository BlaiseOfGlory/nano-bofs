from __future__ import annotations

import argparse
from pathlib import Path


NAME = "regsession"
DESCRIPTION = "Enumerate user registry hives on the local or specified computer."
VARIABLES = [
    {
        "name": "hostname",
        "required": False,
        "description": "Optional host name.",
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


def normalize_hostname(value: str) -> str:
    hostname = ensure_no_nul(value, "hostname").strip()
    if not hostname:
        return ""
    lower = hostname.lower()
    if lower.startswith("ldap://") or lower.startswith("ldaps://"):
        raise ValueError("hostname should be a host name, not an LDAP URL. Try DC01.")
    if hostname.startswith("\\\\"):
        bare_hostname = hostname[2:]
    else:
        bare_hostname = hostname
    bare_hostname = bare_hostname.strip()
    if not bare_hostname:
        raise ValueError("hostname value is not usable after normalization. Provide a host like DC01 or leave it empty for the local host.")
    if "/" in bare_hostname or "\\" in bare_hostname:
        raise ValueError("hostname must be a single host value. Do not pass a UNC path or share name.")
    if ":" in bare_hostname:
        raise ValueError("hostname should not include a port. Pass just the host name.")
    if any(ch.isspace() for ch in bare_hostname):
        raise ValueError("hostname must not contain spaces. Pass a host name or FQDN only.")
    if len(bare_hostname) > 255:
        raise ValueError("hostname is too long to be a viable host name. Keep it to 255 characters or fewer.")
    return bare_hostname


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
            raise ValueError("hostname must be ASCII-safe for this template.")
    return "".join(escaped)


def render_source(template: str, placeholders: dict[str, str]) -> str:
    rendered = template
    for key, value in placeholders.items():
        if key not in rendered:
            raise ValueError(f"template is missing the required placeholder {key}.")
        rendered = rendered.replace(key, c_string_literal(value))
    return rendered


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "hostname",
        nargs="?",
        default="",
        help="Optional host name. Leave empty to target the local host.",
    )


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    hostname = normalize_hostname(args.hostname)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_HOSTNAME__": hostname,
        },
        "metadata": {
            "final_hostname": hostname,
            "targets_local_host": hostname == "",
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
        print(f"final_hostname={plan['metadata']['final_hostname']}")
        print(f"targets_local_host={plan['metadata']['targets_local_host']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
