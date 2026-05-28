# Third-Party Notices

This repository contains original `nano-bofs` code plus small vendored or
upstream-derived components. The root `LICENSE` applies to original
`nano-bofs` code. Third-party components retain their original notices.

## Vendored Python Packages

- `python-ldap-filter`
  - Source: `https://github.com/SteveEwell/python-ldap-filter`
  - Version: `1.0.1`
  - Commit: `c608ea4fc2b069a92703fde17e288794f19adb78`
  - License: MIT
  - Local copies:
    - `src/nano_bofs/_vendor/ldap_filter`
    - `Payload_Type/nano_bofs/src/nano_bofs/_vendor/ldap_filter`

See `docs/vendor-provenance.json` for the machine-readable provenance record.

## Upstream-Derived BOF Code

Several BOF templates and shared support files are derived from public BOF
projects, especially TrustedSec's Situational Awareness BOF work. The local
reference snapshot is recorded in `refs/manifest.json`.

Known notable notices:

- `shared/upstream/SA/whoami/entry.c` carries a ReactOS `whoami` GPL notice.
- `templates/adcs_enum/certca.h` carries a Microsoft copyright notice.

Before redistributing modified upstream-derived BOF code, review the notice in
the specific source file and the upstream project's license terms.
