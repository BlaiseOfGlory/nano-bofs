# ldapsecuritycheck template notes

This is a nano-bofs-specific LDAP security test template rather than a direct
upstream SA port.

## Main deviations

- The target DC is embedded at build time instead of being parsed from BOF
  runtime arguments.
- The template derives and records the final DC and LDAP SPN values during the
  build.
- Execution is expected to run with no runtime BOF arguments.

## Future maintenance

- If SSPI or LDAP bind behavior changes, revisit the result-handling logic in
  `entry.c`.
- If lab environments return different bind completion patterns, keep the
  interpretation logic aligned with the observed behavior instead of assuming a
  server token is always present.
