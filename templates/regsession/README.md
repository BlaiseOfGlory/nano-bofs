# regsession template notes

This template is based on the upstream SA `regsession` BOF and adapted for
nano-bofs.

## Main deviations

- The optional host argument is embedded at build time instead of being parsed
  from BOF runtime arguments.
- Empty input preserves local-host behavior; non-empty input is normalized and
  recorded as metadata.
- Execution is expected to run with no runtime BOF arguments.

## Future maintenance

- If upstream SA changes registry-hive enumeration or output behavior, review
  whether those changes should be ported here.
- If Windows registry-session behavior or host-handling logic changes, update
  both `entry.c` and `parser.py`.
