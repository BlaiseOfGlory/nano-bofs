# netuptime template notes

This template is based on the upstream SA `netuptime` BOF and adapted for
nano-bofs.

## Main deviations

- The optional server argument is embedded at build time instead of being
  parsed from BOF runtime arguments.
- Empty input preserves local-host behavior; non-empty input is normalized and
  recorded as metadata.
- Execution is expected to run with no runtime BOF arguments.

## Future maintenance

- If upstream SA changes uptime-query formatting or behavior, review whether
  those changes should be ported here.
- If Windows uptime or host-query behavior changes, update both `entry.c` and
  `parser.py`.
