from __future__ import annotations

import argparse
from pathlib import Path


NAME = "netloggedon2"
DESCRIPTION = "Return logged-on users in a BOFHound-friendly format from the local or remote computer."
VARIABLES = [
    {
        "name": "server",
        "required": False,
        "description": "Optional server host name.",
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


def normalize_server(value: str) -> str:
    server = ensure_no_nul(value, "server").strip()
    if not server:
        return ""
    lower = server.lower()
    if lower.startswith("ldap://") or lower.startswith("ldaps://"):
        raise ValueError("server should be a host name, not an LDAP URL. Try DC01 or \\\\DC01.")
    if server.startswith("\\\\"):
        bare_server = server[2:]
    else:
        bare_server = server
    bare_server = bare_server.strip()
    if not bare_server:
        raise ValueError("server value is not usable after normalization. Provide a host like DC01 or leave it empty for the local host.")
    if "/" in bare_server or "\\" in bare_server:
        raise ValueError("server must be a single host value. Do not pass a UNC path or share name.")
    if ":" in bare_server:
        raise ValueError("server should not include a port. Pass just the host name.")
    if any(ch.isspace() for ch in bare_server):
        raise ValueError("server must not contain spaces. Pass a host name or FQDN only.")
    if len(bare_server) > 255:
        raise ValueError("server is too long to be a viable host name. Keep it to 255 characters or fewer.")
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
        print(f"final_server={plan['metadata']['final_server']}")
        print(f"targets_local_host={plan['metadata']['targets_local_host']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
