# enum_filter_driver template notes

This template is based on the upstream SA `enum_filter_driver` BOF and adapted
for nano-bofs.

## Main deviations

- The optional computer argument is embedded at build time instead of being
  parsed from BOF runtime arguments.
- Empty input preserves local-host behavior by calling the registry APIs with a
  `NULL` computer name.
- Parser normalization records the final computer target in template metadata.

## Future maintenance

- If upstream SA expands the reported minifilter classes or changes its output
  shape, decide whether to mirror that here without changing the single-arg
  template contract.
- Keep host normalization and local-host handling aligned if the surrounding
  nano-bofs parser conventions change.
