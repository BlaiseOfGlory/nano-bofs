# get_password_policy template notes

This template is based on the upstream SA `get_password_policy` BOF and adapted
for nano-bofs.

## Main deviations

- The optional target server is embedded at build time instead of being parsed
  from BOF runtime arguments.
- Empty input preserves the local-host behavior, while non-empty input is
  normalized by `parser.py`.
- Metadata records the final normalized server value.

## Future maintenance

- If upstream SA changes parsing or output behavior, review whether those
  changes should be ported here.
- If Windows password policy or lockout API behavior changes, update `entry.c`
  and keep the parser metadata aligned with the actual BOF behavior.
