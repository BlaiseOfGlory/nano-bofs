# listmods template notes

This template is based on the upstream SA `listmods` BOF and adapted for
nano-bofs.

## Main deviations

- The optional PID is embedded at build time instead of being parsed from BOF
  runtime arguments.
- Empty input is preserved as the upstream `pid == 0` behavior, which means
  "inspect the current process."
- The template adds a null-safe check around version translation info so a
  module without that metadata degrades into a printed error instead of reading
  through a bad pointer.

## Future maintenance

- If upstream SA changes the module output format, compare that first before
  adding any new normalization here.
- If this BOF ever shows partial module listings under Apollo, compare both the
  target process architecture and the `EnumProcessModulesEx` cross-arch note
  before assuming the template is at fault.
