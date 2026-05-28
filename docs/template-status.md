# Template Status

`nano-bofs` exposes templates dynamically from the standard `templates/` tree.

Most templates are intended for normal operation. Templates with names ending in
`-experimental` or `-wip` are shipped for testing and refinement, but should be
treated as less stable than the normal template set.

## Experimental or Work-In-Progress Templates

- `netview-experimental`
- `sc_query-experimental`
- `vssenum-wip`

## Notes

- `reg_query_recursive` is available, but broad recursive registry queries can
  produce large outputs or agent-specific failures. Prefer narrow paths when
  validating a target environment.
- Template help and Mythic command metadata are generated from each template's
  parser metadata. If a command is hard to operate, improve the parser metadata
  first.
- Runtime behavior ultimately depends on the target host, callback agent, and
  available Windows APIs. Validate new templates against disposable worker
  callbacks before relying on them operationally.
