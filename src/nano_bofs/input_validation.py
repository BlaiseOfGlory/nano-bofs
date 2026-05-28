from __future__ import annotations

"""Shared parser normalizers for common nano-bofs input families.

Template authors should use these helpers first, then layer any stricter
template-specific checks in parser.py rather than duplicating the common
shape validation rules, including the LDAP, WMI, and registry/service/share
helpers below.
"""

import re
from typing import Any

from nano_bofs._vendor.ldap_filter import Filter
from nano_bofs._vendor.ldap_filter import ParseError

_DNS_LABEL_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
_NETBIOS_DOMAIN_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,14})$")
_HEX_DIGITS = set("0123456789abcdefABCDEF")
REGISTRY_HIVE_VALUES: dict[str, int] = {
    "HKCR": 0,
    "HKCU": 1,
    "HKLM": 2,
    "HKU": 3,
}


def ensure_no_nul(value: str, label: str) -> str:
    if "\x00" in value:
        raise ValueError(f"{label} contains a NUL byte, which cannot be embedded into the BOF source.")
    return value


def ensure_ascii(value: str, label: str) -> str:
    try:
        value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{label} must be ASCII for this BOF.") from exc
    return value


def normalize_optional_ascii_text(value: str | None, label: str) -> str:
    if value is None:
        return ""
    return ensure_ascii(ensure_no_nul(value.strip(), label), label)


def normalize_required_ascii_text(value: str, label: str) -> str:
    text = normalize_optional_ascii_text(value, label)
    if not text:
        raise ValueError(f"{label} is required.")
    return text


def normalize_domain_like(
    value: str | None,
    *,
    label: str = "domain",
    allow_empty: bool = True,
    strip_leading_unc: bool = True,
) -> str:
    domain = normalize_optional_ascii_text(value, label)
    if strip_leading_unc and domain.startswith("\\\\"):
        domain = domain[2:]
    if not domain:
        if allow_empty:
            return ""
        raise ValueError(f"{label} is required.")
    lower = domain.lower()
    if lower.startswith(("http://", "https://", "ldap://", "ldaps://", "tcp://")):
        raise ValueError(f"{label} must be a plain DNS or NetBIOS domain value, not a URL.")
    if domain.startswith("//"):
        raise ValueError(f"{label} must be a plain DNS or NetBIOS domain value, not a UNC path.")
    if "/" in domain or "\\" in domain:
        raise ValueError(f"{label} must be a single domain value, not a path or UNC string.")
    if ":" in domain:
        raise ValueError(f"{label} should not include a port.")
    if any(ch.isspace() for ch in domain):
        raise ValueError(f"{label} must not contain spaces. Pass a DNS or NetBIOS domain value only.")
    if len(domain) > 255:
        raise ValueError(f"{label} is too long to be a viable domain value. Keep it to 255 characters or fewer.")
    if "." in domain:
        labels = domain.split(".")
        if any(not part for part in labels):
            raise ValueError(f"{label} must be a plain DNS or NetBIOS domain value, not a dotted path with empty labels.")
        if any(len(part) > 63 for part in labels):
            raise ValueError(f"{label} contains a DNS label longer than 63 characters.")
        if any(_DNS_LABEL_RE.fullmatch(part) is None for part in labels):
            raise ValueError(f"{label} must be a valid DNS domain value using only letters, digits, and internal hyphens.")
        return domain
    if _NETBIOS_DOMAIN_RE.fullmatch(domain) is None:
        raise ValueError(f"{label} must be a valid NetBIOS domain value using 1-15 letters, digits, or hyphens.")
    return domain


def normalize_host_like(
    value: str | None,
    *,
    label: str,
    allow_empty: bool,
    default: str = "",
    strip_leading_unc: bool = True,
    allow_dot: bool = False,
    allow_ipv4: bool = True,
) -> str:
    host = normalize_optional_ascii_text(value, label)
    if not host:
        if allow_empty:
            return default
        raise ValueError(f"{label} is required.")
    if allow_dot and host == ".":
        return host
    lower = host.lower()
    if lower.startswith(("http://", "https://", "ldap://", "ldaps://", "tcp://")):
        raise ValueError(f"{label} must be a host name or IP, not a URL.")
    if host.startswith("//"):
        raise ValueError(f"{label} must be a single host value, not a UNC path or share.")
    if strip_leading_unc and host.startswith("\\\\"):
        host = host[2:]
    host = host.strip()
    if not host:
        if allow_empty:
            return default
        raise ValueError(f"{label} value is not usable after normalization.")
    if "/" in host or "\\" in host:
        raise ValueError(f"{label} must be a single host value, not a path or UNC share.")
    if ":" in host:
        raise ValueError(f"{label} should not include a port.")
    if any(ch.isspace() for ch in host):
        raise ValueError(f"{label} must not contain spaces.")
    if len(host) > 255:
        raise ValueError(f"{label} is too long to be a viable host value. Keep it to 255 characters or fewer.")
    return host


def normalize_int_range(
    value: str,
    *,
    label: str,
    minimum: int,
    maximum: int,
) -> int:
    text = ensure_no_nul(value, label).strip()
    if not text:
        raise ValueError(f"{label} is required.")
    if any(ch.isspace() for ch in text):
        raise ValueError(f"{label} must not contain spaces. Pass a base-10 integer.")
    try:
        parsed = int(text, 10)
    except ValueError as exc:
        raise ValueError(f"{label} must be a base-10 integer.") from exc
    if parsed < minimum or parsed > maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}.")
    return parsed


def normalize_registry_hive(value: str, *, label: str = "hive") -> tuple[str, int]:
    hive = normalize_required_ascii_text(value, label).upper()
    if hive not in REGISTRY_HIVE_VALUES:
        valid = ", ".join(REGISTRY_HIVE_VALUES)
        raise ValueError(f"{label} must be one of {valid}.")
    return hive, REGISTRY_HIVE_VALUES[hive]


def normalize_registry_path(value: str, *, label: str = "path") -> str:
    path = normalize_required_ascii_text(value, label)
    if path.upper().startswith(tuple(f"{hive}\\" for hive in REGISTRY_HIVE_VALUES)):
        raise ValueError(f"{label} should be relative to the hive, not include the hive prefix again.")
    if "/" in path:
        raise ValueError(f"{label} must use registry backslashes, not forward slashes.")
    return path


def normalize_registry_value_name(value: str | None, *, label: str = "value") -> str:
    return normalize_optional_ascii_text(value, label)


def normalize_service_name(
    value: str | None,
    *,
    label: str = "service_name",
    allow_empty: bool = False,
) -> str:
    service_name = normalize_optional_ascii_text(value, label)
    if not service_name:
        if allow_empty:
            return ""
        raise ValueError(f"{label} is required. Pass a service like WebClient or LanmanWorkstation.")
    if len(service_name) > 256:
        raise ValueError(f"{label} is too long. Keep it to 256 characters or fewer.")
    return service_name


def normalize_unc_share(value: str, *, label: str = "share") -> str:
    share = normalize_required_ascii_text(value, label)
    if "/" in share:
        raise ValueError(f"{label} must use backslashes, not forward slashes.")
    if not share.startswith("\\\\"):
        raise ValueError(f"{label} must be a UNC path like \\\\HOST\\Share.")
    unc_parts = share[2:].split("\\")
    if len(unc_parts) < 2 or not unc_parts[0] or not unc_parts[1]:
        raise ValueError(f"{label} must be a UNC path like \\\\HOST\\Share.")
    return share


def normalize_device_name(
    value: str | None,
    *,
    label: str = "device",
    allow_empty: bool = True,
) -> str:
    device = normalize_optional_ascii_text(value, label)
    if not device:
        if allow_empty:
            return ""
        raise ValueError(f"{label} is required.")
    if len(device) == 1 and device.isalpha():
        return device.upper() + ":"
    if len(device) == 2 and device[0].isalpha() and device[1] == ":":
        return device.upper()
    raise ValueError(f"{label} must look like X or X:.")


def normalize_optional_boolish(value: str | None, *, label: str) -> bool:
    text = normalize_optional_ascii_text(value, label).lower()
    if not text:
        return False
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(
        f"{label} must be one of true/false, yes/no, on/off, or 1/0."
    )


def normalize_ldap_filter(value: str, *, label: str = "query") -> str:
    query = normalize_required_ascii_text(value, label)
    if not query.startswith("("):
        raise ValueError(f"{label} must look like an LDAP filter such as (objectClass=*).")
    _ensure_valid_ldap_escapes(query, label)
    try:
        Filter.parse(query)
    except ParseError as exc:
        detail = str(exc).splitlines()[0] if str(exc) else "invalid LDAP filter"
        raise ValueError(f"{label} must be a valid LDAP filter: {detail}") from exc
    return query


def _ensure_valid_ldap_escapes(query: str, label: str) -> None:
    index = 0
    while index < len(query):
        if query[index] != "\\":
            index += 1
            continue
        if index + 2 >= len(query) or any(ch not in _HEX_DIGITS for ch in query[index + 1:index + 3]):
            raise ValueError(f"{label} must use LDAP hex escapes like \\28, \\29, \\2a, \\5c, or \\00.")
        index += 3


def normalize_ldap_dn(
    value: str | None,
    *,
    label: str = "dn",
    allow_empty: bool = True,
) -> str:
    dn = normalize_optional_ascii_text(value, label)
    if not dn:
        if allow_empty:
            return ""
        raise ValueError(f"{label} is required.")
    lower = dn.lower()
    if lower.startswith(("ldap://", "ldaps://", "http://", "https://")):
        raise ValueError(f"{label} must be a distinguished name, not a URL.")
    if dn.startswith(("\\\\", "//")) or "/" in dn:
        raise ValueError(f"{label} must be a distinguished name, not a path or UNC value.")
    if "=" not in dn:
        raise ValueError(f"{label} must look like a distinguished name such as DC=corp,DC=local.")
    return dn


def normalize_ldap_scope(value: str, *, label: str = "scope") -> int:
    raw = normalize_required_ascii_text(value, label).lower()
    scope_aliases = {
        "1": 1,
        "base": 1,
        "2": 2,
        "one": 2,
        "onelevel": 2,
        "level": 2,
        "3": 3,
        "subtree": 3,
        "sub": 3,
    }
    if raw not in scope_aliases:
        raise ValueError(f"{label} must be 1, 2, 3, base, one, onelevel, level, or subtree.")
    return scope_aliases[raw]


def normalize_wql_query(value: str, *, label: str = "query") -> str:
    query = normalize_required_ascii_text(value, label)
    upper = query.upper()
    if not upper.startswith(("SELECT ", "ASSOCIATORS OF ", "REFERENCES OF ")):
        raise ValueError(f"{label} must look like a WQL query such as SELECT ... FROM ....")
    return query


def normalize_wmi_namespace(
    value: str | None,
    *,
    label: str = "namespace",
    default: str = "",
) -> str:
    namespace = normalize_optional_ascii_text(value, label)
    if not namespace:
        return default
    if namespace.startswith("\\"):
        namespace = namespace.lstrip("\\")
    if "/" in namespace:
        raise ValueError(f"{label} must use backslashes, not forward slashes.")
    return namespace


VARIABLE_DOC_FALLBACKS: dict[str, dict[str, Any]] = {
    "domain": {
        "shape": "Single DNS or NetBIOS domain value.",
        "example": "example.test",
        "validation": [
            "Rejects URLs, UNC/path values, ports, spaces, and overlong values.",
            "Small normalizations such as trimming and leading \\\\ stripping may be applied by some templates.",
        ],
    },
    "server": {
        "shape": "Single host value, often a bare hostname, FQDN, or '.'.",
        "example": "WORKSTATION",
        "validation": [
            "Rejects URLs, paths, ports, spaces, and overlong values.",
            "Some templates strip a leading \\\\ before validation.",
        ],
    },
    "computer": {
        "shape": "Single host value.",
        "example": "DC01",
        "validation": [
            "Rejects LDAP/URL forms, paths, ports, spaces, and overlong values.",
        ],
    },
    "hostname": {
        "shape": "Single hostname or IP value.",
        "example": "dc01.example.test",
        "validation": [
            "Rejects URLs, paths, spaces, and overlong values.",
        ],
    },
    "host": {
        "shape": "Single hostname or IP value.",
        "example": "10.0.0.5",
        "validation": [
            "Rejects URLs, paths, spaces, and overlong values.",
        ],
    },
    "dns_server": {
        "shape": "Single IPv4 address or an empty/default sentinel depending on the template.",
        "example": "192.0.2.53",
        "validation": [
            "Rejects malformed addresses and space-separated values.",
        ],
    },
    "port": {
        "shape": "Base-10 integer within the template's allowed range.",
        "example": "445",
        "validation": [
            "Rejects non-integer values and out-of-range ports.",
        ],
    },
    "timeout": {
        "shape": "Base-10 integer timeout value.",
        "example": "10",
        "validation": [
            "Rejects non-integer values and out-of-range timeouts.",
        ],
    },
    "query": {
        "shape": "Single ASCII query string interpreted by the target BOF.",
        "example": "SELECT Name FROM Win32_ComputerSystem",
        "validation": [
            "Rejects empty values and NUL bytes.",
        ],
    },
    "namespace": {
        "shape": "Single WMI namespace path.",
        "example": r"root\cimv2",
        "validation": [
            "Rejects NUL bytes and forward-slash path shapes.",
        ],
    },
    "path": {
        "shape": "Single template-specific path string.",
        "example": r"C:\Windows\Temp",
        "validation": [
            "Rejects NUL bytes and may enforce template-specific separator or prefix rules.",
        ],
    },
    "hive": {
        "shape": "Single registry hive token.",
        "example": "HKLM",
        "validation": [
            "Rejects values outside the supported hive list for the template.",
        ],
    },
    "value": {
        "shape": "Single optional value name.",
        "example": "Debugger",
        "validation": [
            "Rejects NUL bytes.",
        ],
    },
    "groupname": {
        "shape": "Single group name string.",
        "example": "Domain Admins",
        "validation": [
            "Rejects empty values and overlong names.",
        ],
    },
    "service_name": {
        "shape": "Single Windows service name.",
        "example": "WebClient",
        "validation": [
            "Rejects empty values and overlong names.",
        ],
    },
    "share": {
        "shape": "UNC share path.",
        "example": r"\\HOST\Share",
        "validation": [
            "Rejects non-UNC values and malformed host/share shapes.",
        ],
    },
    "sharename": {
        "shape": "UNC share path.",
        "example": r"\\HOST\Share",
        "validation": [
            "Rejects non-UNC values and malformed host/share shapes.",
        ],
    },
    "device": {
        "shape": "Single drive token.",
        "example": "Z:",
        "validation": [
            "Accepts X or X: and normalizes to uppercase X:.",
        ],
    },
    "taskpath": {
        "shape": "Full scheduled-task path starting with a backslash.",
        "example": r"\Microsoft\Windows\MUI\LpRemove",
        "validation": [
            "Rejects malformed task paths and forward-slash forms.",
        ],
    },
    "record_type": {
        "shape": "Single DNS record-type token.",
        "example": "A",
        "validation": [
            "Unknown values may fall back to a template default.",
        ],
    },
    "username": {
        "shape": "Single user or account name string.",
        "example": "domainadmin",
        "validation": [
            "Rejects empty values and NUL bytes.",
        ],
    },
    "target": {
        "shape": "Single template-specific target token.",
        "example": r"\\SERVER\Share",
        "validation": [
            "Validation depends on the command mode for the template.",
        ],
    },
    "scope": {
        "shape": "Single scope token accepted by the template.",
        "example": "subtree",
        "validation": [
            "Rejects unsupported scope values.",
        ],
    },
    "filter": {
        "shape": "Single filter token or expression accepted by the template.",
        "example": "(objectClass=*)",
        "validation": [
            "Rejects malformed or unsupported filter values for the template.",
        ],
    },
}
