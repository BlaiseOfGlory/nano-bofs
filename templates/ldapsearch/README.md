# ldapsearch template notes

This template is based on the upstream SA `ldapsearch` BOF and keeps the LDAP
search logic close to upstream, while shifting operator input handling into the
nano-bofs build step.

## Main deviations

- The query, attributes, count, scope, hostname, base DN, and LDAPS toggle are
  embedded at build time instead of being unpacked from BOF runtime arguments.
- The template keeps upstream defaults from the SA wrapper, including
  `attributes="*"`, `count=0`, `scope=3`, empty hostname, empty DN, and LDAPS
  disabled unless requested.
- `nano-bofs vars ldapsearch` is intended to show the richer flag interface so
  operators can see the supported options and defaults before building.

## Future maintenance

- If upstream `ldapsearch` changes its packed argument order or default flag
  semantics, keep this template aligned with the upstream user-facing contract.
- If Apollo exposes loader or runtime instability in the stock implementation,
  harden the template only where needed and document any resulting deviation.
