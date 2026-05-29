# nano-bofs

<p align="center">
  <img src="Payload_Type/nano_bofs/nano_bofs_mythic/nano_bofs.png" alt="nano-bofs icon" width="180">
</p>

`nano-bofs` renders small, purpose-built BOFs (COFFs) from local templates by embedding operator-friendly inputs at build time. The generated BOF takes no runtime arguments, but still behaves as if the original values were supplied.

That gives operators a simpler workflow:
- inspect available templates
- inspect the expected inputs for one template
- build a one-off BOF with those values embedded
- run the resulting COFF without Beacon-style argument packing

## Quick Start

### Operators

Install `nano-bofs` as a UV tool from the GitHub repo:

```powershell
uv tool install git+https://github.com/BlaiseOfGlory/nano-bofs@v0.1.2
```

Pin a release tag or commit for repeatable installs. Avoid installing from a moving branch for operational use.

This installs both operator entrypoints:

- `nano-bofs` - standard text-oriented CLI
- `nano-bofsx` - AXI-oriented CLI output, or use `nano-bofs --axi`

The tool install includes the standard template set and shared C helpers needed by the CLI.

For AXI-style output conventions, see [axi.md](https://axi.md).

List templates:

```powershell
nano-bofs list
```

Inspect the expected inputs for a template:

```powershell
nano-bofs vars probe
```

Build a BOF:

```powershell
nano-bofs build --arch x64 probe dc01.example.test 445 10
```

By default, artifacts are written under `.nano-bofs/out`.

### Developers

Clone the repo and install the project environment:

```powershell
uv sync --frozen
```

Then use the project-local commands with `uv run`:

```powershell
uv run nano-bofs list
uv run nano-bofs vars probe
uv run nano-bofs build --arch x64 probe dc01.example.test 445 10
```

## Core Commands

The main operator commands are:

- `nano-bofs list` - list available templates
- `nano-bofs vars <template>` - show variables, examples, and validation rules
- `nano-bofs build <template> ...` - build a BOF from a template
- `nano-bofs audit` - audit template input-doc coverage
- `nano-bofs history` - inspect previous builds
- `nano-bofs config path|show` - inspect resolved configuration

Useful examples:

```powershell
nano-bofs vars netuse_add
nano-bofs build --arch x64 netuse_add \\192.0.2.10\IPC$
nano-bofs build probe 192.0.2.20 445 5 --metadata-out probe.json
nano-bofs config show
```

## Build Backends

`nano-bofs` supports:

- `auto`
- `docker`
- `local`

The configured default backend is resolved from:

1. user config
2. project config
3. local project override

You can also override the Docker builder image in config instead of changing code. For example:

```toml
[build]
docker_image = "freefirex2/ts_bof_builder:latest"
default_backend = "docker"
```

You can inspect the active paths with:

```powershell
uv run nano-bofs config path
```

And the resolved values with:

```powershell
uv run nano-bofs config show
```

Project defaults live in [`nano-bofs.toml`](nano-bofs.toml). Repo-local overrides belong in `nano-bofs.local.toml`, which is intentionally ignored.

## Template Model

The standard template source of truth is repo-root [`templates/`](templates). Installed CLI packages bundle that same tree under the `nano_bofs` package so operator installs can use templates without a source checkout.

Each template provides:
- a parser
- input metadata
- validation rules
- rendered build-time placeholders

This means the real operator documentation for a template is its parser metadata. If a template is hard to use from the CLI or Mythic, the parser metadata should usually be improved first.

## Mythic Augmentation

This repo also ships a Mythic command augmentation service under [`Payload_Type/nano_bofs/`](Payload_Type/nano_bofs).

Important behavior:

- the standard template set is baked into the Docker image at `/opt/nano-bofs-base/templates`
- mounted Mythic service templates at `/Mythic/templates` override the baked set
- `Payload_Type/nano_bofs/templates` is therefore an override/drop-in location, not the maintained standard template tree

The Mythic service is a `command_augmentation` container, so it exposes commands to existing callbacks rather than building payloads.

## Repo Layout

- [`src/nano_bofs/`](src/nano_bofs) - core library and CLI
- [`templates/`](templates) - standard BOF templates
- [`shared/`](shared) - shared C helpers and reusable support code
- [`Payload_Type/nano_bofs/`](Payload_Type/nano_bofs) - Mythic runtime packaging
- [`tests/`](tests) - regression coverage

## Status

Current tracked version: `0.1.2`.
