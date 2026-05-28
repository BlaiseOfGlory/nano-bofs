# netshares template notes

This template is based on the upstream SA `netshares` BOF and adapted for
nano-bofs.

## Main deviations

- The optional server argument is embedded at build time instead of being
  parsed from BOF runtime arguments.
- Empty input preserves local-host behavior; non-empty input is normalized and
  recorded as metadata.
- The template currently focuses on the single-argument share-enumeration path.

## Future maintenance

- If upstream SA changes share enumeration or adds logic worth porting, review
  whether that should be brought over without changing the single-argument
  contract.
- Keep parser normalization and BOF behavior aligned if host-handling logic
  changes.
