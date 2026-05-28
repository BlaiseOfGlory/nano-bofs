from __future__ import annotations

from pathlib import Path

from nano_bofs.upstream_zero_arg import COMMON_INCLUDE_DIR
from nano_bofs.upstream_zero_arg import add_no_arguments
from nano_bofs.upstream_zero_arg import parse_no_args
from nano_bofs.upstream_zero_arg import render_upstream_plan
from nano_bofs.upstream_zero_arg import zero_arg_build_plan


NAME = "ipconfig"
DESCRIPTION = "Display host and interface network configuration."
VARIABLES: list[dict[str, object]] = []
UPSTREAM_DIR = Path(__file__).resolve().parents[2] / "shared" / "upstream" / "SA" / NAME


def add_arguments(parser) -> None:
    add_no_arguments(parser)


def build_plan(args) -> dict[str, object]:
    return zero_arg_build_plan(NAME, UPSTREAM_DIR / "entry.c", include_dirs=[COMMON_INCLUDE_DIR])


def render_plan(plan: dict[str, object]) -> str:
    return render_upstream_plan(plan)


def parse_args():
    return parse_no_args(DESCRIPTION)


def main() -> None:
    print(render_plan(build_plan(parse_args())))


if __name__ == "__main__":
    main()
