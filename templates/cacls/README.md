# cacls template notes

This template is based on the upstream SA `cacls` BOF and adapted for
nano-bofs.

## Main deviations

- The path argument is embedded at build time instead of being parsed from BOF
  runtime arguments.
- The upstream string defines are inlined into the template so the generated
  source stays self-contained.
- The upstream runtime-built access-rights table is preserved as-is to avoid
  changing the BOF's output behavior during the port.
- The embedded path is copied onto the stack before the ACL walk. This matches
  the stable runtime shape we observed from the upstream SA BOF when Apollo
  passed the target as a `wchar` argument, and it fixed folder targets like
  `C:\Windows` and `C:\Projects`.
- The current template prints SID strings directly instead of resolving them to
  account names with `LookupAccountSidW`.

## Future maintenance

- If upstream SA changes the ACL formatting or the access-right mappings,
  review whether those should be copied over here.
- If we later want to harden this template further, the `LovingIt` pointer-table
  workaround is the first thing worth reconsidering.
- If folder handling regresses again, compare the generated template against
  the upstream `wchar`-argument execution path first; that was the key delta in
  the Apollo troubleshooting loop.
- If we revisit account-name resolution, treat it as a separate hardening step
  and revalidate it carefully on live Apollo workers.
