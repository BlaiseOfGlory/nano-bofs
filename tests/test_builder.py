from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nano_bofs.builder import build_index_path
from nano_bofs.builder import finalize_artifacts
from nano_bofs.builder import indexed_output_path
from nano_bofs.config import ResolvedConfig
from nano_bofs.pathing import discover_workspace_root


class BuilderTests(unittest.TestCase):
    def load_payload_module(self, module_name: str, file_name: str):
        path = (
            Path(__file__).resolve().parents[1]
            / "Payload_Type"
            / "nano_bofs"
            / "src"
            / "nano_bofs"
            / file_name
        )
        spec = importlib.util.spec_from_file_location(module_name, path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def make_config(self, root: Path) -> ResolvedConfig:
        state_dir = root / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        return ResolvedConfig(
            state_dir=state_dir,
            output_dir=root / "out",
            default_backend="auto",
            docker_image="freefirex2/ts_bof_builder:latest",
            user_config_path=root / ".nano-bofs" / "config.toml",
            project_config_path=None,
            project_local_config_path=None,
        )

    def test_indexed_output_path_appends_suffix_before_arch_extension(self) -> None:
        requested = Path("netstat.x64.o")
        indexed = indexed_output_path(requested, "x64", "12345")
        self.assertEqual(indexed.name, "netstat-12345.x64.o")

    def test_indexed_output_path_appends_suffix_before_generic_extension(self) -> None:
        requested = Path("custom-output.o")
        indexed = indexed_output_path(requested, "x64", "abcde")
        self.assertEqual(indexed.name, "custom-output-abcde.o")

    def test_finalize_artifacts_copies_bof_with_hash_suffix_and_updates_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self.make_config(root)
            staging_dir = config.state_dir / "build" / "fake" / ".staging" / "session"
            temp_output = staging_dir / "artifacts" / "x64.o"
            temp_output.parent.mkdir(parents=True, exist_ok=True)
            temp_output.write_bytes(b"hello bof")

            source_path = staging_dir / "fake.c"
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_text("void go(char * args, int len) {}", encoding="utf-8")

            records = finalize_artifacts(
                config=config,
                template_name="fake",
                source_path_value=source_path,
                temp_outputs={"x64": temp_output},
                requested_output_paths={"x64": root / "payloads" / "fake.x64.o"},
                backend="docker",
                user_inputs={"server": "DC01"},
                metadata={"note": "test"},
            )

            record = records["x64"]
            final_path = Path(record["path"])
            self.assertTrue(final_path.exists())
            self.assertEqual(final_path.read_bytes(), b"hello bof")
            self.assertTrue(final_path.name.startswith("fake-"))
            self.assertTrue(final_path.name.endswith(".x64.o"))
            self.assertEqual(record["md5"][-5:], record["md5_suffix"])
            tracked_source_path = Path(record["source_path"])
            tracked_build_dir = Path(record["build_dir"])
            tracked_build_artifact = Path(record["build_artifact"])
            self.assertEqual(tracked_build_dir, config.state_dir / "build" / "fake" / record["md5_suffix"])
            self.assertTrue(tracked_source_path.exists())
            self.assertEqual(tracked_source_path.read_text(encoding="utf-8"), "void go(char * args, int len) {}")
            self.assertTrue(tracked_build_artifact.exists())
            self.assertEqual(tracked_build_artifact.read_bytes(), b"hello bof")
            self.assertFalse(staging_dir.exists())

            index_path = build_index_path(config)
            self.assertTrue(index_path.exists())
            entries = [json.loads(line) for line in index_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(entries), 1)
            entry = entries[0]
            self.assertEqual(entry["artifact"], str(final_path))
            self.assertEqual(entry["source_path"], str(tracked_source_path))
            self.assertEqual(entry["build_dir"], str(tracked_build_dir))
            self.assertEqual(entry["build_artifact"], str(tracked_build_artifact))
            self.assertEqual(entry["md5"], record["md5"])
            self.assertEqual(entry["md5_suffix"], record["md5_suffix"])
            self.assertEqual(entry["template"], "fake")
            self.assertEqual(entry["user_inputs"], {"server": "DC01"})
            self.assertEqual(entry["final_values"], {"note": "test"})
            self.assertEqual(entry["metadata"], {"note": "test"})

    def test_payload_builder_docker_uses_workspace_root_for_repo_templates(self) -> None:
        self.load_payload_module("nano_bofs.pathing", "pathing.py")
        payload_builder = self.load_payload_module("payload_nano_bofs_builder_test", "builder.py")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self.make_config(root)
            source_path = config.state_dir / "build" / "fake" / ".staging" / "session" / "fake.c"
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_text("void go(char * args, int len) {}", encoding="utf-8")
            repo_root = Path(__file__).resolve().parents[1]
            workspace_root = payload_builder.workspace_root().resolve()
            output_paths = {"x64": root / "payloads" / "fake.x64.o"}
            build_spec = {
                "include_dirs": [
                    str(repo_root / "shared" / "common"),
                    str(repo_root / "templates" / "adcs_enum"),
                    str(repo_root / "Payload_Type" / "nano_bofs" / "shared" / "common"),
                ],
                "cflags": ["-Os", "-c", "-DBOF"],
            }

            with patch.object(payload_builder.subprocess, "run") as run_mock:
                run_mock.return_value.returncode = 0
                run_mock.return_value.stdout = ""
                run_mock.return_value.stderr = ""

                payload_builder._build_with_docker(config, build_spec, source_path, output_paths)

            command = run_mock.call_args.args[0]
            self.assertIn(f"{workspace_root}:/workspace", command)
            container_command = command[-1]
            self.assertIn("-I shared/common", container_command)
            self.assertIn("-I templates/adcs_enum", container_command)
            self.assertIn("-I Payload_Type/nano_bofs/shared/common", container_command)
            self.assertIn("/state/build/fake/.staging/session/fake.c", container_command)

    def test_payload_builder_docker_rejects_include_dir_outside_workspace_and_state(self) -> None:
        self.load_payload_module("nano_bofs.pathing", "pathing.py")
        payload_builder = self.load_payload_module("payload_nano_bofs_builder_invalid_test", "builder.py")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self.make_config(root)
            source_path = config.state_dir / "build" / "fake" / ".staging" / "session" / "fake.c"
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_text("void go(char * args, int len) {}", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "workspace root .* or the nano-bofs state dir"):
                payload_builder._build_with_docker(
                    config,
                    {
                        "include_dirs": [str(root / "outside")],
                        "cflags": ["-Os", "-c", "-DBOF"],
                    },
                    source_path,
                    {"x64": root / "payloads" / "fake.x64.o"},
                )

    def test_payload_pathing_prefers_highest_matching_workspace_root(self) -> None:
        pathing = self.load_payload_module("payload_nano_bofs_pathing_test", "pathing.py")

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            payload_root = repo_root / "Payload_Type" / "nano_bofs"
            source_file = payload_root / "src" / "nano_bofs" / "builder.py"
            for root in (repo_root, payload_root):
                (root / "templates").mkdir(parents=True, exist_ok=True)
                (root / "shared").mkdir(parents=True, exist_ok=True)
            source_file.parent.mkdir(parents=True, exist_ok=True)
            source_file.write_text("", encoding="utf-8")

            discovered = pathing.discover_workspace_root(source_file.resolve(), payload_root.resolve())
            self.assertEqual(discovered, repo_root.resolve())

    def test_payload_pathing_falls_back_to_payload_root_for_shallow_install(self) -> None:
        pathing = self.load_payload_module("payload_nano_bofs_pathing_shallow_test", "pathing.py")

        with tempfile.TemporaryDirectory() as temp_dir:
            payload_root = Path(temp_dir) / "Mythic"
            source_file = payload_root / "src" / "nano_bofs" / "builder.py"
            (payload_root / "templates").mkdir(parents=True, exist_ok=True)
            (payload_root / "shared").mkdir(parents=True, exist_ok=True)
            source_file.parent.mkdir(parents=True, exist_ok=True)
            source_file.write_text("", encoding="utf-8")

            discovered = pathing.discover_workspace_root(source_file.resolve(), payload_root.resolve())
            self.assertEqual(discovered, payload_root.resolve())

    def test_core_pathing_prefers_highest_matching_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "repo"
            package_root = repo_root / "src" / "nano_bofs"
            source_file = package_root / "builder.py"
            (repo_root / "templates").mkdir(parents=True, exist_ok=True)
            (repo_root / "shared").mkdir(parents=True, exist_ok=True)
            package_root.mkdir(parents=True, exist_ok=True)
            source_file.write_text("", encoding="utf-8")

            discovered = discover_workspace_root(source_file.resolve(), package_root.resolve())
            self.assertEqual(discovered, repo_root.resolve())

    def test_core_pathing_supports_installed_package_data_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package_root = Path(temp_dir) / "site-packages" / "nano_bofs"
            source_file = package_root / "builder.py"
            (package_root / "templates").mkdir(parents=True, exist_ok=True)
            (package_root / "shared").mkdir(parents=True, exist_ok=True)
            source_file.write_text("", encoding="utf-8")

            discovered = discover_workspace_root(source_file.resolve(), package_root.resolve())
            self.assertEqual(discovered, package_root.resolve())


if __name__ == "__main__":
    unittest.main()
