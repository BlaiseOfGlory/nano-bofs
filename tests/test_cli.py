from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nano_bofs.cli import build_command
from nano_bofs.cli import history_command
from nano_bofs.cli import main
from nano_bofs.cli import vars_command
from nano_bofs.config import ResolvedConfig
from nano_bofs.renderers import render_payload


class CliTests(unittest.TestCase):
    def render_command_result(self, result) -> str:
        payload, format_name = result
        return render_payload(payload, format_name)

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

    def test_build_command_uses_config_output_dir_when_output_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self.make_config(root)
            captured: dict[str, object] = {}

            module = SimpleNamespace()
            module.NAME = "fake"
            module.DESCRIPTION = "Fake test module."
            module.add_arguments = lambda parser: None
            module.build_plan = lambda args: {
                "artifact_basename": "demo",
                "source_name": "demo.c",
                "build": {},
                "metadata": {},
            }
            module.render_plan = lambda plan: "void go(char * args, int len) { (void)args; (void)len; }"

            def fake_build_artifacts(**kwargs):
                captured["requested_output_paths"] = kwargs["requested_output_paths"]
                return (
                    "docker",
                    {
                        "x64": {
                            "path": str(kwargs["requested_output_paths"]["x64"].with_name("demo-abcde.x64.o")),
                            "md5": "000000000000000000000000000abcde",
                            "md5_suffix": "abcde",
                        }
                    },
                )

            with patch("nano_bofs.cli.load_config", return_value=config):
                with patch("nano_bofs.cli.discover_templates", return_value=["fake"]):
                    with patch("nano_bofs.cli.load_template_module", return_value=module):
                        with patch("nano_bofs.cli.build_artifacts", side_effect=fake_build_artifacts):
                            result = build_command(["fake", "--arch", "x64"])

            requested_output_paths = captured["requested_output_paths"]
            self.assertEqual(requested_output_paths["x64"], config.output_dir / "demo.x64.o")
            output = self.render_command_result(result)
            self.assertIn("template: fake", output)
            self.assertIn("backend:  docker", output)
            self.assertIn("artifact (x64):", output)
            self.assertNotIn('"source_paths"', output)

    def test_build_command_json_flag_prints_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self.make_config(root)

            module = SimpleNamespace()
            module.NAME = "fake"
            module.DESCRIPTION = "Fake test module."
            module.add_arguments = lambda parser: None
            module.build_plan = lambda args: {
                "artifact_basename": "demo",
                "source_name": "demo.c",
                "build": {},
                "metadata": {"final_server": "\\\\DC01"},
            }
            module.render_plan = lambda plan: "void go(char * args, int len) { (void)args; (void)len; }"

            def fake_build_artifacts(**kwargs):
                return (
                    "docker",
                    {
                        "x64": {
                            "path": str(kwargs["requested_output_paths"]["x64"].with_name("demo-abcde.x64.o")),
                            "md5": "000000000000000000000000000abcde",
                            "md5_suffix": "abcde",
                            "source_path": str(config.state_dir / "build" / "fake" / "abcde" / "demo.c"),
                        }
                    },
                )

            with patch("nano_bofs.cli.load_config", return_value=config):
                with patch("nano_bofs.cli.discover_templates", return_value=["fake"]):
                    with patch("nano_bofs.cli.load_template_module", return_value=module):
                        with patch("nano_bofs.cli.build_artifacts", side_effect=fake_build_artifacts):
                            result = build_command(["fake", "--arch", "x64", "--json"])

            output = self.render_command_result(result)
            data = json.loads(output)
            self.assertEqual(data["template"], "fake")
            self.assertIn("source_paths", data)
            self.assertEqual(data["metadata"]["final_server"], "\\\\DC01")

    def test_build_command_template_help_prefers_template_parser(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self.make_config(root)

            module = SimpleNamespace()
            module.NAME = "fake"
            module.DESCRIPTION = "Fake test module."

            def add_arguments(parser) -> None:
                parser.add_argument("target", help="Target host.")

            module.add_arguments = add_arguments
            module.build_plan = lambda args: {
                "artifact_basename": "demo",
                "source_name": "demo.c",
                "build": {},
                "metadata": {},
            }
            module.render_plan = lambda plan: "void go(char * args, int len) { (void)args; (void)len; }"

            with patch("nano_bofs.cli.load_config", return_value=config):
                with patch("nano_bofs.cli.discover_templates", return_value=["fake"]):
                    with patch("nano_bofs.cli.load_template_module", return_value=module):
                        stdout = io.StringIO()
                        with contextlib.redirect_stdout(stdout):
                            with self.assertRaises(SystemExit) as exc:
                                build_command(["fake", "-h"], binary_name="nano-bofsx", default_format="toon")

            self.assertEqual(exc.exception.code, 0)
            output = stdout.getvalue()
            self.assertIn("usage: nano-bofsx build fake", output)
            self.assertIn("Target host.", output)
            self.assertNotIn("{fake}", output)

    def test_history_command_reads_index_from_configured_state_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self.make_config(root)
            index_path = config.state_dir / "index.jsonl"
            index_path.parent.mkdir(parents=True, exist_ok=True)
            index_path.write_text(
                json.dumps(
                    {
                        "built_at": "2026-04-21T18:28:12.153556+00:00",
                        "template": "netstat",
                        "architecture": "x64",
                        "artifact": str(root / "netstat-12345.x64.o"),
                        "source_path": str(config.state_dir / "build" / "netstat" / "12345" / "netstat.c"),
                        "md5": "aaaaaaaaaaaaaaaaaaaaaaaaaaa12345",
                        "md5_suffix": "12345",
                        "backend": "docker",
                        "user_inputs": {"server": "dc01"},
                        "final_values": {"final_server": "\\\\DC01", "targets_local_host": False},
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with patch("nano_bofs.cli.load_config", return_value=config):
                result = history_command(["netstat"])

            output = self.render_command_result(result)
            self.assertIn("netstat", output)
            self.assertIn("12345", output)
            self.assertIn("docker", output)
            self.assertIn('"server": "dc01"', output)
            self.assertIn('"final_server": "\\\\\\\\DC01"', output)

    def test_history_query_returns_all_matching_entries_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self.make_config(root)
            index_path = config.state_dir / "index.jsonl"
            index_path.parent.mkdir(parents=True, exist_ok=True)
            index_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "built_at": "2026-04-21T18:28:12.153556+00:00",
                                "template": "cacls",
                                "architecture": "x64",
                                "artifact": str(root / "cacls-11111.x64.o"),
                                "md5": "aaaaaaaaaaaaaaaaaaaaaaaaaaa11111",
                                "md5_suffix": "11111",
                                "backend": "docker",
                            }
                        ),
                        json.dumps(
                            {
                                "built_at": "2026-04-22T18:28:12.153556+00:00",
                                "template": "cacls",
                                "architecture": "x64",
                                "artifact": str(root / "cacls-22222.x64.o"),
                                "md5": "bbbbbbbbbbbbbbbbbbbbbbbbbbb22222",
                                "md5_suffix": "22222",
                                "backend": "docker",
                            }
                        ),
                        json.dumps(
                            {
                                "built_at": "2026-04-23T18:28:12.153556+00:00",
                                "template": "ldapsearch",
                                "architecture": "x64",
                                "artifact": str(root / "ldapsearch-33333.x64.o"),
                                "md5": "ccccccccccccccccccccccccccc33333",
                                "md5_suffix": "33333",
                                "backend": "docker",
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with patch("nano_bofs.cli.load_config", return_value=config):
                result = history_command(["cacls"])

            output = self.render_command_result(result)
            self.assertIn("11111", output)
            self.assertIn("22222", output)
            self.assertNotIn("33333", output)
            self.assertLess(output.index("22222"), output.index("11111"))

    def test_history_command_defaults_to_latest_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self.make_config(root)
            index_path = config.state_dir / "index.jsonl"
            index_path.parent.mkdir(parents=True, exist_ok=True)
            index_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "built_at": "2026-04-21T18:28:12.153556+00:00",
                                "template": "netstat",
                                "architecture": "x64",
                                "artifact": str(root / "netstat-11111.x64.o"),
                                "md5": "aaaaaaaaaaaaaaaaaaaaaaaaaaa11111",
                                "md5_suffix": "11111",
                                "backend": "docker",
                            }
                        ),
                        json.dumps(
                            {
                                "built_at": "2026-04-22T18:28:12.153556+00:00",
                                "template": "ldapsearch",
                                "architecture": "x64",
                                "artifact": str(root / "ldapsearch-22222.x64.o"),
                                "md5": "bbbbbbbbbbbbbbbbbbbbbbbbbbb22222",
                                "md5_suffix": "22222",
                                "backend": "docker",
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with patch("nano_bofs.cli.load_config", return_value=config):
                result = history_command([])

            output = self.render_command_result(result)
            self.assertIn("ldapsearch", output)
            self.assertIn("22222", output)
            self.assertNotIn("netstat", output)
            self.assertNotIn("11111", output)

    def test_history_command_all_shows_everything_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self.make_config(root)
            index_path = config.state_dir / "index.jsonl"
            index_path.parent.mkdir(parents=True, exist_ok=True)
            index_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "built_at": "2026-04-21T18:28:12.153556+00:00",
                                "template": "netstat",
                                "architecture": "x64",
                                "artifact": str(root / "netstat-11111.x64.o"),
                                "md5": "aaaaaaaaaaaaaaaaaaaaaaaaaaa11111",
                                "md5_suffix": "11111",
                                "backend": "docker",
                            }
                        ),
                        json.dumps(
                            {
                                "built_at": "2026-04-22T18:28:12.153556+00:00",
                                "template": "ldapsearch",
                                "architecture": "x64",
                                "artifact": str(root / "ldapsearch-22222.x64.o"),
                                "md5": "bbbbbbbbbbbbbbbbbbbbbbbbbbb22222",
                                "md5_suffix": "22222",
                                "backend": "docker",
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with patch("nano_bofs.cli.load_config", return_value=config):
                result = history_command(["all"])

            output = self.render_command_result(result)
            self.assertIn("ldapsearch", output)
            self.assertIn("netstat", output)
            self.assertLess(output.index("ldapsearch"), output.index("netstat"))

    def test_history_command_supports_first_and_last_slices(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self.make_config(root)
            index_path = config.state_dir / "index.jsonl"
            index_path.parent.mkdir(parents=True, exist_ok=True)
            index_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "built_at": "2026-04-20T18:28:12.153556+00:00",
                                "template": "one",
                                "architecture": "x64",
                                "artifact": str(root / "one-11111.x64.o"),
                                "md5": "aaaaaaaaaaaaaaaaaaaaaaaaaaa11111",
                                "md5_suffix": "11111",
                                "backend": "docker",
                            }
                        ),
                        json.dumps(
                            {
                                "built_at": "2026-04-21T18:28:12.153556+00:00",
                                "template": "two",
                                "architecture": "x64",
                                "artifact": str(root / "two-22222.x64.o"),
                                "md5": "bbbbbbbbbbbbbbbbbbbbbbbbbbb22222",
                                "md5_suffix": "22222",
                                "backend": "docker",
                            }
                        ),
                        json.dumps(
                            {
                                "built_at": "2026-04-22T18:28:12.153556+00:00",
                                "template": "three",
                                "architecture": "x64",
                                "artifact": str(root / "three-33333.x64.o"),
                                "md5": "ccccccccccccccccccccccccccc33333",
                                "md5_suffix": "33333",
                                "backend": "docker",
                            }
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with patch("nano_bofs.cli.load_config", return_value=config):
                first_result = history_command(["--first", "2"])

                last_result = history_command(["--last", "2"])

            first_output = self.render_command_result(first_result)
            self.assertIn("one", first_output)
            self.assertIn("two", first_output)
            self.assertNotIn("three", first_output)
            self.assertLess(first_output.index("one"), first_output.index("two"))

            last_output = self.render_command_result(last_result)
            self.assertIn("two", last_output)
            self.assertIn("three", last_output)
            self.assertNotIn("one", last_output)
            self.assertLess(last_output.index("three"), last_output.index("two"))

    def test_vars_command_shows_template_help_with_defaults(self) -> None:
        result = vars_command(["ldapsearch"])

        output = self.render_command_result(result)
        self.assertIn("ldapsearch variables:", output)
        self.assertIn("--attributes ATTRIBUTES", output)
        self.assertIn("--scope SCOPE", output)
        self.assertIn("--ldaps", output)
        self.assertIn('default: *', output)
        self.assertIn('default: 3', output)

    def test_main_history_help_reaches_history_parser(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as exc:
                main(["history", "--help"])

        self.assertEqual(exc.exception.code, 0)
        output = stdout.getvalue()
        self.assertIn("usage: nano-bofs history", output)
        self.assertIn("QUERY|all", output)
        self.assertIn("--first N", output)
        self.assertIn("--last N", output)


if __name__ == "__main__":
    unittest.main()
