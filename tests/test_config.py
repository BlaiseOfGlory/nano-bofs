from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nano_bofs.config import DEFAULT_DOCKER_IMAGE
from nano_bofs.config import PROJECT_CONFIG_NAME
from nano_bofs.config import PROJECT_LOCAL_CONFIG_NAME
from nano_bofs.config import load_config


class ConfigTests(unittest.TestCase):
    def assert_path_equal(self, left: Path, right: Path) -> None:
        self.assertEqual(str(left.resolve()), str(right.resolve()))

    def test_defaults_use_home_dot_directory_and_start_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            home_dir = Path(temp_dir) / "home"
            start_dir = Path(temp_dir) / "workspace"
            home_dir.mkdir()
            start_dir.mkdir()

            with patch.dict(os.environ, {}, clear=True):
                with patch("nano_bofs.config.Path.home", return_value=home_dir):
                    config = load_config(start_dir)

            self.assert_path_equal(config.state_dir, home_dir / ".nano-bofs")
            self.assert_path_equal(config.output_dir, start_dir)
            self.assert_path_equal(config.user_config_path, home_dir / ".nano-bofs" / "config.toml")
            self.assertIsNone(config.project_config_path)
            self.assertIsNone(config.project_local_config_path)
            self.assertEqual(config.default_backend, "auto")
            self.assertEqual(config.docker_image, DEFAULT_DOCKER_IMAGE)

    def test_project_config_overrides_user_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home_dir = root / "home"
            project_dir = root / "project"
            nested_dir = project_dir / "nested"
            home_dir.mkdir()
            nested_dir.mkdir(parents=True)

            user_config = home_dir / ".nano-bofs" / "config.toml"
            user_config.parent.mkdir(parents=True)
            user_config.write_text(
                "[paths]\n"
                f"state_dir = \"{(root / 'user-state').as_posix()}\"\n"
                f"output_dir = \"{(root / 'user-out').as_posix()}\"\n"
                "\n[build]\n"
                "default_backend = \"local\"\n"
                "docker_image = \"user/image:1\"\n",
                encoding="utf-8",
            )

            project_config = project_dir / PROJECT_CONFIG_NAME
            project_config.write_text(
                "[paths]\n"
                f"state_dir = \"{(root / 'project-state').as_posix()}\"\n"
                f"output_dir = \"{(root / 'project-out').as_posix()}\"\n"
                "\n[build]\n"
                "default_backend = \"docker\"\n"
                "docker_image = \"project/image:2\"\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                with patch("nano_bofs.config.Path.home", return_value=home_dir):
                    config = load_config(nested_dir)

            self.assert_path_equal(config.project_config_path, project_config)
            self.assertIsNone(config.project_local_config_path)
            self.assert_path_equal(config.state_dir, root / "project-state")
            self.assert_path_equal(config.output_dir, root / "project-out")
            self.assertEqual(config.default_backend, "docker")
            self.assertEqual(config.docker_image, "project/image:2")

    def test_local_project_config_overrides_project_for_testing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home_dir = root / "home"
            project_dir = root / "project"
            nested_dir = project_dir / "nested"
            home_dir.mkdir()
            nested_dir.mkdir(parents=True)

            project_config = project_dir / PROJECT_CONFIG_NAME
            project_config.write_text(
                "[paths]\n"
                f"state_dir = \"{(root / 'project-state').as_posix()}\"\n"
                f"output_dir = \"{(root / 'project-out').as_posix()}\"\n"
                "\n[build]\n"
                "default_backend = \"docker\"\n"
                "docker_image = \"project/image:2\"\n",
                encoding="utf-8",
            )

            project_local_config = project_dir / PROJECT_LOCAL_CONFIG_NAME
            project_local_config.write_text(
                "[paths]\n"
                "state_dir = \".nano-bofs\"\n"
                "output_dir = \"out-local\"\n"
                "\n[build]\n"
                "default_backend = \"local\"\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                with patch("nano_bofs.config.Path.home", return_value=home_dir):
                    config = load_config(nested_dir)

            self.assert_path_equal(config.project_config_path, project_config)
            self.assert_path_equal(config.project_local_config_path, project_local_config)
            self.assert_path_equal(config.state_dir, project_dir / ".nano-bofs")
            self.assert_path_equal(config.output_dir, project_dir / "out-local")
            self.assertEqual(config.default_backend, "local")
            self.assertEqual(config.docker_image, "project/image:2")

    def test_environment_overrides_take_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            home_dir = root / "home"
            home_dir.mkdir()
            user_config = root / "custom-config.toml"
            user_config.write_text(
                "[paths]\n"
                f"state_dir = \"{(root / 'user-state').as_posix()}\"\n"
                f"output_dir = \"{(root / 'user-out').as_posix()}\"\n"
                "\n[build]\n"
                "default_backend = \"local\"\n"
                "docker_image = \"user/image:1\"\n",
                encoding="utf-8",
            )

            env = {
                "NANO_BOFS_CONFIG": str(user_config),
                "NANO_BOFS_STATE_DIR": str(root / "env-state"),
                "NANO_BOFS_OUTPUT_DIR": str(root / "env-out"),
                "NANO_BOFS_DEFAULT_BACKEND": "docker",
                "NANO_BOFS_DOCKER_IMAGE": "env/image:3",
            }

            with patch.dict(os.environ, env, clear=True):
                with patch("nano_bofs.config.Path.home", return_value=home_dir):
                    config = load_config(root)

            self.assert_path_equal(config.user_config_path, user_config)
            self.assert_path_equal(config.state_dir, root / "env-state")
            self.assert_path_equal(config.output_dir, root / "env-out")
            self.assertEqual(config.default_backend, "docker")
            self.assertEqual(config.docker_image, "env/image:3")


if __name__ == "__main__":
    unittest.main()
