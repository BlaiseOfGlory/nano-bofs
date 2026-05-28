from __future__ import annotations

import argparse
from ipaddress import IPv4Address
from pathlib import Path


NAME = "nslookup"
DESCRIPTION = "Resolve a hostname or IP with an optional DNS server and record type."
VARIABLES = [
    {
        "name": "hostname",
        "required": True,
        "description": "Hostname or IP address to resolve.",
    },
    {
        "name": "dns_server",
        "required": False,
        "description": "Optional IPv4 DNS server. Use 0 or omit for the system default.",
    },
    {
        "name": "record_type",
        "required": False,
        "description": "Optional DNS record type. Unknown values fall back to A.",
    },
]
DEFAULT_TEMPLATE = Path(__file__).with_name("entry.c")
COMMON_INCLUDE_DIR = (
    Path(__file__).resolve().parents[2]
    / "shared" / "common"
)

RECORD_TYPES: dict[str, int] = {
    "A": 0x0001,
    "NS": 0x0002,
    "MD": 0x0003,
    "MF": 0x0004,
    "CNAME": 0x0005,
    "SOA": 0x0006,
    "MB": 0x0007,
    "MG": 0x0008,
    "MR": 0x0009,
    "WKS": 0x000B,
    "PTR": 0x000C,
    "HINFO": 0x000D,
    "MINFO": 0x000E,
    "MX": 0x000F,
    "TEXT": 0x0010,
    "RP": 0x0011,
    "AFSDB": 0x0012,
    "X25": 0x0013,
    "ISDN": 0x0014,
    "RT": 0x0015,
    "KEY": 0x0019,
    "AAAA": 0x001C,
    "SRV": 0x0021,
    "ANY": 0x00FF,
    "WINSR": 0xFF02,
}


def ensure_no_nul(value: str, label: str) -> str:
    if "\x00" in value:
        raise ValueError(f"{label} contains a NUL byte, which cannot be embedded into the BOF source.")
    return value


def ensure_ascii(value: str, label: str) -> str:
    try:
        value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{label} must be ASCII for this BOF.") from exc
    return value


def normalize_hostname(value: str) -> str:
    hostname = ensure_ascii(ensure_no_nul(value, "hostname").strip(), "hostname")
    if not hostname:
        raise ValueError("hostname is required.")
    if any(ch.isspace() for ch in hostname):
        raise ValueError("hostname must not contain spaces.")
    if hostname.lower().startswith(("http://", "https://", "ldap://", "ldaps://")):
        raise ValueError("hostname must be a hostname or IP, not a URL.")
    if "/" in hostname or "\\" in hostname:
        raise ValueError("hostname must be a single hostname or IP value, not a path.")
    return hostname


def normalize_server(value: str) -> str:
    server = ensure_ascii(ensure_no_nul(value, "dns server").strip(), "dns server")
    if not server or server == "0":
        return ""
    if any(ch.isspace() for ch in server):
        raise ValueError("dns server must not contain spaces.")
    try:
        parsed = IPv4Address(server)
    except ValueError as exc:
        raise ValueError("dns server must be an IPv4 address, 0, or omitted.") from exc
    if str(parsed) == "127.0.0.1":
        raise ValueError("dns server 127.0.0.1 is refused because upstream warns it can crash.")
    return str(parsed)


def normalize_record_type(value: str) -> tuple[str, int]:
    requested = ensure_ascii(ensure_no_nul(value, "record type").strip(), "record type").upper()
    if not requested:
        requested = "A"
    final_name = requested if requested in RECORD_TYPES else "A"
    return final_name, RECORD_TYPES[final_name]


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
        "hostname",
        help="Hostname or IP address to resolve.",
    )
    parser.add_argument(
        "dns_server",
        nargs="?",
        default="",
        help="Optional IPv4 DNS server. Use 0 or omit for the system default.",
    )
    parser.add_argument(
        "record_type",
        nargs="?",
        default="A",
        help="Optional DNS record type. Unknown values fall back to A.",
    )


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    hostname = normalize_hostname(args.hostname)
    dns_server = normalize_server(args.dns_server)
    record_type_name, record_type_value = normalize_record_type(args.record_type)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_LOOKUP__": c_string_literal(hostname),
            "__NANO_SERVER__": c_string_literal(dns_server),
            "__NANO_RECORD_TYPE__": str(record_type_value),
        },
        "metadata": {
            "final_lookup": hostname,
            "final_server": dns_server,
            "uses_system_default_server": dns_server == "",
            "final_record_type_name": record_type_name,
            "final_record_type_value": record_type_value,
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
        print(f"final_lookup={plan['metadata']['final_lookup']}")
        print(f"final_server={plan['metadata']['final_server']}")
        print(f"uses_system_default_server={plan['metadata']['uses_system_default_server']}")
        print(f"final_record_type_name={plan['metadata']['final_record_type_name']}")
        print(f"final_record_type_value={plan['metadata']['final_record_type_value']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
