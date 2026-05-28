# netloggedon template notes

This template is based on the upstream SA `netloggedon` BOF and adapted for
nano-bofs.

## Main deviations

- The optional server argument is embedded at build time instead of being
  parsed from BOF runtime arguments.
- Empty input preserves local-host behavior; non-empty input is normalized and
  recorded as metadata.
- Execution is expected to run with no runtime BOF arguments.

## Future maintenance

- If upstream SA changes logged-on-user enumeration or formatting, review
  whether those changes should be ported here.
- Keep parser normalization and BOF behavior aligned if host-handling logic
  changes.
