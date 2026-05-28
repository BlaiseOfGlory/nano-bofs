from __future__ import annotations

import argparse
from pathlib import Path


NAME = "netstat"
DESCRIPTION = "Display local IPv4 and IPv6 TCP and UDP endpoints."
VARIABLES = [
    {
        "name": "filters",
        "required": False,
        "description": "Optional endpoint filters: ipv4, ipv6, tcp, udp.",
        "shape": "One or more filters separated by spaces or commas.",
        "example": "ipv4 tcp",
        "choices": ["ipv4", "ipv6", "tcp", "udp"],
        "validation": [
            "Supported values: ipv4, ipv6, tcp, udp.",
            "Leave empty to show all IPv4 and IPv6 TCP and UDP endpoints.",
        ],
        "modal_display_name": "Filters",
        "placeholder": "ipv4 tcp",
    }
]
DEFAULT_TEMPLATE = Path(__file__).with_name("entry.c")
COMMON_INCLUDE_DIR = (
    Path(__file__).resolve().parents[2]
    / "shared" / "common"
)

TCP4_MASK = 0x0001
TCP6_MASK = 0x0010
UDP4_MASK = 0x0100
UDP6_MASK = 0x1000
DEFAULT_MASK = TCP4_MASK | TCP6_MASK | UDP4_MASK | UDP6_MASK
VALID_FILTERS = ("ipv4", "ipv6", "tcp", "udp")


def resolve_choice_mask(filters: list[str]) -> int:
    if not filters:
        return DEFAULT_MASK

    selected = set(filters)
    mask = 0

    if "tcp" in selected:
        mask |= TCP4_MASK | TCP6_MASK
    if "udp" in selected:
        mask |= UDP4_MASK | UDP6_MASK

    if "ipv4" in selected:
        if "tcp" in selected or "udp" in selected:
            if "tcp" in selected:
                mask &= ~TCP6_MASK
            if "udp" in selected:
                mask &= ~UDP6_MASK
        else:
            mask |= TCP4_MASK | UDP4_MASK

    if "ipv6" in selected:
        if "tcp" in selected or "udp" in selected:
            if "tcp" in selected:
                mask &= ~TCP4_MASK
            if "udp" in selected:
                mask &= ~UDP4_MASK
        else:
            mask |= TCP6_MASK | UDP6_MASK

    if "ipv4" not in selected and "ipv6" not in selected and ("tcp" in selected or "udp" in selected):
        return mask

    if "tcp" not in selected and "udp" not in selected and ("ipv4" in selected or "ipv6" in selected):
        return mask

    if mask == 0:
        raise ValueError("filter combination produced an empty endpoint set.")

    return mask


def validate_filters(filters: list[str]) -> list[str]:
    normalized: list[str] = []
    for item in filters:
        for piece in item.replace(",", " ").split():
            if piece:
                normalized.append(piece)
    filters = normalized
    invalid = [item for item in filters if item not in VALID_FILTERS]
    if invalid:
        supported = ", ".join(VALID_FILTERS)
        bad = ", ".join(invalid)
        raise ValueError(f"unsupported filters: {bad}. Supported values: {supported}.")
    return filters


def render_source(template: str, placeholders: dict[str, str]) -> str:
    rendered = template
    for key, value in placeholders.items():
        if key not in rendered:
            raise ValueError(f"template is missing the required placeholder {key}.")
        rendered = rendered.replace(key, value)
    return rendered


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "filters",
        nargs="*",
        help="Optional filters. Examples: ipv4 tcp, udp, ipv6.",
    )


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    filters = validate_filters(list(args.filters))
    choice_mask = resolve_choice_mask(filters)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_CHOICE_MASK__": f"0x{choice_mask:04x}",
        },
        "metadata": {
            "filters": filters,
            "choice_mask": choice_mask,
            "defaults_to_all": not filters,
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
        print(f"filters={plan['metadata']['filters']}")
        print(f"choice_mask={plan['metadata']['choice_mask']}")
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
