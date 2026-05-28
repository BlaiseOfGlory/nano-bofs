# netGroupList template notes

This template is based on the upstream SA `netGroupList` BOF and adapted for
nano-bofs.

## Main deviations

- The optional domain argument is embedded at build time instead of being
  parsed from BOF runtime arguments.
- Empty input preserves the runtime default-domain behavior; non-empty input is
  normalized and recorded as metadata.
- The build uses `-fno-jump-tables` to reduce loader-sensitive compiler output.

## Future maintenance

- If upstream SA changes group enumeration or output behavior, review whether
  those changes should be ported here.
- If domain-handling behavior changes, keep the parser normalization, metadata,
  and BOF logic in sync.
