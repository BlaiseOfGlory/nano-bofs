# tasklist template notes

This template is based on the upstream SA `tasklist` BOF and adapted for
nano-bofs.

## Main deviations

- The optional server argument is embedded at build time instead of being
  parsed from BOF runtime arguments.
- The template precomputes the WMI resource string instead of forwarding a raw
  host value to `Wmi_Connect`.
- Empty input preserves local-host behavior by connecting to `root\\cimv2` on
  the local machine.

## Future maintenance

- If upstream SA changes the selected process fields or output formatting,
  review whether that should be carried over without changing the single-arg
  contract.
- Keep the embedded WMI resource logic aligned with the shared `wmi.c`
  expectations if the WMI helper behavior changes.
