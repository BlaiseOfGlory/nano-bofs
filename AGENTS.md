# nano-bofs Repository Guide

This file is the committed, repo-specific guide for agents working on `nano-bofs`.

If a local developer has a private overlay at `./.agents/AGENTS.md`, read that too and treat it as environment-specific guidance layered on top of this file.

## Repo Boundary

- Stay inside the `nano-bofs` codebase by default.
- If a proposed fix or improvement would require editing files outside `nano-bofs`, stop after proposing the solution and ask the user for permission before making those edits.

## Project Layout

- Core Python package: `src/nano_bofs/`
- CLI entrypoints and operator UX: `src/nano_bofs/cli.py`
- Standard templates: `templates/`
- Shared C helpers and reusable upstream-derived support code: `shared/`
- Mythic augmentation service: `Payload_Type/nano_bofs/`
- Mythic runtime mirror of selected core modules: `Payload_Type/nano_bofs/src/nano_bofs/`
- Mythic service-specific code: `Payload_Type/nano_bofs/nano_bofs_mythic/`

## Source of Truth

- Treat repo-root `templates/` as the source of truth for standard templates.
- Treat repo-root parser modules as the source of truth for command metadata, validation, examples, and Mythic help quality.
- Treat `Payload_Type/nano_bofs/templates/` as an override/drop-in directory for installed-service custom templates, not as the maintained standard template set.
- The Dockerized Mythic service bakes the standard template set into `/opt/nano-bofs-base/templates` and checks mounted `/Mythic/templates` overrides first.

## Separation of Concerns

- The core package under `src/nano_bofs/` owns template discovery, rendering, build planning, config handling, and operator-facing CLI behavior.
- The CLI should remain a thin layer over core library behavior rather than inventing separate build logic.
- The Mythic service under `Payload_Type/nano_bofs/` is a packaging/runtime target for the same concepts, not a separate product with different template semantics.
- When core logic must also exist in the Mythic service runtime mirror, keep the two copies intentionally aligned.
- Avoid letting payload-side convenience code become the hidden source of truth for repo behavior.

## Mythic Integration Model

- `nano_bofs` is a `command_augmentation` container, not a normal payload-building agent.
- A command augmentation provides commands to existing callbacks rather than building payloads or defining C2 profiles.
- The supported OS and/or supported agent metadata controls which callbacks can load the augmentation's commands.
- The current service uses dynamic template discovery rather than a fixed pilot list.

## Command Discovery and Sync

- Mythic command discovery is dynamic:
  - templates are exposed unless their parser sets `MYTHIC_ENABLED = False`
  - the current Mythic readiness filter excludes parser shapes the UI bridge cannot represent cleanly yet
- Parser shapes that still need special handling include:
  - top-level `argparse` subparsers
  - generic positional `arguments` wrappers unless the template uses the explicit Mythic input bridge
- `nanobofs_sync` re-syncs the dynamic command set. Use it after parser metadata or `MYTHIC_ENABLED` changes when a full service restart is unnecessary.
- Mythic help text for `nb_*` commands is generated from template metadata:
  - command help uses template description, validation rules, and input notes
  - parameter help uses each variable's description, shape, example, default, and validation notes
  - if Mythic help looks weak, improve parser metadata first

## Template and Porting Guidance

- Treat the upstream BOF source and its operator wrapper layer as a combined contract. The source file alone is often not enough to recover the true argument model or default behavior.
- Some upstream BOFs expect Beacon-packed typed arguments rather than a raw `coff_arguments` string. Do not assume the two are equivalent.
- Lock upstream argument semantics before porting the parser. Optional arguments may still be packed and passed as empty typed values rather than omitted.
- When porting to build-time templating, preserve behavior first and change only the input mechanism.
- If multiple commands are thin wrappers over one upstream BOF, prefer one shared nano-bofs base template for the real C logic and keep wrappers parser-driven.
- Keep wrapper `entry.c` files minimal when they exist only for template discovery.

## Validation Guidance

- Check the Aggressor script or equivalent operator wrapper layer early, not just the source tree.
- If behavior is unclear, prove the upstream BOF first on the same target values when possible.
- For remote-target templates, inspect the rendered source early and verify final embedded path/host string shape, not just parser logic.
- Keep live validation linear when stability is in doubt. One artifact at a time makes failures easier to classify.
- Before blaming a remote BOF, validate the same target with the equivalent shell command on the same worker.
- Treat timeouts as ambiguous until task state confirms what happened.
- If a BOF appears to hang or kill the worker, add temporary checkpoint output around major API stages and flush between them.

## Local Dev Artifacts

- `Payload_Type/nano_bofs/rabbitmq_config.json` is a local developer config file and is intentionally ignored.
- `Payload_Type/nano_bofs/rabbitmq_config.json.example` is the committed example.
- `Payload_Type/nano_bofs/.venv-win/`, `Payload_Type/nano_bofs/.nano-bofs-state/`, and `Payload_Type/nano_bofs/*.log` are local runtime artifacts and should remain untracked.
