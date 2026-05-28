from __future__ import annotations

import argparse
from pathlib import Path


NAME = "vssenum"
DESCRIPTION = "Enumerate volume shadow snapshots exposed over SMB on a remote host."
MYTHIC_ENABLED = False
VARIABLES = [
    {
        "name": "hostname",
        "required": True,
        "description": "Target host name to query.",
    },
    {
        "name": "sharename",
        "required": False,
        "description": "Optional share name. Defaults to C$.",
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


def normalize_hostname(value: str) -> str:
    hostname = ensure_ascii(ensure_no_nul(value, "hostname").strip(), "hostname")
    if not hostname:
        raise ValueError("hostname is required. Pass a host like WORKSTATION or DC01.")
    if hostname.lower().startswith(("http://", "https://", "ldap://", "ldaps://")):
        raise ValueError("hostname must be a host name, not a URL.")
    if hostname.startswith("\\\\"):
        hostname = hostname[2:]
    if not hostname:
        raise ValueError("hostname is not usable after normalization.")
    if "/" in hostname or "\\" in hostname:
        raise ValueError("hostname must be a single host value, not a path or UNC share.")
    if ":" in hostname:
        raise ValueError("hostname should not include a port.")
    if any(ch.isspace() for ch in hostname):
        raise ValueError("hostname must not contain spaces.")
    if len(hostname) > 255:
        raise ValueError("hostname is too long to be a viable host name.")
    return hostname


def normalize_sharename(value: str) -> str:
    sharename = ensure_ascii(ensure_no_nul(value, "sharename").strip(), "sharename")
    if not sharename:
        return "C$"
    if sharename.lower().startswith(("http://", "https://")):
        raise ValueError("sharename must be a share name, not a URL.")
    if sharename.startswith("\\\\"):
        raise ValueError("sharename must be just the share name, not a UNC path.")
    if "/" in sharename or "\\" in sharename:
        raise ValueError("sharename must not contain path separators.")
    if ":" in sharename:
        raise ValueError("sharename must not contain a colon.")
    if len(sharename) > 255:
        raise ValueError("sharename is too long to be a viable share name.")
    return sharename


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
        rendered = rendered.replace(key, c_wide_string_literal(value))
    return rendered


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "hostname",
        help="Target host name to query.",
    )
    parser.add_argument(
        "sharename",
        nargs="?",
        default="C$",
        help="Optional share name. Defaults to C$.",
    )


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    hostname = normalize_hostname(args.hostname)
    sharename = normalize_sharename(args.sharename)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_HOSTNAME__": hostname,
            "__NANO_SHARENAME__": sharename,
        },
        "metadata": {
            "final_hostname": hostname,
            "final_sharename": sharename,
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
        print(f"final_hostname={plan['metadata']['final_hostname']}")
        print(f"final_sharename={plan['metadata']['final_sharename']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
