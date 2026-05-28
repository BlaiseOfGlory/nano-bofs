from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path


VALID_BACKENDS = {"auto", "docker", "local"}
DEFAULT_BACKEND = "auto"
DEFAULT_DOCKER_IMAGE = "freefirex2/ts_bof_builder:latest"
PROJECT_CONFIG_NAME = "nano-bofs.toml"
PROJECT_LOCAL_CONFIG_NAME = "nano-bofs.local.toml"


@dataclass(frozen=True)
class ResolvedConfig:
    state_dir: Path
    output_dir: Path
    default_backend: str
    docker_image: str
    user_config_path: Path
    project_config_path: Path | None
    project_local_config_path: Path | None


def default_user_config_path() -> Path:
    return default_state_dir() / "config.toml"


def default_state_dir() -> Path:
    return Path.home() / ".nano-bofs"


def find_project_config(start: Path | None = None, config_name: str = PROJECT_CONFIG_NAME) -> Path | None:
    current = (start or Path.cwd()).resolve()
    for candidate_dir in (current, *current.parents):
        candidate = candidate_dir / config_name
        if candidate.exists():
            return candidate
    return None


def load_config(start: Path | None = None) -> ResolvedConfig:
    start_path = (start or Path.cwd()).resolve()
    user_config_path = _user_config_path()
    project_config_path = find_project_config(start_path)
    project_local_config_path = find_project_config(start_path, PROJECT_LOCAL_CONFIG_NAME)

    state_dir = default_state_dir()
    output_dir = start_path
    default_backend = DEFAULT_BACKEND
    docker_image = DEFAULT_DOCKER_IMAGE

    file_settings = [
        (user_config_path, _read_config_file(user_config_path)),
        (project_config_path, _read_config_file(project_config_path)),
        (project_local_config_path, _read_config_file(project_local_config_path)),
    ]

    for config_path, data in file_settings:
        if not data:
            continue
        paths_table = _get_table(data, "paths", config_path)
        build_table = _get_table(data, "build", config_path)

        state_value = paths_table.get("state_dir")
        if state_value:
            state_dir = _resolve_path_value(str(state_value), config_path.parent if config_path else start_path)

        output_value = paths_table.get("output_dir")
        if output_value:
            output_dir = _resolve_path_value(str(output_value), config_path.parent if config_path else start_path)

        backend_value = build_table.get("default_backend")
        if backend_value:
            default_backend = str(backend_value)

        docker_value = build_table.get("docker_image")
        if docker_value:
            docker_image = str(docker_value)

    env_state_dir = os.environ.get("NANO_BOFS_STATE_DIR")
    if env_state_dir:
        state_dir = _resolve_path_value(env_state_dir, start_path)

    env_output_dir = os.environ.get("NANO_BOFS_OUTPUT_DIR")
    if env_output_dir:
        output_dir = _resolve_path_value(env_output_dir, start_path)

    env_backend = os.environ.get("NANO_BOFS_DEFAULT_BACKEND")
    if env_backend:
        default_backend = env_backend

    env_docker_image = os.environ.get("NANO_BOFS_DOCKER_IMAGE")
    if env_docker_image:
        docker_image = env_docker_image

    default_backend = _validate_backend(default_backend)
    docker_image = docker_image.strip()
    if not docker_image:
        raise ValueError("docker_image must not be empty. Set build.docker_image to a container image name.")
    if output_dir.suffix.lower() == ".o":
        raise ValueError("output_dir must be a directory path, not a .o file. Set paths.output_dir to a folder.")

    return ResolvedConfig(
        state_dir=state_dir,
        output_dir=output_dir,
        default_backend=default_backend,
        docker_image=docker_image,
        user_config_path=user_config_path,
        project_config_path=project_config_path,
        project_local_config_path=project_local_config_path,
    )


def _user_config_path() -> Path:
    override = os.environ.get("NANO_BOFS_CONFIG")
    if override:
        return _resolve_path_value(override, Path.cwd().resolve())
    return default_user_config_path()


def _read_config_file(path: Path | None) -> dict[str, object]:
    if path is None or not path.exists():
        return {}

    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"invalid config file at {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"invalid config file at {path}: expected a TOML table at the root.")
    return data


def _resolve_path_value(value: str, base_dir: Path) -> Path:
    candidate = Path(os.path.expandvars(value)).expanduser()
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate.resolve()


def _get_table(data: dict[str, object], name: str, path: Path | None) -> dict[str, object]:
    value = data.get(name, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"invalid config file at {path}: [{name}] must be a TOML table.")
    return value


def _validate_backend(value: str) -> str:
    candidate = value.strip().lower()
    if candidate not in VALID_BACKENDS:
        raise ValueError(
            "default_backend must be one of: auto, docker, local. "
            f"Received: {value!r}."
        )
    return candidate
