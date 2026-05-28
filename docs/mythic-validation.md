# Mythic Validation Guidance

The Mythic service is a command augmentation. It exposes `nb_*` commands to
existing callbacks and builds BOFs on demand from template metadata.

Use disposable worker callbacks for validation. Avoid using long-lived control
callbacks for BOF execution unless you explicitly intend to test there.

Recommended validation loop:

1. Confirm the `nano_bofs` service is online.
2. Run `nanobofs_sync` after metadata or parser changes if you do not restart
   the service.
3. Inspect the target `nb_*` command metadata in Mythic.
4. Task one BOF on a disposable worker callback.
5. If a task times out, inspect task status and output before treating it as a
   BOF failure.
6. If a worker stops checking in, retry on a fresh worker before classifying the
   BOF as unstable.

Metadata-readiness checks should use a fresh operator context where possible.
The operator should be able to infer required JSON fields, optional fields,
defaults, and examples from the live command metadata alone.
