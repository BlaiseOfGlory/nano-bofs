from __future__ import annotations

import sys
import unittest
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nano_bofs.input_validation import normalize_ldap_filter


class LdapFilterValidationTests(unittest.TestCase):
    def test_accepts_valid_ldap_filters(self) -> None:
        valid_filters = [
            "(objectClass=*)",
            "(objectClass=computer)",
            "(&(objectClass=user)(sAMAccountName=alice))",
            "(|(cn=DC01)(dNSHostName=DC01.example.test))",
            "(!(userAccountControl:1.2.840.113556.1.4.803:=2))",
            r"(cn=Alice\2a)",
        ]

        for query in valid_filters:
            with self.subTest(query=query):
                self.assertEqual(normalize_ldap_filter(query), query)

    def test_rejects_non_parenthesized_filters(self) -> None:
        with self.assertRaisesRegex(ValueError, "must look like an LDAP filter"):
            normalize_ldap_filter("objectClass=*")

    def test_rejects_malformed_ldap_filters(self) -> None:
        invalid_filters = [
            "(objectClass=*",
            "(|(cn=DC01)cn=WORKSTATION)",
            "(&(objectClass=user))trailing",
        ]

        for query in invalid_filters:
            with self.subTest(query=query):
                with self.assertRaisesRegex(ValueError, "must be a valid LDAP filter"):
                    normalize_ldap_filter(query)

    def test_rejects_malformed_ldap_escapes(self) -> None:
        with self.assertRaisesRegex(ValueError, "must use LDAP hex escapes"):
            normalize_ldap_filter(r"(cn=Alice\zz)")

    def test_rejects_empty_and_nul_values_before_parsing(self) -> None:
        with self.assertRaisesRegex(ValueError, "query is required"):
            normalize_ldap_filter("")
        with self.assertRaisesRegex(ValueError, "query contains a NUL byte"):
            normalize_ldap_filter("(cn=Alice\x00)")


if __name__ == "__main__":
    unittest.main()
