from __future__ import annotations

import argparse
from pathlib import Path


NAME = "findLoadedModule"
DESCRIPTION = "Find processes loading a module name fragment, optionally limited to a process name fragment."
VARIABLES = [
    {
        "name": "modulepart",
        "required": True,
        "description": "Required module name fragment to search for.",
    },
    {
        "name": "procnamepart",
        "required": False,
        "description": "Optional process name fragment to limit the search.",
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


def normalize_modulepart(value: str) -> str:
    modulepart = ensure_ascii(ensure_no_nul(value, "modulepart").strip(), "modulepart")
    if not modulepart:
        raise ValueError("modulepart is required.")
    return modulepart


def normalize_procnamepart(value: str) -> str:
    return ensure_ascii(ensure_no_nul(value, "procnamepart").strip(), "procnamepart")


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
        "modulepart",
        help="Required module name fragment to search for.",
    )
    parser.add_argument(
        "procnamepart",
        nargs="?",
        default="",
        help="Optional process name fragment to limit the search.",
    )


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    modulepart = normalize_modulepart(args.modulepart)
    procnamepart = normalize_procnamepart(args.procnamepart)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_MODULEPART__": c_string_literal(modulepart),
            "__NANO_PROCNAMEPART__": c_string_literal(procnamepart),
        },
        "metadata": {
            "final_modulepart": modulepart,
            "final_procnamepart": procnamepart,
            "filters_process_name": procnamepart != "",
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
        print(f"final_modulepart={plan['metadata']['final_modulepart']}")
        print(f"final_procnamepart={plan['metadata']['final_procnamepart']}")
        print(f"filters_process_name={plan['metadata']['filters_process_name']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
