from __future__ import annotations

import argparse
from pathlib import Path

from nano_bofs.input_validation import normalize_domain_like


NAME = "adcs_enum"
DESCRIPTION = "Enumerate certificate authorities and templates in AD CS."
VARIABLES = [
    {
        "name": "domain",
        "required": False,
        "description": "Optional AD domain scope for CA enumeration.",
        "shape": "Single DNS or NetBIOS domain value. Omit it to resolve the current ComputerNameDnsDomain at runtime.",
        "example": "example.test",
        "modal_display_name": "Domain",
        "mythic_parameter_type": "String",
        "placeholder": "example.test",
        "validation": [
            "Rejects URLs, UNC/path values, ports, spaces, and overlong values.",
            "Must be ASCII-safe for this template.",
        ],
    }
]
VALIDATION_RULES = [
    "This template embeds the domain at build time; the generated BOF takes no runtime arguments.",
    "When domain is omitted, the BOF resolves ComputerNameDnsDomain at runtime and exits cleanly if that lookup fails.",
    "Explicit domain values are passed through to CAEnumFirstCA with CA_FLAG_SCOPE_DNS.",
]
INPUT_NOTES = [
    "Prefer a DNS-style domain such as corp.local when you want explicit scope.",
    "A fake or unreachable domain will return the underlying CAEnumFirstCA HRESULT during BOF execution.",
]
DEFAULT_TEMPLATE = Path(__file__).with_name("entry.c")
COMMON_INCLUDE_DIR = Path(__file__).resolve().parents[2] / "shared" / "common"
TEMPLATE_DIR = Path(__file__).resolve().parent

def normalize_domain(value: str | None) -> str | None:
    if value is None:
        return None
    domain = normalize_domain_like(value, label="domain", allow_empty=True)
    return domain or None


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
    parser.add_argument("domain", nargs="?", default=None, help="Optional domain. Defaults to the current domain.")


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    domain = normalize_domain(args.domain)

    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": "entry.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_DOMAIN__": c_wide_string_literal(domain or ""),
            "__NANO_USE_CURRENT_DOMAIN__": "1" if domain is None else "0",
        },
        "metadata": {
            "domain": domain,
            "use_current_domain": domain is None,
        },
        "build": {
            "include_dirs": [str(COMMON_INCLUDE_DIR), str(TEMPLATE_DIR)],
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
