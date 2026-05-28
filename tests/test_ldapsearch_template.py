from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path


TEMPLATES_ROOT = Path(__file__).resolve().parents[1] / "templates"
if str(TEMPLATES_ROOT) not in sys.path:
    sys.path.insert(0, str(TEMPLATES_ROOT))

from ldapsearch import parser as ldapsearch_parser


class LdapsearchTemplateTests(unittest.TestCase):
    def make_args(self, *argv: str) -> argparse.Namespace:
        parser = argparse.ArgumentParser()
        ldapsearch_parser.add_arguments(parser)
        return parser.parse_args(list(argv))

    def test_build_plan_uses_upstream_defaults(self) -> None:
        plan = ldapsearch_parser.build_plan(self.make_args("(objectClass=*)"))

        self.assertEqual(plan["metadata"]["final_query"], "(objectClass=*)")
        self.assertEqual(plan["metadata"]["final_attributes"], "*")
        self.assertEqual(plan["metadata"]["final_count"], 0)
        self.assertEqual(plan["metadata"]["final_scope"], 3)
        self.assertEqual(plan["metadata"]["final_hostname"], "")
        self.assertEqual(plan["metadata"]["final_dn"], "")
        self.assertFalse(plan["metadata"]["final_ldaps"])

    def test_build_plan_normalizes_all_optional_values(self) -> None:
        plan = ldapsearch_parser.build_plan(
            self.make_args(
                "(samAccountType=805306368)",
                "--attributes",
                "cn,distinguishedName",
                "--count",
                "25",
                "--scope",
                "subtree",
                "--hostname",
                "\\\\DC01",
                "--dn",
                "DC=example,DC=test",
                "--ldaps",
            )
        )

        self.assertEqual(plan["metadata"]["final_attributes"], "cn,distinguishedName")
        self.assertEqual(plan["metadata"]["final_count"], 25)
        self.assertEqual(plan["metadata"]["final_scope"], 3)
        self.assertEqual(plan["metadata"]["final_hostname"], "DC01")
        self.assertEqual(plan["metadata"]["final_dn"], "DC=example,DC=test")
        self.assertTrue(plan["metadata"]["final_ldaps"])

    def test_build_plan_rejects_bad_scope(self) -> None:
        with self.assertRaisesRegex(ValueError, "scope must be"):
            ldapsearch_parser.build_plan(self.make_args("(objectClass=*)", "--scope", "forest"))

    def test_build_plan_rejects_bad_count(self) -> None:
        with self.assertRaisesRegex(ValueError, "count must be"):
            ldapsearch_parser.build_plan(self.make_args("(objectClass=*)", "--count", "abc"))

    def test_build_plan_rejects_space_separated_attributes(self) -> None:
        with self.assertRaisesRegex(ValueError, "attributes must be a comma-separated LDAP attribute list"):
            ldapsearch_parser.build_plan(
                self.make_args("(objectClass=*)", "--attributes", "cn dNSHostName")
            )

    def test_build_plan_rejects_malformed_hostname(self) -> None:
        with self.assertRaisesRegex(ValueError, "hostname should not include a port"):
            ldapsearch_parser.build_plan(self.make_args("(objectClass=*)", "--hostname", "dc01:636"))

    def test_build_plan_rejects_nul_strings(self) -> None:
        with self.assertRaisesRegex(ValueError, "query contains a NUL byte"):
            ldapsearch_parser.build_plan(self.make_args("abc\x00def"))


if __name__ == "__main__":
    unittest.main()
