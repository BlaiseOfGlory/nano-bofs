# netloggedon2 template notes

This template is based on the upstream SA `netloggedon2` BOF and adapted for
nano-bofs.

## Main deviations

- The optional server argument is embedded at build time instead of being
  parsed from BOF runtime arguments.
- Empty input preserves local-host behavior; non-empty input is normalized and
  recorded as metadata.
- The output is intended to preserve the BOFHound-friendly format while still
  following the nano-bofs build-time argument model.

## Future maintenance

- If upstream SA changes the BOFHound-oriented output format, review whether
  those changes should be ported here.
- Keep parser normalization and BOF behavior aligned if host-handling logic
  changes.
