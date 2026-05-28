from __future__ import annotations

import contextlib
import hashlib
import json
import shlex
import shutil
import subprocess
from datetime import UTC
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from nano_bofs.config import ResolvedConfig
from nano_bofs.pathing import discover_workspace_root


PAYLOAD_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = discover_workspace_root(Path(__file__).resolve(), PAYLOAD_ROOT)
ARCH_TO_COMPILER = {
    "x64": "x86_64-w64-mingw32-gcc",
    "x86": "i686-w64-mingw32-gcc",
}


def normalize_arches(arch: str) -> list[str]:
    if arch == "both":
        return ["x64", "x86"]
    return [arch]


def artifact_paths(output: Path | None, artifact_basename: str, arch: str) -> dict[str, Path]:
    arches = normalize_arches(arch)
    if output is None:
        base_dir = Path.cwd()
        return {item: base_dir / f"{artifact_basename}.{item}.o" for item in arches}

    if output.exists() and output.is_dir():
        return {item: output / f"{artifact_basename}.{item}.o" for item in arches}

    if output.suffix == "":
        return {item: output / f"{artifact_basename}.{item}.o" for item in arches}

    if arch == "both":
        raise ValueError("multi-arch builds require --output to be a directory or suffixless path, not a single .o file.")

    return {arch: output}


def build_root(config: ResolvedConfig) -> Path:
    return config.state_dir / "build"


def build_index_path(config: ResolvedConfig) -> Path:
    return config.state_dir / "index.jsonl"


def create_staging_dir(config: ResolvedConfig, template_name: str) -> Path:
    staging_dir = build_root(config) / template_name / ".staging" / uuid4().hex
    staging_dir.mkdir(parents=True, exist_ok=False)
    return staging_dir


def source_path(staging_dir: Path, source_name: str) -> Path:
    return staging_dir / source_name


def temp_artifact_paths(staging_dir: Path, arches: list[str]) -> dict[str, Path]:
    artifact_dir = staging_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return {arch: artifact_dir / f"{arch}.o" for arch in arches}


def workspace_root() -> Path:
    return REPO_ROOT


def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    result = subprocess.run(
        ["docker", "version", "--format", "{{.Server.Version}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def local_available() -> bool:
    return all(shutil.which(compiler) for compiler in ARCH_TO_COMPILER.values())


def choose_backend(backend: str) -> str:
    if backend == "docker":
        if not docker_available():
            raise ValueError("Docker backend was requested, but Docker is unavailable or the daemon is not running.")
        return "docker"

    if backend == "local":
        if not local_available():
            raise ValueError(
                "Local backend was requested, but the MinGW cross-compilers were not found. "
                "Install x86_64-w64-mingw32-gcc and i686-w64-mingw32-gcc."
            )
        return "local"

    if docker_available():
        return "docker"

    if local_available():
        return "local"

    raise ValueError(
        "No usable build backend is available. Install Docker for the primary backend or "
        "install x86_64-w64-mingw32-gcc and i686-w64-mingw32-gcc for local fallback builds."
    )


def build_artifacts(
    *,
    config: ResolvedConfig,
    template_name: str,
    build_spec: dict[str, object],
    source_path_value: Path,
    requested_output_paths: dict[str, Path],
    backend: str,
    user_inputs: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
) -> tuple[str, dict[str, dict[str, str]]]:
    arches = list(requested_output_paths)
    temp_outputs = temp_artifact_paths(source_path_value.parent, arches)
    selected_backend = choose_backend(backend)
    if selected_backend == "docker":
        _build_with_docker(config, build_spec, source_path_value, temp_outputs)
    else:
        _build_with_local(build_spec, source_path_value, temp_outputs)

    build_records = finalize_artifacts(
        config=config,
        template_name=template_name,
        source_path_value=source_path_value,
        temp_outputs=temp_outputs,
        requested_output_paths=requested_output_paths,
        backend=selected_backend,
        user_inputs=user_inputs or {},
        metadata=metadata or {},
    )
    return selected_backend, build_records


def finalize_artifacts(
    *,
    config: ResolvedConfig,
    template_name: str,
    source_path_value: Path,
    temp_outputs: dict[str, Path],
    requested_output_paths: dict[str, Path],
    backend: str,
    user_inputs: dict[str, object],
    metadata: dict[str, object],
) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    for arch, temp_output in temp_outputs.items():
        md5 = hashlib.md5(temp_output.read_bytes()).hexdigest()
        suffix = md5[-5:]
        final_path = indexed_output_path(requested_output_paths[arch], arch, suffix)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(temp_output, final_path)
        tracked_build_dir = build_root(config) / template_name / suffix
        tracked_build_dir.mkdir(parents=True, exist_ok=True)
        tracked_source_path = tracked_build_dir / source_path_value.name
        tracked_artifact_path = tracked_build_dir / "artifacts" / temp_output.name
        tracked_artifact_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path_value, tracked_source_path)
        shutil.copy2(temp_output, tracked_artifact_path)
        record = {
            "path": str(final_path),
            "md5": md5,
            "md5_suffix": suffix,
            "source_path": str(tracked_source_path),
            "build_dir": str(tracked_build_dir),
            "build_artifact": str(tracked_artifact_path),
        }
        records[arch] = record
        append_build_index(
            config,
            {
                "built_at": datetime.now(UTC).isoformat(),
                "template": template_name,
                "architecture": arch,
                "backend": backend,
                "artifact": str(final_path),
                "requested_artifact": str(requested_output_paths[arch]),
                "source_path": str(tracked_source_path),
                "build_dir": str(tracked_build_dir),
                "build_artifact": str(tracked_artifact_path),
                "md5": md5,
                "md5_suffix": suffix,
                "user_inputs": user_inputs,
                "final_values": metadata,
                "metadata": metadata,
            }
        )
    staging_dir = source_path_value.parent
    shutil.rmtree(staging_dir, ignore_errors=True)
    with contextlib.suppress(OSError):
        staging_dir.parent.rmdir()
    return records


def indexed_output_path(requested_output: Path, arch: str, md5_suffix: str) -> Path:
    filename = requested_output.name
    arch_suffix = f".{arch}.o"
    if filename.endswith(arch_suffix):
        base = filename[: -len(arch_suffix)]
        return requested_output.with_name(f"{base}-{md5_suffix}{arch_suffix}")

    joined_suffix = "".join(requested_output.suffixes)
    if joined_suffix:
        base = filename[: -len(joined_suffix)]
        return requested_output.with_name(f"{base}-{md5_suffix}{joined_suffix}")

    return requested_output.with_name(f"{filename}-{md5_suffix}")


def append_build_index(config: ResolvedConfig, entry: dict[str, object]) -> None:
    index_path = build_index_path(config)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, sort_keys=True))
        handle.write("\n")


def _build_with_local(
    build_spec: dict[str, object],
    source_path_value: Path,
    output_paths: dict[str, Path],
) -> None:
    include_dirs = [Path(item) for item in build_spec.get("include_dirs", [])]
    cflags = list(build_spec.get("cflags", []))

    for arch, output_path in output_paths.items():
        compiler = ARCH_TO_COMPILER[arch]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = [
            compiler,
            "-o",
            str(output_path),
            *[flag for flag in cflags],
            *[value for include_dir in include_dirs for value in ("-I", str(include_dir))],
            str(source_path_value),
        ]
        result = subprocess.run(
            command,
            cwd=PAYLOAD_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise ValueError(
                f"{arch} BOF compilation failed using the local backend. "
                f"Rendered source: {source_path_value}\n{result.stderr.strip() or result.stdout.strip()}"
            )


def _build_with_docker(
    config: ResolvedConfig,
    build_spec: dict[str, object],
    source_path_value: Path,
    output_paths: dict[str, Path],
) -> None:
    workspace = workspace_root().resolve()
    state_root = config.state_dir.resolve()
    include_dirs = [Path(item).resolve() for item in build_spec.get("include_dirs", [])]
    cflags = list(build_spec.get("cflags", []))
    source_rel = source_path_value.resolve().relative_to(state_root).as_posix()
    include_rel = [_include_dir_in_container(item, workspace, state_root) for item in include_dirs]
    source_in_container = f"/state/{source_rel}"

    for arch, output_path in output_paths.items():
        compiler = ARCH_TO_COMPILER[arch]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        container_command = [
            compiler,
            "-o",
            f"/out/{output_path.name}",
            *[flag for flag in cflags],
            *[value for include_dir in include_rel for value in ("-I", include_dir)],
            source_in_container,
        ]
        command = [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "/bin/sh",
            "-v",
            f"{workspace}:/workspace",
            "-v",
            f"{state_root}:/state",
            "-v",
            f"{output_path.parent.resolve()}:/out",
            "-w",
            "/workspace",
            config.docker_image,
            "-lc",
            " ".join(shlex.quote(part) for part in container_command),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise ValueError(
                f"{arch} BOF compilation failed using the Docker backend. "
                f"Rendered source: {source_path_value}\n{result.stderr.strip() or result.stdout.strip()}"
            )


def _include_dir_in_container(include_dir: Path, workspace: Path, state_root: Path) -> str:
    try:
        return include_dir.relative_to(workspace).as_posix()
    except ValueError:
        pass

    try:
        return f"/state/{include_dir.relative_to(state_root).as_posix()}"
    except ValueError as exc:
        raise ValueError(
            "Docker include directory must live under the current workspace root "
            f"({workspace}) or the nano-bofs state dir ({state_root}). Received: {include_dir}"
        ) from exc
