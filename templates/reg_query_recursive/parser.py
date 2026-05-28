from __future__ import annotations

import argparse
from pathlib import Path

from nano_bofs.input_validation import (
    REGISTRY_HIVE_VALUES,
    normalize_host_like,
    normalize_optional_ascii_text,
    normalize_registry_hive,
    normalize_registry_path,
)


NAME = "reg_query_recursive"
DESCRIPTION = "Recursively enumerate a registry key on the local host or an optional remote host."
VARIABLES = [
    {
        "name": "hostname",
        "required": False,
        "description": "Optional target host name. Leave empty to query the local host.",
    },
    {
        "name": "hive",
        "required": True,
        "description": "Registry hive: HKLM, HKCU, HKU, or HKCR.",
    },
    {
        "name": "path",
        "required": True,
        "description": "Registry path relative to the hive.",
    },
]
MYTHIC_VARIABLES = [
    {
        "name": "hostname",
        "required": False,
        "description": "Optional target host name. Leave empty to query the local host.",
        "shape": "Single host name.",
        "example": "DC01",
        "validation": [
            "Leave empty for local mode.",
            "Do not include leading backslashes.",
        ],
        "placeholder": "DC01",
    },
    {
        "name": "hive",
        "required": True,
        "description": "Registry hive: HKLM, HKCU, HKU, or HKCR.",
        "shape": "Registry hive name.",
        "example": "HKLM",
        "choices": ["HKLM", "HKCU", "HKU", "HKCR"],
        "placeholder": "HKLM",
    },
    {
        "name": "path",
        "required": True,
        "description": "Registry path relative to the hive.",
        "shape": "Registry path without the hive prefix.",
        "example": "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion",
        "validation": [
            "Do not repeat the hive prefix in the path.",
        ],
        "placeholder": "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion",
    },
]
INPUT_NOTES = [
    "Leave `hostname` empty to query the local host.",
    "This variant always recurses through the target key.",
]
DEFAULT_TEMPLATE = Path(__file__).resolve().parents[1] / "reg_query" / "entry.c"
COMMON_INCLUDE_DIR = (
    Path(__file__).resolve().parents[2]
    / "shared" / "common"
)

def normalize_hostname(value: str) -> str:
    hostname = normalize_host_like(value, label="hostname", allow_empty=True)
    if not hostname:
        return ""
    return f"\\\\{hostname}"


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


def resolve_cli(tokens: list[str]) -> tuple[str, str, int, str]:
    if len(tokens) < 2 or len(tokens) > 3:
        raise ValueError("usage: reg_query_recursive [hostname] <hive> <path>")

    first = normalize_optional_ascii_text(tokens[0], "first argument").upper()
    if first in REGISTRY_HIVE_VALUES:
        hostname = ""
        hive_name, hive_value = normalize_registry_hive(tokens[0])
        path = normalize_registry_path(tokens[1])
        if len(tokens) == 3:
            raise ValueError("too many arguments for local mode. Use: reg_query_recursive <hive> <path>")
    else:
        if len(tokens) != 3:
            raise ValueError("remote mode requires: reg_query_recursive <hostname> <hive> <path>")
        hostname = normalize_hostname(tokens[0])
        hive_name, hive_value = normalize_registry_hive(tokens[1])
        path = normalize_registry_path(tokens[2])

    return hostname, hive_name, hive_value, path


def _mythic_text(raw_inputs: dict[str, object], name: str) -> str:
    value = raw_inputs.get(name)
    if value is None:
        return ""
    return str(value)


def parse_mythic_inputs(raw_inputs: dict[str, object]) -> argparse.Namespace:
    hostname = normalize_host_like(_mythic_text(raw_inputs, "hostname"), label="hostname", allow_empty=True)
    hive_name, _ = normalize_registry_hive(_mythic_text(raw_inputs, "hive"))
    path = normalize_registry_path(_mythic_text(raw_inputs, "path"))

    arguments = [hive_name, path]
    if hostname:
        arguments = [hostname, hive_name, path]
    return argparse.Namespace(arguments=arguments)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "arguments",
        nargs="+",
        help="Use either <hive> <path> or <hostname> <hive> <path>.",
    )


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    hostname, hive_name, hive_value, path = resolve_cli(list(args.arguments))
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_HOSTNAME__": c_string_literal(hostname),
            "__NANO_HIVE__": str(hive_value),
            "__NANO_PATH__": c_string_literal(path),
            "__NANO_VALUE__": "",
            "__NANO_RECURSIVE__": "1",
        },
        "metadata": {
            "final_hostname": hostname,
            "final_hive_name": hive_name,
            "final_hive_value": hive_value,
            "final_path": path,
            "targets_local_host": hostname == "",
            "recursive": True,
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
        print(f"final_hive_name={plan['metadata']['final_hive_name']}")
        print(f"final_hive_value={plan['metadata']['final_hive_value']}")
        print(f"final_path={plan['metadata']['final_path']}")
        print(f"targets_local_host={plan['metadata']['targets_local_host']}")
        print(f"recursive={plan['metadata']['recursive']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
