from __future__ import annotations

import argparse
from pathlib import Path


NAME = "mythicSmoke"
DESCRIPTION = "Print a simple success message to verify COFF execution through Mythic."
VARIABLES: list[dict[str, object]] = []
DEFAULT_TEMPLATE = Path(__file__).with_name("entry.c")
COMMON_INCLUDE_DIR = (
    Path(__file__).resolve().parents[2]
    / "shared" / "common"
)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    return None


def build_plan(args: argparse.Namespace) -> dict[str, object]:
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {},
        "metadata": {
            "test_name": "mythic-coff-smoke",
            "expected_output": [
                "[nano-bofs] Mythic COFF test OK",
                "[nano-bofs] Argument buffer length: 0",
            ],
        },
        "build": {
            "include_dirs": [str(COMMON_INCLUDE_DIR)],
            "cflags": ["-Os", "-c", "-DBOF"],
        },
    }


def render_plan(plan: dict[str, object]) -> str:
    return Path(plan["template_path"]).read_text(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    add_arguments(parser)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plan = build_plan(args)
    print(render_plan(plan))


if __name__ == "__main__":
    main()
