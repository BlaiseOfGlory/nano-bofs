from __future__ import annotations

import argparse
from pathlib import Path

from nano_bofs.input_validation import normalize_domain_like


NAME = "netgroup"
DESCRIPTION = "List members of the specified domain group."
VARIABLES = [
    {
        "name": "groupname",
        "required": True,
        "description": "Domain group name to enumerate.",
        "shape": "Single domain group name.",
        "example": "Domain Admins",
        "validation": [
            "Must not be empty.",
            "Keep it to 255 characters or fewer.",
        ],
        "modal_display_name": "Group Name",
        "placeholder": "Domain Admins",
    },
    {
        "name": "domain",
        "required": False,
        "description": "Optional AD domain name.",
        "shape": "Single DNS or NetBIOS domain value.",
        "example": "corp.local",
        "validation": [
            "Leave empty to use runtime default-domain resolution.",
            "Must not be a URL, UNC path, or include a port.",
        ],
        "modal_display_name": "Domain",
        "placeholder": "corp.local",
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


def normalize_groupname(value: str) -> str:
    groupname = ensure_no_nul(value, "groupname").strip()
    if not groupname:
        raise ValueError("groupname is required. Pass a domain group like \"Domain Admins\".")
    if len(groupname) > 255:
        raise ValueError("groupname is too long. Keep it to 255 characters or fewer.")
    return groupname


def normalize_domain(value: str) -> str:
    return normalize_domain_like(value, label="domain", allow_empty=True)


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
    parser.add_argument("groupname", help="Domain group name to enumerate.")
    parser.add_argument(
        "domain",
        nargs="?",
        default="",
        help="Optional domain name. Leave empty to preserve runtime default-domain resolution.",
    )


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    groupname = normalize_groupname(args.groupname)
    domain = normalize_domain(args.domain)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_GROUP__": groupname,
            "__NANO_DOMAIN__": domain,
        },
        "metadata": {
            "final_groupname": groupname,
            "final_domain": domain,
            "uses_runtime_default_domain": domain == "",
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
        print(f"final_groupname={plan['metadata']['final_groupname']}")
        print(f"final_domain={plan['metadata']['final_domain']}")
        print(f"uses_runtime_default_domain={plan['metadata']['uses_runtime_default_domain']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
