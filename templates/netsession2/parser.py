from __future__ import annotations

import argparse
from ipaddress import IPv4Address
from pathlib import Path


NAME = "netsession2"
DESCRIPTION = "Enumerate server sessions with optional client resolution."
VARIABLES = [
    {
        "name": "computer",
        "required": False,
        "description": "Optional target computer name.",
    },
    {
        "name": "resolution_method",
        "required": False,
        "description": "Optional client resolution method: 1 for DNS, 2 for NetWkstaGetInfo. Omitted defaults to NetWkstaGetInfo.",
    },
    {
        "name": "dns_server",
        "required": False,
        "description": "Optional IPv4 DNS server used for DNS resolution mode.",
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


def ensure_ascii(value: str, label: str) -> str:
    try:
        value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{label} must be ASCII for this BOF.") from exc
    return value


def normalize_computer(value: str) -> str:
    computer = ensure_ascii(ensure_no_nul(value, "computer").strip(), "computer")
    if not computer:
        return ""
    lower = computer.lower()
    if lower.startswith(("http://", "https://", "ldap://", "ldaps://")):
        raise ValueError("computer should be a host name, not a URL.")
    if computer.startswith("\\\\"):
        bare = computer[2:]
    else:
        bare = computer
    bare = bare.strip()
    if not bare:
        raise ValueError("computer value is not usable after normalization.")
    if "/" in bare or "\\" in bare:
        raise ValueError("computer must be a single host value. Do not pass a UNC path.")
    if ":" in bare:
        raise ValueError("computer should not include a port. Pass only the host name.")
    if any(ch.isspace() for ch in bare):
        raise ValueError("computer must not contain spaces.")
    if len(bare) > 255:
        raise ValueError("computer is too long to be a viable host name.")
    return f"\\\\{bare}"


def normalize_resolution_method(value: str) -> tuple[int, int, str]:
    text = ensure_no_nul(value, "resolution method").strip()
    if not text:
        text = "2"
    try:
        external = int(text, 10)
    except ValueError as exc:
        raise ValueError("resolution method must be 1 or 2.") from exc
    if external == 1:
        return external, 0, "DNS"
    if external == 2:
        return external, 1, "NetWkstaGetInfo"
    raise ValueError("resolution method must be 1 (DNS) or 2 (NetWkstaGetInfo).")


def normalize_dns_server(value: str) -> str:
    server = ensure_ascii(ensure_no_nul(value, "dns server").strip(), "dns server")
    if not server:
        return ""
    if any(ch.isspace() for ch in server):
        raise ValueError("dns server must not contain spaces.")
    try:
        parsed = IPv4Address(server)
    except ValueError as exc:
        raise ValueError("dns server must be an IPv4 address or omitted.") from exc
    return str(parsed)


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
    parser.add_argument(
        "computer",
        nargs="?",
        default="",
        help="Optional target computer name.",
    )
    parser.add_argument(
        "resolution_method",
        nargs="?",
        default="2",
        help="Optional resolution method: 1 for DNS, 2 for NetWkstaGetInfo. Omitted defaults to NetWkstaGetInfo.",
    )
    parser.add_argument(
        "dns_server",
        nargs="?",
        default="",
        help="Optional IPv4 DNS server used for DNS resolution mode.",
    )


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    computer = normalize_computer(args.computer)
    requested_method, internal_method, method_name = normalize_resolution_method(args.resolution_method)
    dns_server = normalize_dns_server(args.dns_server)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_HOSTNAME__": c_wide_string_literal(computer),
            "__NANO_RESOLVE_METHOD__": str(internal_method),
            "__NANO_DNSSERVER__": c_string_literal(dns_server),
        },
        "metadata": {
            "final_computer": computer,
            "requested_resolution_method": requested_method,
            "internal_resolution_method": internal_method,
            "resolution_method_name": method_name,
            "final_dns_server": dns_server,
            "targets_local_host": computer == "",
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
        print(f"final_computer={plan['metadata']['final_computer']}")
        print(f"requested_resolution_method={plan['metadata']['requested_resolution_method']}")
        print(f"internal_resolution_method={plan['metadata']['internal_resolution_method']}")
        print(f"resolution_method_name={plan['metadata']['resolution_method_name']}")
        print(f"final_dns_server={plan['metadata']['final_dns_server']}")
        print(f"targets_local_host={plan['metadata']['targets_local_host']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
