from __future__ import annotations

import argparse
from pathlib import Path

from nano_bofs.input_validation import normalize_host_like
from nano_bofs.input_validation import normalize_int_range
from nano_bofs.input_validation import normalize_optional_ascii_text


NAME = "probe"
DESCRIPTION = "Check whether a TCP port is open on a target host."
VARIABLES = [
    {
        "name": "host",
        "required": True,
        "description": "Target host name or IPv4 address.",
        "shape": "Single hostname or IPv4 literal.",
        "example": "dc01.example.test",
        "modal_display_name": "Host",
        "mythic_parameter_type": "String",
        "placeholder": "dc01.example.test",
        "validation": [
            "Must not contain spaces.",
            "Must not be a URL or path.",
            "Must not contain a NUL byte.",
        ],
    },
    {
        "name": "port",
        "required": True,
        "description": "Target TCP port.",
        "shape": "Base-10 integer between 1 and 65535.",
        "example": "445",
        "modal_display_name": "Port",
        "mythic_parameter_type": "Number",
        "placeholder": "445",
        "validation": [
            "Must be a base-10 integer.",
            "Must be between 1 and 65535.",
        ],
    },
    {
        "name": "timeout",
        "required": False,
        "description": "Optional timeout in seconds. Defaults to 5.",
        "shape": "Base-10 integer between 1 and 3600, or 0 to use the default 5 seconds.",
        "example": "10",
        "modal_display_name": "Timeout",
        "mythic_parameter_type": "Number",
        "placeholder": "5",
        "mythic_default_value": 5,
        "validation": [
            "Defaults to 5 when omitted or set to 0.",
            "Must be between 1 and 3600 when non-zero.",
        ],
    },
]
VALIDATION_RULES = [
    "probe validates host, port, and timeout before rendering the BOF source.",
    "The generated BOF takes no runtime arguments because all values are embedded at build time.",
]
INPUT_NOTES = [
    "Use a bare host or IP such as dc01 or 10.0.0.5, not a URL.",
]
DEFAULT_TEMPLATE = Path(__file__).with_name("entry.c")
COMMON_INCLUDE_DIR = (
    Path(__file__).resolve().parents[2]
    / "shared" / "common"
)

def normalize_host(value: str) -> str:
    return normalize_host_like(value, label="host", allow_empty=False)


def normalize_port(value: str) -> int:
    return normalize_int_range(value, label="port", minimum=1, maximum=65535)


def normalize_timeout(value: str) -> int:
    text = normalize_optional_ascii_text(value, "timeout")
    if not text or text == "0":
        return 5
    return normalize_int_range(text, label="timeout", minimum=1, maximum=3600)


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
        "host",
        help="Target host name or IPv4 address.",
    )
    parser.add_argument(
        "port",
        help="Target TCP port.",
    )
    parser.add_argument(
        "timeout",
        nargs="?",
        default="5",
        help="Optional timeout in seconds. Defaults to 5.",
    )


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    host = normalize_host(args.host)
    port = normalize_port(args.port)
    timeout = normalize_timeout(args.timeout)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_HOST__": c_string_literal(host),
            "__NANO_PORT__": str(port),
            "__NANO_TIMEOUT__": str(timeout),
        },
        "metadata": {
            "final_host": host,
            "final_port": port,
            "final_timeout": timeout,
            "uses_default_timeout": timeout == 5,
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
        print(f"final_host={plan['metadata']['final_host']}")
        print(f"final_port={plan['metadata']['final_port']}")
        print(f"final_timeout={plan['metadata']['final_timeout']}")
        print(f"uses_default_timeout={plan['metadata']['uses_default_timeout']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
