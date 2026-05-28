# windowlist template notes

This template is based on the upstream SA `windowlist` BOF and adapted for
nano-bofs.

## Main deviations

- The optional mode is embedded at build time instead of being parsed from BOF
  runtime arguments.
- The template preserves the upstream user-facing behavior exactly: empty input
  lists visible windows only, and the literal `all` includes hidden windows.
- The `ALL` toggle is set at runtime from the embedded value rather than being
  parsed from Beacon data before enumeration.

## Future maintenance

- If upstream SA changes the `all` toggle semantics, keep the empty/default
  behavior aligned first; that is the most user-visible part of this template.
- If this BOF ever returns no output on a live worker, compare it against the
  callback's session context before assuming the enumeration logic broke.
