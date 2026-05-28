from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def discover_workspace_root(start: Path, fallback: Path) -> Path:
    def _has_workspace_markers(candidate: Path) -> bool:
        try:
            return (candidate / "templates").exists() and (candidate / "shared").exists()
        except PermissionError:
            return False

    matches = [
        candidate
        for candidate in (start, *start.parents)
        if _has_workspace_markers(candidate)
    ]
    if matches:
        return matches[-1]
    return fallback


def workspace_root() -> Path:
    return discover_workspace_root(Path(__file__).resolve(), PACKAGE_ROOT)


def templates_root() -> Path:
    root = workspace_root()
    candidate = root / "templates"
    if candidate.exists():
        return candidate
    return PACKAGE_ROOT / "templates"


def shared_root() -> Path:
    root = workspace_root()
    candidate = root / "shared"
    if candidate.exists():
        return candidate
    return PACKAGE_ROOT / "shared"
