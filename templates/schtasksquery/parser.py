from __future__ import annotations

import argparse
from pathlib import Path


NAME = "schtasksquery"
DESCRIPTION = "Query a scheduled task on the local or a remote host."
VARIABLES = [
    {
        "name": "server",
        "required": False,
        "description": "Optional target server host name.",
        "shape": "Single bare host name or FQDN.",
        "example": "WORKSTATION",
        "validation": [
            "Leave empty to target the local host.",
            "Must not be a URL, UNC path, or include a port.",
        ],
        "modal_display_name": "Server",
        "placeholder": "WORKSTATION",
    },
    {
        "name": "taskpath",
        "required": True,
        "description": "Full scheduled task path, such as \\Microsoft\\Windows\\MUI\\LpRemove.",
        "shape": "Full scheduled task path starting with a backslash.",
        "example": "\\Microsoft\\Windows\\MUI\\LpRemove",
        "validation": [
            "Must start with a backslash.",
            "Must use backslashes, not forward slashes.",
        ],
        "modal_display_name": "Task Path",
        "placeholder": "\\Microsoft\\Windows\\MUI\\LpRemove",
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


def normalize_server(value: str) -> str:
    server = ensure_no_nul(value, "server").strip()
    if not server:
        return ""
    lower = server.lower()
    if lower.startswith(("http://", "https://", "ldap://", "ldaps://")):
        raise ValueError("server should be a host name, not a URL.")
    if server.startswith("\\\\"):
        bare_server = server[2:]
    else:
        bare_server = server
    bare_server = bare_server.strip()
    if not bare_server:
        raise ValueError("server value is not usable after normalization. Provide a host like WORKSTATION or leave it empty for the local host.")
    if "/" in bare_server or "\\" in bare_server:
        raise ValueError("server must be a single host value. Do not pass a UNC path or share name.")
    if ":" in bare_server:
        raise ValueError("server should not include a port. Pass just the host name.")
    if any(ch.isspace() for ch in bare_server):
        raise ValueError("server must not contain spaces. Pass a host name or FQDN only.")
    if len(bare_server) > 255:
        raise ValueError("server is too long to be a viable host name. Keep it to 255 characters or fewer.")
    return bare_server


def normalize_taskpath(value: str) -> str:
    taskpath = ensure_no_nul(value, "taskpath").strip()
    if not taskpath:
        raise ValueError("taskpath is required. Pass a full task path like \\Microsoft\\Windows\\MUI\\LpRemove.")
    if not taskpath.startswith("\\"):
        raise ValueError("taskpath must be a full task path that starts with a backslash.")
    if "/" in taskpath:
        raise ValueError("taskpath must use backslashes, not forward slashes.")
    parts = [part for part in taskpath.split("\\") if part]
    if not parts:
        raise ValueError("taskpath must include at least one task name component.")
    taskpath = "\\" + "\\".join(parts)
    if len(taskpath) > 1024:
        raise ValueError("taskpath is too long. Keep it to 1024 characters or fewer.")
    return taskpath


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
        "server",
        nargs="?",
        default="",
        help="Optional server name when also supplying a task path. If omitted, the first value is treated as the task path.",
    )
    parser.add_argument(
        "taskpath",
        nargs="?",
        default="",
        help="Full scheduled task path. Required unless the first positional value is already the task path.",
    )


def split_inputs(args: argparse.Namespace) -> tuple[str, str]:
    if args.taskpath:
        return args.server, args.taskpath
    return "", args.server


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    raw_server, raw_taskpath = split_inputs(args)
    server = normalize_server(raw_server)
    taskpath = normalize_taskpath(raw_taskpath)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_SERVER__": server,
            "__NANO_TASKPATH__": taskpath,
        },
        "metadata": {
            "final_server": server,
            "final_taskpath": taskpath,
            "targets_local_host": server == "",
        },
        "build": {
            "include_dirs": [str(COMMON_INCLUDE_DIR)],
            "cflags": ["-fno-jump-tables", "-Os", "-c", "-DBOF"],
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
        print(f"final_server={plan['metadata']['final_server']}")
        print(f"final_taskpath={plan['metadata']['final_taskpath']}")
        print(f"targets_local_host={plan['metadata']['targets_local_host']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
