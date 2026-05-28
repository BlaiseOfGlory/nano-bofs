# mythicSmoke template notes

This is a nano-bofs-specific utility template used as a minimal Mythic/Apollo
COFF sanity check.

## Main deviations

- This is not a full upstream SA port; it is intentionally small and
  purpose-built.
- The template takes no runtime BOF arguments and prints a known-good success
  message.
- The goal is to validate registration, execution, and output capture with as
  little moving code as possible.

## Future maintenance

- Keep this template simple. Avoid adding logic that weakens its value as a
  smoke test.
- If Beacon/Mythic output expectations change, update the printed message
  format without turning this into a general-purpose BOF.
