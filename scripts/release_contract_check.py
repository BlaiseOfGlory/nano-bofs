from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IMAGE_REF_PREFIX = "ghcr.io/blaiseofglory/nano_bofs:"


def fail(message: str) -> None:
    raise SystemExit(message)


def read_project_version(path: Path) -> str:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return data["project"]["version"]


def read_builder_values(path: Path) -> tuple[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    semver = None
    icon_path = None

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != "NanoBofs":
            continue
        for item in node.body:
            names = assignment_names(item)
            value = assignment_value(item)
            if not names or value is None:
                continue
            if "semver" in names and isinstance(value, ast.Constant):
                semver = str(value.value)
            if "agent_icon_path" in names:
                icon_path = render_pure_path_expression(value)

    if semver is None:
        fail(f"{path} does not define NanoBofs.semver")
    if icon_path is None:
        fail(f"{path} does not define NanoBofs.agent_icon_path")
    return semver, icon_path


def assignment_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Assign):
        return [target.id for target in node.targets if isinstance(target, ast.Name)]
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [node.target.id]
    return []


def assignment_value(node: ast.AST) -> ast.AST | None:
    if isinstance(node, ast.Assign):
        return node.value
    if isinstance(node, ast.AnnAssign):
        return node.value
    return None


def render_pure_path_expression(node: ast.AST) -> str:
    parts: list[str] = []

    def visit(value: ast.AST) -> None:
        if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Div):
            visit(value.left)
            visit(value.right)
            return
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            parts.append(value.value)
            return
        if isinstance(value, ast.Name) and value.id == "agent_path":
            parts.extend(["nano_bofs_mythic"])
            return

    visit(node)
    if not parts:
        fail("Could not resolve NanoBofs.agent_icon_path")
    return "/".join(parts)


def check_png(path: Path) -> None:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        fail(f"{path} is not a PNG")
    if len(data) < 26:
        fail(f"{path} is too small to be a valid PNG")
    color_type = data[25]
    if color_type not in {4, 6}:
        fail(f"{path} is not an alpha-capable PNG; IHDR color type is {color_type}")


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.splitlines()


def check_tracked_hygiene(files: list[str]) -> None:
    forbidden_exact = {
        ".agents/AGENTS.md",
        "Payload_Type/nano_bofs/rabbitmq_config.json",
    }
    forbidden_suffixes = (
        ".pyc",
        ".log",
    )
    forbidden_prefixes = (
        ".local/",
        ".uv-cache/",
        ".venv-ci/",
        ".wheel-smoke",
        "dist/",
        "build/",
        "out/",
        "Payload_Type/nano_bofs/.nano-bofs-state/",
        "Payload_Type/nano_bofs/.uv-cache/",
        "Payload_Type/nano_bofs/.venv-win/",
    )

    bad: list[str] = []
    for file in files:
        normalized = file.replace("\\", "/")
        if normalized in forbidden_exact:
            bad.append(normalized)
        if normalized.startswith("refs/") and normalized != "refs/manifest.json":
            bad.append(normalized)
        if any(normalized.startswith(prefix) for prefix in forbidden_prefixes):
            bad.append(normalized)
        if any(normalized.endswith(suffix) for suffix in forbidden_suffixes):
            bad.append(normalized)

    if bad:
        fail("Tracked local/generated files are not release-safe:\n" + "\n".join(sorted(set(bad))))


def check_tracked_content_hygiene(files: list[str]) -> None:
    forbidden_patterns = [
        ("lab domain", re.compile("lu" + "dus", re.IGNORECASE)),
        ("lab network", re.compile(r"\b10\.9\.")),
        ("lab hostname", re.compile("ad" + "lab", re.IGNORECASE)),
        ("local user path", re.compile(r"C:\\Users\\blaiseofglory", re.IGNORECASE)),
        ("test SSH credential", re.compile(r"debian\s*[:=]\s*debian", re.IGNORECASE)),
    ]
    skip_suffixes = {
        ".ico",
        ".jpg",
        ".jpeg",
        ".lock",
        ".o",
        ".pdf",
        ".png",
        ".webp",
    }
    findings: list[str] = []

    for file in files:
        path = REPO_ROOT / file
        if path.suffix.lower() in skip_suffixes or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in forbidden_patterns:
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{file}:{line}: {label} marker")

    if findings:
        fail("Tracked files contain release-blocking lab/local markers:\n" + "\n".join(findings))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate nano-bofs release metadata contracts.")
    parser.add_argument("--tag", help="Expected release tag, such as v0.1.1.")
    args = parser.parse_args()

    root_version = read_project_version(REPO_ROOT / "pyproject.toml")
    runtime_version = read_project_version(REPO_ROOT / "Payload_Type" / "nano_bofs" / "pyproject.toml")
    expected_tag = f"v{root_version}"
    tag = args.tag or expected_tag

    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag):
        fail(f"Tag must look like vMAJOR.MINOR.PATCH; got {tag!r}")
    if runtime_version != root_version:
        fail(f"Root version {root_version!r} does not match Mythic runtime version {runtime_version!r}")
    if tag != expected_tag:
        fail(f"Tag {tag!r} does not match pyproject version {root_version!r}; expected {expected_tag!r}")

    builder_path = REPO_ROOT / "Payload_Type" / "nano_bofs" / "nano_bofs_mythic" / "builder.py"
    semver, icon_path = read_builder_values(builder_path)
    if semver != root_version:
        fail(f"NanoBofs.semver {semver!r} does not match project version {root_version!r}")

    icon_file = REPO_ROOT / "Payload_Type" / "nano_bofs" / icon_path
    if not icon_file.exists():
        fail(f"Mythic icon path does not exist: {icon_file.relative_to(REPO_ROOT)}")
    if icon_file.suffix.lower() == ".png":
        check_png(icon_file)

    config = json.loads((REPO_ROOT / "config.json").read_text(encoding="utf-8"))
    if config.get("exclude_agent_icons") is not False:
        fail("config.json must set exclude_agent_icons to false so Mythic can install the service icon")
    image_ref = config.get("remote_images", {}).get("nano_bofs")
    expected_image_ref = f"{IMAGE_REF_PREFIX}{tag}"
    if image_ref != expected_image_ref:
        fail(f"config.json nano_bofs image {image_ref!r} does not match expected {expected_image_ref!r}")

    installer_icon = REPO_ROOT / "agent_icons" / "nano_bofs.png"
    if not installer_icon.exists():
        fail("agent_icons/nano_bofs.png is required for Mythic's installed-service icon")
    check_png(installer_icon)
    if installer_icon.read_bytes() != icon_file.read_bytes():
        fail("agent_icons/nano_bofs.png does not match the runtime Mythic icon")

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    if f"@{tag}" not in readme:
        fail(f"README.md does not reference install tag @{tag}")
    readme_icon = "Payload_Type/nano_bofs/nano_bofs_mythic/nano_bofs.png"
    if readme_icon not in readme:
        fail(f"README.md does not reference {readme_icon}")

    files = tracked_files()
    check_tracked_hygiene(files)
    check_tracked_content_hygiene(files)
    print(f"release metadata contracts passed for {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
