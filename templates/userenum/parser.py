from __future__ import annotations

import argparse
from pathlib import Path


NAME = "userenum"
DESCRIPTION = "Enumerate domain or local user accounts."
VARIABLES: list[dict[str, object]] = []
DEFAULT_TEMPLATE = Path(__file__).resolve().parents[1] / "netuserenum" / "entry.c"
COMMON_INCLUDE_DIR = (
    Path(__file__).resolve().parents[2]
    / "shared" / "common"
)


def add_arguments(parser) -> None:
    return None


def build_plan(args) -> dict[str, object]:
    (void := args)
    return {
        "template_path": DEFAULT_TEMPLATE,
        "source_name": f"{NAME}.c",
        "artifact_basename": NAME,
        "placeholders": {
            "__NANO_USEDOMAIN__": "0",
            "__NANO_USERFILTER__": "1",
        },
        "metadata": {
            "final_scope": "local",
            "final_filter": "all",
            "final_filter_value": 1,
            "usedomain": 0,
        },
        "build": {
            "include_dirs": [str(COMMON_INCLUDE_DIR)],
            "cflags": ["-Os", "-c", "-DBOF"],
        },
    }


def render_plan(plan: dict[str, object]) -> str:
    template = Path(plan["template_path"]).read_text(encoding="utf-8")
    rendered = template
    for key, value in dict(plan["placeholders"]).items():
        if key not in rendered:
            raise ValueError(f"template is missing the required placeholder {key}.")
        rendered = rendered.replace(key, value)
    return rendered


def parse_args():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    add_arguments(parser)
    return parser.parse_args()


def main() -> None:
    plan = build_plan(parse_args())
    print(render_plan(plan))
    print(f"final_scope={plan['metadata']['final_scope']}")
    print(f"final_filter={plan['metadata']['final_filter']}")
    print(f"final_filter_value={plan['metadata']['final_filter_value']}")
    print(f"usedomain={plan['metadata']['usedomain']}")


if __name__ == "__main__":
    main()
