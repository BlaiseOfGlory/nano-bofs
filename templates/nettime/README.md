# nettime template notes

This template is based on the upstream SA `nettime` BOF and adapted for
nano-bofs.

## Main deviations

- The optional server argument is embedded at build time instead of being
  parsed from BOF runtime arguments.
- Empty input preserves local-host behavior; non-empty input is normalized and
  recorded as metadata.
- Execution is expected to run with no runtime BOF arguments.

## Future maintenance

- If upstream SA changes time-query formatting or behavior, review whether
  those changes should be ported here.
- If Windows time-query APIs or host-handling behavior change, update both
  `entry.c` and `parser.py`.
