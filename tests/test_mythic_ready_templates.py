from __future__ import annotations

import argparse
import importlib
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
PAYLOAD_SRC_ROOT = Path(__file__).resolve().parents[1] / "Payload_Type" / "nano_bofs" / "src"


def _load_payload_template_catalog():
    original_path = list(sys.path)
    original_modules = {
        name: module
        for name, module in sys.modules.items()
        if name == "nano_bofs" or name.startswith("nano_bofs.")
    }
    for name in list(sys.modules):
        if name == "nano_bofs" or name.startswith("nano_bofs."):
            del sys.modules[name]
    sys.path.insert(0, str(PAYLOAD_SRC_ROOT))
    try:
        return importlib.import_module("nano_bofs.template_catalog")
    finally:
        for name in list(sys.modules):
            if name == "nano_bofs" or name.startswith("nano_bofs."):
                del sys.modules[name]
        sys.modules.update(original_modules)
        sys.path[:] = original_path


template_catalog = _load_payload_template_catalog()
load_mythic_template_definitions = template_catalog.load_mythic_template_definitions
load_template_definition = template_catalog.load_template_definition
parse_template_inputs = template_catalog.parse_template_inputs


class MythicReadyTemplateTests(unittest.TestCase):
    def test_load_mythic_template_definitions_includes_newly_supported_templates(self) -> None:
        names = {definition.name for definition in load_mythic_template_definitions()}

        self.assertIn("mythicSmoke", names)
        self.assertIn("netuse", names)
        self.assertIn("reg_query", names)
        self.assertIn("reg_query_recursive", names)

    def test_netuse_definition_uses_mythic_friendly_fields(self) -> None:
        definition = load_template_definition("netuse")
        variable_names = [variable.name for variable in definition.variables]

        self.assertEqual(
            variable_names,
            [
                "command",
                "share",
                "username",
                "password",
                "device",
                "persist",
                "require_privacy",
                "target",
                "force",
            ],
        )

    def test_parse_template_inputs_supports_reg_query_fields(self) -> None:
        args = parse_template_inputs(
            "reg_query",
            {
                "hostname": "DC01",
                "hive": "HKLM",
                "path": "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion",
                "value": "ProductName",
            },
        )

        self.assertEqual(
            args.arguments,
            ["DC01", "HKLM", "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion", "ProductName"],
        )

    def test_parse_template_inputs_supports_reg_query_recursive_fields(self) -> None:
        args = parse_template_inputs(
            "reg_query_recursive",
            {
                "hive": "HKLM",
                "path": "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion",
            },
        )

        self.assertEqual(
            args.arguments,
            ["HKLM", "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion"],
        )

    def test_parse_template_inputs_preserves_optional_values_across_templates(self) -> None:
        cases = [
            (
                "ldapsearch",
                {
                    "query": "(objectClass=computer)",
                    "attributes": "cn,dNSHostName",
                    "count": 1,
                    "scope": 1,
                    "hostname": "dc01.example.test",
                    "dn": "DC=example,DC=test",
                    "ldaps": "true",
                },
                {
                    "query": "(objectClass=computer)",
                    "attributes": "cn,dNSHostName",
                    "count": "1",
                    "scope": "1",
                    "hostname": "dc01.example.test",
                    "dn": "DC=example,DC=test",
                    "ldaps": True,
                },
            ),
            (
                "netuse",
                {
                    "command": "delete",
                    "target": "\\\\192.0.2.10\\IPC$",
                    "force": "true",
                },
                {
                    "command": "delete",
                    "target": "\\\\192.0.2.10\\IPC$",
                    "force": True,
                },
            ),
        ]

        for template_name, raw_inputs, expected_values in cases:
            with self.subTest(template=template_name):
                args = parse_template_inputs(template_name, raw_inputs)
                self.assertIsInstance(args, argparse.Namespace)
                for field_name, expected in expected_values.items():
                    self.assertEqual(getattr(args, field_name), expected)

    def test_parse_template_inputs_rejects_invalid_boolish_flag_values_across_templates(self) -> None:
        cases = [
            (
                "ldapsearch",
                {
                    "query": "(objectClass=computer)",
                    "ldaps": "maybe",
                },
                "ldaps must be one of",
            ),
            (
                "netuse",
                {
                    "command": "delete",
                    "target": "\\\\192.0.2.10\\IPC$",
                    "force": "maybe",
                },
                "force must be one of",
            ),
        ]

        for template_name, raw_inputs, expected_error in cases:
            with self.subTest(template=template_name):
                with self.assertRaisesRegex(ValueError, expected_error):
                    parse_template_inputs(template_name, raw_inputs)


class TemplateOverlayTests(unittest.TestCase):
    def _write_template(self, root: Path, name: str, description: str) -> None:
        template_dir = root / name
        template_dir.mkdir(parents=True, exist_ok=True)
        (template_dir / "parser.py").write_text(
            "\n".join(
                [
                    "from __future__ import annotations",
                    "",
                    "import argparse",
                    "",
                    f'NAME = "{name}"',
                    f'DESCRIPTION = "{description}"',
                    "VARIABLES = []",
                    "",
                    "def add_arguments(parser: argparse.ArgumentParser) -> None:",
                    "    return None",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def test_mounted_templates_are_discovered_without_baked_templates(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mounted = root / "mounted"
            baked = root / "baked"
            self._write_template(mounted, "custom_only", "mounted template")

            with (
                patch.object(template_catalog, "REPO_TEMPLATES_ROOT", root / "missing-repo"),
                patch.object(template_catalog, "VENDORED_TEMPLATES_ROOT", mounted),
                patch.object(template_catalog, "BAKED_TEMPLATES_ROOT", baked),
            ):
                self.assertIn("custom_only", template_catalog.discover_templates())

    def test_baked_templates_are_discovered_when_mounted_templates_are_missing(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mounted = root / "mounted"
            baked = root / "baked"
            self._write_template(baked, "mythicSmoke", "baked smoke test")

            with (
                patch.object(template_catalog, "REPO_TEMPLATES_ROOT", root / "missing-repo"),
                patch.object(template_catalog, "VENDORED_TEMPLATES_ROOT", mounted),
                patch.object(template_catalog, "BAKED_TEMPLATES_ROOT", baked),
            ):
                self.assertIn("mythicSmoke", template_catalog.discover_templates())
                definition = template_catalog.load_template_definition("mythicSmoke")
                self.assertEqual(definition.description, "baked smoke test")

    def test_mounted_templates_override_baked_templates_with_same_name(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mounted = root / "mounted"
            baked = root / "baked"
            self._write_template(mounted, "override_me", "mounted version")
            self._write_template(baked, "override_me", "baked version")

            with (
                patch.object(template_catalog, "REPO_TEMPLATES_ROOT", root / "missing-repo"),
                patch.object(template_catalog, "VENDORED_TEMPLATES_ROOT", mounted),
                patch.object(template_catalog, "BAKED_TEMPLATES_ROOT", baked),
            ):
                definition = template_catalog.load_template_definition("override_me")
                self.assertEqual(definition.description, "mounted version")

    def test_discover_templates_merges_roots_without_duplicates(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mounted = root / "mounted"
            baked = root / "baked"
            self._write_template(mounted, "custom_only", "mounted only")
            self._write_template(mounted, "override_me", "mounted version")
            self._write_template(baked, "override_me", "baked version")
            self._write_template(baked, "standard_only", "baked only")

            with (
                patch.object(template_catalog, "REPO_TEMPLATES_ROOT", root / "missing-repo"),
                patch.object(template_catalog, "VENDORED_TEMPLATES_ROOT", mounted),
                patch.object(template_catalog, "BAKED_TEMPLATES_ROOT", baked),
            ):
                names = template_catalog.discover_templates()

            self.assertIn("custom_only", names)
            self.assertIn("override_me", names)
            self.assertIn("standard_only", names)
            self.assertEqual(names.count("override_me"), 1)


if __name__ == "__main__":
    unittest.main()
