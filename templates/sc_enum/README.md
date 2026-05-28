# sc_enum template notes

This template is based on the upstream SA `sc_enum` BOF, but it intentionally
deviates in a few places to behave better in the nano-bofs + Apollo testing
path.

## Main deviations

- The target server is embedded at build time instead of being parsed from BOF
  runtime arguments.
- The upstream `anticrash.c` + dynamically allocated enum-string tables were
  replaced with static switch-based helper functions.
- The template adds defensive handling around service config, failure-action,
  and trigger data so malformed or unusual service records are more likely to
  degrade into partial output instead of a loader/runtime failure.
- The build uses `-fno-jump-tables` to reduce loader-sensitive compiler output.

## Why this exists

The stock upstream compiled `sc_enum` COFF failed under Apollo in this lab with
`RunCOFF failed with status: 1`, while the hardened template version executed
successfully and returned service output.

## Future maintenance

- If Windows introduces new service states, trigger types, trigger actions,
  startup types, error controls, or failure actions, update the switch helpers
  in `entry.c`.
- If those helpers are not updated, the BOF should still run, but some output
  may show `UNKNOWN` or `(FAILED TO RESOLVE)`.
- If upstream SA `sc_enum` changes meaningfully, review whether any new logic
  should be ported here without reintroducing the dynamic enum-table approach.
