from __future__ import annotations

import argparse
from pathlib import Path


NAME = "netview"
DESCRIPTION = "List reachable computers in the current or specified domain."
MYTHIC_ENABLED = False
VARIABLES = [
    {
        "name": "domain",
        "required": False,
        "description": "Optional AD domain name.",
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


def normalize_domain(value: str) -> str:
    domain = ensure_no_nul(value, "domain").strip()
    if domain.startswith("\\\\"):
        domain = domain[2:]
    if not domain:
        return ""
    lower = domain.lower()
    if lower.startswith("ldap://") or lower.startswith("ldaps://"):
        raise ValueError("domain should be a plain AD domain value, not an LDAP URL. Try corp.local or leave it empty for runtime resolution.")
    if "/" in domain or "\\" in domain:
        raise ValueError("domain must be a single domain value. Do not pass a path or UNC string.")
    if ":" in domain:
        raise ValueError("domain should not include a port. Pass just the domain name.")
    if any(ch.isspace() for ch in domain):
        raise ValueError("domain must not contain spaces. Pass a DNS or NetBIOS domain value only.")
    if len(domain) > 255:
        raise ValueError("domain is too long to be a viable AD domain value. Keep it to 255 characters or fewer.")
    return domain


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
        "domain",
        nargs="?",
        default="",
        help="Optional domain name. Leave empty to preserve runtime default-domain resolution.",
    )


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    domain = normalize_domain(args.domain)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_DOMAIN__": domain,
        },
        "metadata": {
            "final_domain": domain,
            "uses_runtime_default_domain": domain == "",
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
        print(f"final_domain={plan['metadata']['final_domain']}")
        print(f"uses_runtime_default_domain={plan['metadata']['uses_runtime_default_domain']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
