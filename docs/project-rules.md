# nano-bofs Project Rules

## Human-Facing Text

- All human-facing text must be concise and operator friendly.
- Describe what the BOF does, not how nano-bofs packages or embeds it.
- Avoid implementation details in descriptions, help text, and variable labels unless they are directly useful to the operator.

## Template Descriptions

- Template descriptions should read like capability summaries.
- Match the intent and wording style of the original BOF documentation when practical.
- Good: `Check LDAP signing and LDAPS channel binding requirements on domain controllers.`
- Avoid: `Render a no-args BOF with embedded values.`

## Variable Descriptions

- Variable descriptions should describe the value the operator needs to provide.
- Keep them short and direct.
- Good: `Domain controller hostname or FQDN.`
- Avoid: `Domain controller hostname or FQDN used to generate the embedded ldap/<dc> SPN.`

## Errors

- Validation errors must be actionable.
- Tell the operator what is wrong and how to correct it.
- Prefer direct wording over Python or implementation terminology.
