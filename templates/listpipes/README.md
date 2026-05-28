# listpipes

This template is a nano-bofs-native implementation.

The upstream SA entry for `listpipes` is only a C2 alias that lists `//./pipe/`; there is no upstream BOF source under `refs/CS-Situational-Awareness-BOF/src/SA` to port directly.

## Main deviations

- Implemented as a local zero-argument BOF that enumerates `\\\\.\\pipe\\*` with `FindFirstFileW` / `FindNextFileW`.
- Keeps the operator-facing behavior simple: print each pipe name and a final total.

## Maintenance notes

- If the upstream project later adds a real `listpipes` BOF, compare its output and error-handling behavior before replacing this implementation.
- This version only enumerates local named pipes; it does not add filtering or remote targeting.
