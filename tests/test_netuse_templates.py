from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path


TEMPLATES_ROOT = Path(__file__).resolve().parents[1] / "templates"
if str(TEMPLATES_ROOT) not in sys.path:
    sys.path.insert(0, str(TEMPLATES_ROOT))

from netuse_add import parser as netuse_add_parser
from netuse_delete import parser as netuse_delete_parser


class NetuseAddTemplateTests(unittest.TestCase):
    def make_args(self, *argv: str) -> argparse.Namespace:
        parser = argparse.ArgumentParser()
        netuse_add_parser.add_arguments(parser)
        return parser.parse_args(list(argv))

    def test_build_plan_defaults_optional_fields(self) -> None:
        plan = netuse_add_parser.build_plan(self.make_args("\\\\192.0.2.10\\IPC$"))

        self.assertEqual(plan["metadata"]["share"], "\\\\192.0.2.10\\IPC$")
        self.assertEqual(plan["metadata"]["username"], "")
        self.assertEqual(plan["placeholders"]["__NANO_PASSWORD__"], "")
        self.assertEqual(plan["metadata"]["device"], "")
        self.assertFalse(plan["metadata"]["persist"])
        self.assertFalse(plan["metadata"]["require_privacy"])

    def test_build_plan_sets_flags_and_device(self) -> None:
        plan = netuse_add_parser.build_plan(
            self.make_args(
                "\\\\192.0.2.10\\IPC$",
                "",
                "",
                "Z:",
                "true",
                "true",
            )
        )

        self.assertEqual(plan["metadata"]["device"], "Z:")
        self.assertTrue(plan["metadata"]["persist"])
        self.assertTrue(plan["metadata"]["require_privacy"])
        self.assertEqual(plan["placeholders"]["__NANO_PERSIST__"], "1")
        self.assertEqual(plan["placeholders"]["__NANO_REQUIRE_PRIVACY__"], "1")

    def test_build_plan_rejects_bad_boolish_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "persist must be one of"):
            netuse_add_parser.build_plan(
                self.make_args("\\\\192.0.2.10\\IPC$", "", "", "", "sometimes")
            )


class NetuseDeleteTemplateTests(unittest.TestCase):
    def make_args(self, *argv: str) -> argparse.Namespace:
        parser = argparse.ArgumentParser()
        netuse_delete_parser.add_arguments(parser)
        return parser.parse_args(list(argv))

    def test_build_plan_defaults_optional_flags(self) -> None:
        plan = netuse_delete_parser.build_plan(
            self.make_args("\\\\192.0.2.10\\MissingShare")
        )

        self.assertEqual(plan["metadata"]["target"], "\\\\192.0.2.10\\MissingShare")
        self.assertFalse(plan["metadata"]["persist"])
        self.assertFalse(plan["metadata"]["force"])

    def test_build_plan_sets_force_and_persist(self) -> None:
        plan = netuse_delete_parser.build_plan(
            self.make_args("\\\\192.0.2.10\\MissingShare", "true", "true")
        )

        self.assertTrue(plan["metadata"]["persist"])
        self.assertTrue(plan["metadata"]["force"])
        self.assertEqual(plan["placeholders"]["__NANO_PERSIST__"], "1")
        self.assertEqual(plan["placeholders"]["__NANO_FORCE__"], "1")

    def test_build_plan_rejects_bad_boolish_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "force must be one of"):
            netuse_delete_parser.build_plan(
                self.make_args("\\\\192.0.2.10\\MissingShare", "", "later")
            )


if __name__ == "__main__":
    unittest.main()
