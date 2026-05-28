from __future__ import annotations

import argparse
from pathlib import Path

from nano_bofs.input_validation import (
    normalize_device_name,
    normalize_optional_boolish,
    normalize_optional_ascii_text,
    normalize_unc_share,
)


NAME = "netuse"
DESCRIPTION = "Manage network-use connections."
VARIABLES = [
    {
        "name": "command",
        "required": True,
        "description": "Subcommand: add, list, or delete.",
    }
]
MYTHIC_VARIABLES = [
    {
        "name": "command",
        "required": True,
        "description": "Subcommand: add, list, or delete.",
        "shape": "One of add, list, or delete.",
        "example": "list",
        "choices": ["list", "add", "delete"],
        "mythic_default_value": "list",
        "validation": [
            "Use add with share inputs.",
            "Use list with an optional target.",
            "Use delete with target and optional persist/force flags.",
        ],
    },
    {
        "name": "share",
        "required": False,
        "description": "UNC share like \\\\HOST\\Share for the add subcommand.",
        "shape": "UNC share path.",
        "example": "\\\\192.0.2.10\\IPC$",
        "validation": [
            "Required when command is add.",
        ],
        "placeholder": "\\\\192.0.2.10\\IPC$",
    },
    {
        "name": "username",
        "required": False,
        "description": "Optional username for the add subcommand.",
        "shape": "Single username value.",
        "example": "EXAMPLE\\alice",
    },
    {
        "name": "password",
        "required": False,
        "description": "Optional password for the add subcommand.",
        "shape": "Single password string.",
        "example": "Passw0rd!",
    },
    {
        "name": "device",
        "required": False,
        "description": "Optional device mapping for the add subcommand.",
        "shape": "Drive letter mapping.",
        "example": "Z:",
        "validation": [
            "Must look like X or X: when supplied.",
        ],
    },
    {
        "name": "persist",
        "required": False,
        "description": "Optional persist flag for add or delete.",
        "shape": "Boolean flag.",
        "example": "true",
        "validation": [
            "Accepted true values: 1, true, yes, y, on.",
            "Accepted false values: empty, 0, false, no, n, off.",
        ],
    },
    {
        "name": "require_privacy",
        "required": False,
        "description": "Optional encrypted SMB flag for the add subcommand.",
        "shape": "Boolean flag.",
        "example": "true",
        "validation": [
            "Accepted true values: 1, true, yes, y, on.",
            "Accepted false values: empty, 0, false, no, n, off.",
        ],
    },
    {
        "name": "target",
        "required": False,
        "description": "Optional target for list or required target for delete.",
        "shape": "Drive letter or UNC path.",
        "example": "\\\\192.0.2.10\\IPC$",
        "validation": [
            "Required when command is delete.",
            "Optional when command is list.",
        ],
        "placeholder": "\\\\192.0.2.10\\IPC$",
    },
    {
        "name": "force",
        "required": False,
        "description": "Optional force flag for the delete subcommand.",
        "shape": "Boolean flag.",
        "example": "true",
        "validation": [
            "Accepted true values: 1, true, yes, y, on.",
            "Accepted false values: empty, 0, false, no, n, off.",
        ],
    },
]
INPUT_NOTES = [
    "For command=`add`, supply `share` and any optional username, password, device, persist, or require_privacy values.",
    "For command=`list`, omit everything except an optional `target`.",
    "For command=`delete`, supply `target` and optional `persist` or `force` values.",
]
DEFAULT_TEMPLATE = Path(__file__).with_name("entry.c")
COMMON_INCLUDE_DIR = (
    Path(__file__).resolve().parents[2]
    / "shared" / "common"
)

CMD_ADD = 1
CMD_LIST = 2
CMD_DELETE = 3


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


def normalize_share(value: str) -> str:
    return normalize_unc_share(value, label="share")


def normalize_optional_text(value: str | None, label: str) -> str:
    return normalize_optional_ascii_text(value, label)


def normalize_device(value: str | None) -> str:
    return normalize_device_name(value, label="device")


def normalize_target(value: str | None) -> str:
    if value is None:
        return ""
    target = normalize_optional_ascii_text(value, "target")
    if not target:
        return ""
    if len(target) == 1:
        if not target.isalpha():
            raise ValueError("single-character targets must be drive letters.")
        return target.upper() + ":"
    if len(target) == 2 and target[0].isalpha() and target[1] == ":":
        return target.upper()
    if len(target) > 2:
        return target if target.startswith("\\\\") else "\\\\" + target
    return target


def _mythic_text(raw_inputs: dict[str, object], name: str) -> str:
    value = raw_inputs.get(name)
    if value is None:
        return ""
    return str(value)


def parse_mythic_inputs(raw_inputs: dict[str, object]) -> argparse.Namespace:
    command = normalize_optional_ascii_text(_mythic_text(raw_inputs, "command"), "command").lower()
    if command not in {"add", "list", "delete"}:
        raise ValueError("command must be one of add, list, or delete.")

    if command == "add":
        share = normalize_share(_mythic_text(raw_inputs, "share"))
        username = normalize_optional_text(_mythic_text(raw_inputs, "username"), "username")
        password = normalize_optional_text(_mythic_text(raw_inputs, "password"), "password")
        device = normalize_device(_mythic_text(raw_inputs, "device"))
        persist = normalize_optional_boolish(_mythic_text(raw_inputs, "persist"), label="persist")
        require_privacy = normalize_optional_boolish(
            _mythic_text(raw_inputs, "require_privacy"),
            label="require_privacy",
        )
        return argparse.Namespace(
            command=command,
            share=share,
            username=username,
            password=password,
            device=device,
            persist=persist,
            require_privacy=require_privacy,
            target="",
            force=False,
        )

    target = normalize_target(_mythic_text(raw_inputs, "target"))
    persist = normalize_optional_boolish(_mythic_text(raw_inputs, "persist"), label="persist")
    if command == "list":
        return argparse.Namespace(
            command=command,
            share="",
            username="",
            password="",
            device="",
            persist=False,
            require_privacy=False,
            target=target,
            force=False,
        )

    if not target:
        raise ValueError("target is required when command is delete.")
    force = normalize_optional_boolish(_mythic_text(raw_inputs, "force"), label="force")
    return argparse.Namespace(
        command=command,
        share="",
        username="",
        password="",
        device="",
        persist=persist,
        require_privacy=False,
        target=target,
        force=force,
    )


def add_arguments(parser: argparse.ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Create a new network-use connection.")
    add_parser.add_argument("share", help="UNC share like \\\\HOST\\Share.")
    add_parser.add_argument("username", nargs="?", default="", help="Optional username.")
    add_parser.add_argument("password", nargs="?", default="", help="Optional password.")
    add_parser.add_argument("--device", dest="device", default="", help="Optional device name like Z or Z:.")
    add_parser.add_argument("--persist", action="store_true", help="Persist the mapping.")
    add_parser.add_argument("--require-privacy", action="store_true", help="Request encrypted SMB.")

    list_parser = subparsers.add_parser("list", help="List current network-use connections.")
    list_parser.add_argument("target", nargs="?", default="", help="Optional drive letter or remote name.")

    delete_parser = subparsers.add_parser("delete", help="Delete a network-use connection.")
    delete_parser.add_argument("target", help="Drive letter or remote name.")
    delete_parser.add_argument("--persist", action="store_true", help="Delete a persisted mapping.")
    delete_parser.add_argument("--force", action="store_true", help="Force deletion.")


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    placeholders = {
        "__NANO_CMD__": "0",
        "__NANO_TARGET__": "",
        "__NANO_SHARE_NAME__": "",
        "__NANO_USERNAME__": "",
        "__NANO_PASSWORD__": "",
        "__NANO_DEVICE_NAME__": "",
        "__NANO_PERSIST__": "0",
        "__NANO_REQUIRE_PRIVACY__": "0",
        "__NANO_FORCE__": "0",
    }
    metadata: dict[str, object] = {"command": args.command}

    if args.command == "add":
        share = normalize_share(args.share)
        username = normalize_optional_text(args.username, "username")
        password = normalize_optional_text(args.password, "password")
        device = normalize_device(args.device)
        placeholders.update(
            {
                "__NANO_CMD__": str(CMD_ADD),
                "__NANO_SHARE_NAME__": c_wide_string_literal(share),
                "__NANO_USERNAME__": c_wide_string_literal(username),
                "__NANO_PASSWORD__": c_wide_string_literal(password),
                "__NANO_DEVICE_NAME__": c_wide_string_literal(device),
                "__NANO_PERSIST__": "1" if args.persist else "0",
                "__NANO_REQUIRE_PRIVACY__": "1" if args.require_privacy else "0",
            }
        )
        metadata.update({"share": share, "username": username, "device": device, "persist": args.persist, "require_privacy": args.require_privacy})
    elif args.command == "list":
        target = normalize_target(args.target)
        placeholders.update(
            {
                "__NANO_CMD__": str(CMD_LIST),
                "__NANO_TARGET__": c_wide_string_literal(target),
            }
        )
        metadata.update({"target": target})
    elif args.command == "delete":
        target = normalize_target(args.target)
        placeholders.update(
            {
                "__NANO_CMD__": str(CMD_DELETE),
                "__NANO_TARGET__": c_wide_string_literal(target),
                "__NANO_PERSIST__": "1" if args.persist else "0",
                "__NANO_FORCE__": "1" if args.force else "0",
            }
        )
        metadata.update({"target": target, "persist": args.persist, "force": args.force})
    else:
        raise ValueError("unsupported command")

    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": placeholders,
        "metadata": metadata,
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
