# netLocalGroupList template notes

This template is based on the upstream SA `netLocalGroupList` BOF and adapted
for nano-bofs.

## Main deviations

- The optional server argument is embedded at build time instead of being
  parsed from BOF runtime arguments.
- Empty input preserves local-host behavior; non-empty input is normalized and
  recorded as metadata.
- The build uses `-fno-jump-tables` to reduce loader-sensitive compiler output.

## Future maintenance

- If upstream SA changes enumeration or output behavior, review whether those
  changes should be ported here.
- If Windows local-group APIs or host normalization assumptions change, update
  both `entry.c` and `parser.py`.
