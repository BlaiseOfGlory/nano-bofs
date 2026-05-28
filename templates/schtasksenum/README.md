# schtasksenum template notes

This template is based on the upstream SA `schtasksenum` BOF and adapted for
nano-bofs.

## Main deviations

- The optional server argument is embedded at build time instead of being
  parsed from BOF runtime arguments.
- The upstream `anticrash.c` state-string setup is replaced with static helper
  mappings in the template entrypoint.
- Empty input preserves local-host behavior by connecting to the local task
  scheduler service.

## Future maintenance

- If Windows adds new task state values, update the local switch mapping so the
  BOF keeps printing friendly names instead of falling back to `UNKNOWN`.
- If upstream SA changes the folder-walk or XML-print behavior, review whether
  those updates should be carried into this template without changing the
  single-argument contract.
