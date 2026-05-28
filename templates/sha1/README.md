# sha1 template notes

This template is based on the upstream SA `sha1` BOF and adapted for
nano-bofs.

## Main deviations

- The file path argument is embedded at build time instead of being parsed from
  BOF runtime arguments.
- The runtime hashing logic is otherwise kept very close to the upstream SA
  implementation.

## Future maintenance

- If upstream SA changes its hash formatting or CryptoAPI handling, review
  whether that should be mirrored here.
- This template currently expects an ASCII-safe path because it hashes files
  through `CreateFileA`.
