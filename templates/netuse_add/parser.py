from __future__ import annotations

import argparse
from pathlib import Path

from nano_bofs.input_validation import (
    normalize_device_name,
    normalize_optional_boolish,
    normalize_optional_ascii_text,
    normalize_unc_share,
)


NAME = "netuse_add"
DESCRIPTION = "Create a new network-use connection."
VARIABLES = [
    {
        "name": "share",
        "required": True,
        "description": "UNC share like \\\\HOST\\Share.",
        "shape": "UNC share path.",
        "example": "\\\\192.0.2.10\\IPC$",
        "validation": [
            "Must be a UNC path like \\\\HOST\\Share.",
        ],
        "modal_display_name": "Share",
        "placeholder": "\\\\192.0.2.10\\IPC$",
    },
    {
        "name": "username",
        "required": False,
        "description": "Optional username for the network-use connection.",
        "shape": "Single username value.",
        "example": "EXAMPLE\\alice",
        "validation": [
            "Leave empty to use the current context.",
        ],
        "modal_display_name": "Username",
        "placeholder": "EXAMPLE\\alice",
    },
    {
        "name": "password",
        "required": False,
        "description": "Optional password for the supplied username.",
        "shape": "Single password string.",
        "example": "Passw0rd!",
        "validation": [
            "Leave empty when no password is needed.",
        ],
        "modal_display_name": "Password",
        "placeholder": "Passw0rd!",
    },
    {
        "name": "device",
        "required": False,
        "description": "Optional device name like Z or Z:.",
        "shape": "Drive letter mapping.",
        "example": "Z:",
        "validation": [
            "Leave empty to avoid creating a device mapping.",
            "Must look like X or X:.",
        ],
        "modal_display_name": "Device",
        "placeholder": "Z:",
    },
    {
        "name": "persist",
        "required": False,
        "description": "Persist the mapping.",
        "shape": "Boolean flag.",
        "example": "true",
        "validation": [
            "Accepted true values: 1, true, yes, y, on.",
            "Accepted false values: empty, 0, false, no, n, off.",
        ],
        "modal_display_name": "Persist",
        "placeholder": "true",
    },
    {
        "name": "require_privacy",
        "required": False,
        "description": "Request encrypted SMB for the mapping.",
        "shape": "Boolean flag.",
        "example": "true",
        "validation": [
            "Accepted true values: 1, true, yes, y, on.",
            "Accepted false values: empty, 0, false, no, n, off.",
        ],
        "modal_display_name": "Require Privacy",
        "placeholder": "true",
    }
]
DEFAULT_TEMPLATE = Path(__file__).resolve().parents[1] / "netuse" / "entry.c"
COMMON_INCLUDE_DIR = (
    Path(__file__).resolve().parents[2]
    / "shared" / "common"
)


def normalize_share(value: str) -> str:
    return normalize_unc_share(value, label="share")


def normalize_optional_text(value: str | None, label: str) -> str:
    return normalize_optional_ascii_text(value, label)


def normalize_device(value: str | None) -> str:
    return normalize_device_name(value, label="device")


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
    parser.add_argument("share", help="UNC share like \\\\HOST\\Share.")
    parser.add_argument("username", nargs="?", default="", help="Optional username.")
    parser.add_argument("password", nargs="?", default="", help="Optional password.")
    parser.add_argument("device", nargs="?", default="", help="Optional device name like Z or Z:.")
    parser.add_argument("persist", nargs="?", default="", help="Optional persist flag.")
    parser.add_argument("require_privacy", nargs="?", default="", help="Optional require-privacy flag.")


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    share = normalize_share(args.share)
    username = normalize_optional_text(args.username, "username")
    password = normalize_optional_text(args.password, "password")
    device = normalize_device(args.device)
    persist = normalize_optional_boolish(args.persist, label="persist")
    require_privacy = normalize_optional_boolish(args.require_privacy, label="require_privacy")

    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_CMD__": "1",
            "__NANO_TARGET__": "",
            "__NANO_SHARE_NAME__": c_wide_string_literal(share),
            "__NANO_USERNAME__": c_wide_string_literal(username),
            "__NANO_PASSWORD__": c_wide_string_literal(password),
            "__NANO_DEVICE_NAME__": c_wide_string_literal(device),
            "__NANO_PERSIST__": "1" if persist else "0",
            "__NANO_REQUIRE_PRIVACY__": "1" if require_privacy else "0",
            "__NANO_FORCE__": "0",
        },
        "metadata": {
            "share": share,
            "username": username,
            "device": device,
            "persist": persist,
            "require_privacy": require_privacy,
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
        print(f"share={plan['metadata']['share']}")
        print(f"username={plan['metadata']['username']}")
        print(f"device={plan['metadata']['device']}")
        print(f"persist={plan['metadata']['persist']}")
        print(f"require_privacy={plan['metadata']['require_privacy']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
