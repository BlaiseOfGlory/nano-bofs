from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from nano_bofs.builder import artifact_paths
from nano_bofs.builder import build_artifacts
from nano_bofs.builder import build_index_path
from nano_bofs.builder import create_staging_dir
from nano_bofs.builder import source_path
from nano_bofs.config import ResolvedConfig
from nano_bofs.config import load_config
from nano_bofs.input_validation import VARIABLE_DOC_FALLBACKS
from nano_bofs.pathing import templates_root
from nano_bofs.pathing import workspace_root
from nano_bofs.renderers import render_error
from nano_bofs.renderers import render_payload


CLI_DESCRIPTION = "Render embedded-input BOF artifacts from local templates."
PROJECT_ROOT = workspace_root()
TEMPLATES_ROOT = templates_root()
OUTPUT_FORMATS = {"text", "toon", "json"}


class CliError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: int = 1,
        usage: str | None = None,
        help_items: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message.strip()
        self.code = code
        self.usage = usage.strip() if usage else None
        self.help_items = [item.strip() for item in (help_items or []) if item.strip()]


class NanoArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CliError(message, code=2, usage=self.format_usage().rstrip())

    def exit(self, status: int = 0, message: str | None = None) -> None:
        if status == 0:
            if message:
                self._print_message(message, sys.stdout)
            raise SystemExit(0)
        raise CliError((message or "").strip(), code=status, usage=self.format_usage().rstrip())


def discover_templates() -> list[str]:
    names: list[str] = []
    if not TEMPLATES_ROOT.exists():
        return names
    for child in sorted(TEMPLATES_ROOT.iterdir()):
        if child.is_dir() and (child / "parser.py").exists():
            names.append(child.name)
    return names


def load_template_module(name: str) -> ModuleType:
    parser_path = TEMPLATES_ROOT / name / "parser.py"
    if not parser_path.exists():
        raise CliError(f"unknown template: {name}", code=2)

    module_name = f"nano_bofs_template_{name}"
    spec = importlib.util.spec_from_file_location(module_name, parser_path)
    if spec is None or spec.loader is None:
        raise CliError(f"failed to load parser module for {name}", code=1)

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def create_template_parser(
    template: str,
    module: ModuleType,
    *,
    binary_name: str,
    formatter_class: type[argparse.HelpFormatter] | None = None,
) -> argparse.ArgumentParser:
    kwargs: dict[str, object] = {
        "prog": f"{binary_name} build {template}",
        "description": getattr(module, "DESCRIPTION", None),
    }
    if formatter_class is not None:
        kwargs["formatter_class"] = formatter_class
    parser = NanoArgumentParser(**kwargs)
    add_output_arguments(parser)
    module.add_arguments(parser)
    return parser


def add_output_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=["text", "toon", "json"],
        help="Render output as text, TOON, or JSON.",
    )
    parser.add_argument(
        "--axi",
        action="store_true",
        help="Shortcut for --format toon.",
    )


def normalize_binary_name(raw_value: str) -> str:
    candidate = Path(raw_value).name or "nano-bofs"
    if candidate.lower().endswith(".exe"):
        return Path(candidate).stem
    return candidate


def extract_output_format(argv: list[str], default_format: str) -> tuple[list[str], str]:
    cleaned: list[str] = []
    selected = default_format
    index = 0
    while index < len(argv):
        current = argv[index]
        if current == "--axi":
            selected = "toon"
            index += 1
            continue
        if current == "--format":
            if index + 1 >= len(argv):
                raise CliError("--format requires one of: text, toon, json.", code=2)
            candidate = argv[index + 1].strip().lower()
            if candidate not in OUTPUT_FORMATS:
                raise CliError(
                    f"--format must be one of: text, toon, json. Received: {argv[index + 1]!r}.",
                    code=2,
                )
            selected = candidate
            index += 2
            continue
        if current.startswith("--format="):
            candidate = current.split("=", 1)[1].strip().lower()
            if candidate not in OUTPUT_FORMATS:
                raise CliError(
                    f"--format must be one of: text, toon, json. Received: {candidate!r}.",
                    code=2,
                )
            selected = candidate
            index += 1
            continue
        cleaned.append(current)
        index += 1
    return cleaned, selected


def _as_list_of_dicts(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _as_list_of_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _is_required_action(action: argparse.Action) -> bool:
    if getattr(action, "required", False):
        return True
    if action.option_strings:
        return False
    return action.nargs not in ("?", "*")


def _inferred_variables_from_parser(parser: argparse.ArgumentParser) -> list[dict[str, object]]:
    inferred: list[dict[str, object]] = []
    for action in parser._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        if isinstance(action, argparse._SubParsersAction):
            inferred.append(
                {
                    "name": action.dest or "command",
                    "required": True,
                    "description": action.help or "Template subcommand selector.",
                }
            )
            continue
        if action.dest in {"format", "axi"}:
            continue
        if not action.dest or action.dest == argparse.SUPPRESS:
            continue
        inferred.append(
            {
                "name": action.dest,
                "required": _is_required_action(action),
                "description": action.help or "",
            }
        )
    return inferred


def _merge_variables(module_variables: list[dict[str, object]], parser_variables: list[dict[str, object]]) -> list[dict[str, object]]:
    merged: list[dict[str, object]] = []
    index_by_name: dict[str, int] = {}
    seen: set[str] = set()
    for item in module_variables + parser_variables:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        if name in seen:
            idx = index_by_name[name]
            merged[idx] = {**merged[idx], **item}
            continue
        seen.add(name)
        index_by_name[name] = len(merged)
        merged.append(dict(item))
    return merged


def _apply_variable_fallbacks(variables: list[dict[str, object]]) -> list[dict[str, object]]:
    resolved: list[dict[str, object]] = []
    for variable in variables:
        name = str(variable.get("name", "")).strip()
        fallback = VARIABLE_DOC_FALLBACKS.get(name, {})
        merged = dict(variable)
        for key in ("shape", "example"):
            if not str(merged.get(key, "")).strip() and key in fallback:
                merged[key] = fallback[key]
        validation = merged.get("validation", [])
        validation_list = [item for item in validation if isinstance(item, str) and item.strip()] if isinstance(validation, list) else []
        if not validation_list and "validation" in fallback:
            merged["validation"] = list(fallback["validation"])
        resolved.append(merged)
    return resolved


def _resolve_template_docs(template: str, module: ModuleType, *, binary_name: str) -> tuple[list[dict[str, object]], list[str], list[str]]:
    parser = create_template_parser(
        template,
        module,
        binary_name=binary_name,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    raw_variables = _as_list_of_dicts(getattr(module, "VARIABLES", []))
    inferred_variables = _inferred_variables_from_parser(parser)
    variables = _apply_variable_fallbacks(_merge_variables(raw_variables, inferred_variables))
    validation_rules = _as_list_of_strings(getattr(module, "VALIDATION_RULES", []))
    input_notes = _as_list_of_strings(getattr(module, "INPUT_NOTES", []))

    if not variables:
        validation_rules = validation_rules or [
            "This template takes no build-time inputs.",
            "The generated BOF takes no runtime arguments.",
        ]
        input_notes = input_notes or [
            f"Use `{binary_name} build {template}` to render the BOF directly.",
        ]
        return variables, validation_rules, input_notes

    validation_rules = validation_rules or [
        "Inputs are validated at build time before BOF source rendering.",
        "The generated BOF takes no runtime arguments.",
    ]
    input_notes = input_notes or [
        f"Use `{binary_name} build {template} --help` for the exact argument order and defaults.",
    ]
    return variables, validation_rules, input_notes


def render_build(
    config: ResolvedConfig,
    module: ModuleType,
    template_args: argparse.Namespace,
    output_override: Path | None,
    arch: str,
    backend: str,
) -> tuple[dict[str, dict[str, str]], Path, dict[str, object], str]:
    plan = module.build_plan(template_args)
    requested_output_paths = artifact_paths(output_override, str(plan["artifact_basename"]), arch)
    staging_dir = create_staging_dir(config, str(getattr(module, "NAME", "template")))
    rendered_source_path = source_path(staging_dir, str(plan["source_name"]))
    rendered = module.render_plan(plan)
    rendered_source_path.parent.mkdir(parents=True, exist_ok=True)
    rendered_source_path.write_text(rendered, encoding="utf-8", newline="\n")
    user_inputs = dict(vars(template_args))
    selected_backend, build_records = build_artifacts(
        config=config,
        template_name=str(getattr(module, "NAME", "template")),
        build_spec=dict(plan["build"]),
        source_path_value=rendered_source_path,
        requested_output_paths=requested_output_paths,
        backend=backend,
        user_inputs=user_inputs,
        metadata=dict(plan.get("metadata", {})),
    )
    return build_records, rendered_source_path, plan, selected_backend


def load_config_or_raise() -> ResolvedConfig:
    try:
        return load_config()
    except ValueError as exc:
        raise CliError(f"error loading config: {exc}") from exc


def load_history_entries(config: ResolvedConfig) -> list[dict[str, object]]:
    index_path = build_index_path(config)
    if not index_path.exists():
        return []

    entries: list[dict[str, object]] = []
    for line in index_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        entries.append(json.loads(line))
    return entries


def normalize_history_entry(entry: dict[str, object]) -> dict[str, object]:
    user_inputs = entry.get("user_inputs", {})
    final_values = entry.get("final_values", entry.get("metadata", {}))
    return {
        "built_at": str(entry.get("built_at", "")),
        "template": str(entry.get("template", "")),
        "architecture": str(entry.get("architecture", "")),
        "backend": str(entry.get("backend", "")),
        "artifact": str(entry.get("artifact", "")),
        "md5": str(entry.get("md5", "")),
        "md5_suffix": str(entry.get("md5_suffix", "")),
        "inputs": dict(user_inputs) if isinstance(user_inputs, dict) else {},
        "final": dict(final_values) if isinstance(final_values, dict) else {},
    }


def select_history_entries(
    entries: list[dict[str, object]],
    *,
    query: str | None,
    first: int | None,
    last: int | None,
) -> list[dict[str, object]]:
    filtered_entries = entries
    needle = query.lower() if query else None
    if needle and needle != "all":
        matched: list[dict[str, object]] = []
        for entry in entries:
            artifact_name = Path(str(entry.get("artifact", ""))).name
            haystacks = [
                str(entry.get("template", "")),
                artifact_name,
                str(entry.get("md5", "")),
                str(entry.get("md5_suffix", "")),
            ]
            if any(needle in item.lower() for item in haystacks):
                matched.append(entry)
        filtered_entries = matched

    if first is not None:
        return filtered_entries[:first]
    if last is not None:
        return list(reversed(filtered_entries[-last:]))
    if needle:
        return list(reversed(filtered_entries))
    if filtered_entries:
        return [filtered_entries[-1]]
    return []


def build_dashboard_payload(binary_name: str) -> dict[str, Any]:
    config = load_config_or_raise()
    entries = load_history_entries(config)
    recent_rows = [normalize_history_entry(entry) for entry in reversed(entries[-3:])]
    help_items = [
        f"Run `{binary_name} list` to see templates.",
        f"Run `{binary_name} vars <template>` to inspect input shape.",
        f"Run `{binary_name} history all` to review prior builds.",
    ]

    text_lines = [
        f"bin: {binary_name}",
        f"description: {CLI_DESCRIPTION}",
        "",
    ]
    if recent_rows:
        text_lines.append("recent builds:")
        for row in recent_rows:
            text_lines.append(
                f"- {row['template']} {row['architecture']} {row['backend']} {row['md5_suffix']}"
            )
    else:
        text_lines.append("recent builds: 0 builds found.")
    text_lines.append("")
    text_lines.append("help:")
    for item in help_items:
        text_lines.append(f"- {item}")

    return {
        "data": {
            "bin": binary_name,
            "description": CLI_DESCRIPTION,
            "recent_builds": recent_rows,
            "help": help_items,
        },
        "sections": [
            {
                "type": "fields",
                "fields": {
                    "bin": binary_name,
                    "description": CLI_DESCRIPTION,
                },
            },
            {
                "type": "table",
                "name": "recent_builds",
                "fields": ["template", "architecture", "backend", "md5_suffix"],
                "rows": recent_rows,
                "empty": "0 builds found in this workspace.",
            },
            {
                "type": "messages",
                "name": "help",
                "items": help_items,
            },
        ],
        "text_lines": text_lines,
    }


def create_build_base_parser(binary_name: str, *, add_help: bool = True) -> NanoArgumentParser:
    parser = NanoArgumentParser(prog=f"{binary_name} build", add_help=add_help)
    add_output_arguments(parser)
    parser.add_argument("template", choices=discover_templates())
    parser.add_argument(
        "--arch",
        choices=["both", "x64", "x86"],
        default="both",
        help="Architecture to build. Defaults to both x64 and x86.",
    )
    parser.add_argument(
        "--backend",
        choices=["auto", "docker", "local"],
        default=None,
        help="Build backend to use. Defaults to the configured backend.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file or directory for the final BOF artifacts. Defaults to the configured output directory.",
    )
    parser.add_argument(
        "--metadata-out",
        type=Path,
        help="Optional path to write build metadata as JSON.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Compatibility alias for --format json.",
    )
    return parser


def build_command(
    argv: list[str],
    *,
    binary_name: str = "nano-bofs",
    default_format: str = "text",
) -> tuple[dict[str, Any], str]:
    template_names = set(discover_templates())
    template_help_requested = False
    for index, token in enumerate(argv):
        if token in template_names:
            template_help_requested = any(item in {"-h", "--help"} for item in argv[index + 1 :])
            break

    base_parser = create_build_base_parser(binary_name, add_help=not template_help_requested)
    base_args, remaining = base_parser.parse_known_args(argv)

    config = load_config_or_raise()
    module = load_template_module(base_args.template)
    template_parser = create_template_parser(base_args.template, module, binary_name=binary_name)
    if template_help_requested:
        template_parser.parse_args(remaining)
    template_args = template_parser.parse_args(remaining)
    backend = base_args.backend or config.default_backend

    try:
        build_records, rendered_source_path, plan, selected_backend = render_build(
            config,
            module,
            template_args,
            base_args.output or config.output_dir,
            base_args.arch,
            backend,
        )
    except ValueError as exc:
        raise CliError(
            f"error building {base_args.template}: {exc}",
            code=2,
            usage=base_parser.format_usage().rstrip(),
        ) from exc

    artifact_rows = []
    for arch, record in build_records.items():
        artifact_rows.append(
            {
                "arch": arch,
                "path": record["path"],
                "source_path": record.get("source_path", str(rendered_source_path)),
                "md5": record["md5"],
                "md5_suffix": record["md5_suffix"],
            }
        )

    metadata = {
        "template": base_args.template,
        "backend": selected_backend,
        "artifacts": artifact_rows,
        "source_path": next(
            (record["source_path"] for record in build_records.values() if "source_path" in record),
            str(rendered_source_path),
        ),
        "source_paths": {
            arch: record.get("source_path", str(rendered_source_path))
            for arch, record in build_records.items()
        },
        "metadata": plan.get("metadata", {}),
    }

    if base_args.metadata_out:
        base_args.metadata_out.parent.mkdir(parents=True, exist_ok=True)
        base_args.metadata_out.write_text(json.dumps(metadata, indent=2), encoding="utf-8", newline="\n")
        metadata["metadata_output_path"] = str(base_args.metadata_out)

    text_lines = [
        f"template: {base_args.template}",
        f"backend:  {selected_backend}",
    ]
    for row in artifact_rows:
        text_lines.append(f"artifact ({row['arch']}): {row['path']}")
    if "metadata_output_path" in metadata:
        text_lines.append(f"metadata: {metadata['metadata_output_path']}")

    payload = {
        "data": metadata,
        "sections": [
            {
                "type": "fields",
                "fields": {
                    "template": base_args.template,
                    "backend": selected_backend,
                },
            },
            {
                "type": "table",
                "name": "artifacts",
                "fields": ["arch", "path", "source_path", "md5_suffix"],
                "rows": artifact_rows,
                "empty": "0 artifacts built.",
            },
        ],
        "text_lines": text_lines,
    }
    if "metadata_output_path" in metadata:
        payload["sections"].append(
            {
                "type": "fields",
                "name": "metadata",
                "fields": {
                    "path": metadata["metadata_output_path"],
                },
            }
        )

    return payload, ("json" if base_args.json else default_format)


def vars_command(
    argv: list[str],
    *,
    binary_name: str = "nano-bofs",
    default_format: str = "text",
) -> tuple[dict[str, Any], str]:
    parser = NanoArgumentParser(prog=f"{binary_name} vars")
    add_output_arguments(parser)
    parser.add_argument("template", choices=discover_templates())
    args = parser.parse_args(argv)

    module = load_template_module(args.template)
    template_parser = create_template_parser(
        args.template,
        module,
        binary_name=binary_name,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    variables, validation_rules, input_notes = _resolve_template_docs(args.template, module, binary_name=binary_name)
    usage_text = template_parser.format_help().rstrip()

    variable_rows = []
    for variable in variables:
        validation_items = variable.get("validation", [])
        joined_validation = " | ".join(
            item for item in validation_items if isinstance(item, str) and item.strip()
        )
        variable_rows.append(
            {
                "name": variable["name"],
                "required": "required" if variable.get("required", False) else "optional",
                "description": variable.get("description", ""),
                "shape": str(variable.get("shape", "")).strip(),
                "example": str(variable.get("example", "")).strip(),
                "validation": joined_validation,
            }
        )

    text_lines: list[str] = []
    if variables:
        text_lines.append(f"{args.template} variables:")
        for variable in variables:
            name = variable["name"]
            required = "required" if variable.get("required", False) else "optional"
            description = variable.get("description", "")
            text_lines.append(f"- {name} ({required}): {description}")
            shape = str(variable.get("shape", "")).strip()
            if shape:
                text_lines.append(f"  shape: {shape}")
            example = str(variable.get("example", "")).strip()
            if example:
                text_lines.append(f"  example: {example}")
            validation = variable.get("validation", [])
            if isinstance(validation, list):
                for rule in validation:
                    if isinstance(rule, str) and rule.strip():
                        text_lines.append(f"  validation: {rule}")
        text_lines.append("")
    else:
        text_lines.extend(
            [
                f"{args.template} variables:",
                "- none: This BOF takes no build-time inputs.",
                "",
            ]
        )

    if validation_rules:
        text_lines.append(f"{args.template} validation rules:")
        for rule in validation_rules:
            text_lines.append(f"- {rule}")
        text_lines.append("")

    if input_notes:
        text_lines.append(f"{args.template} input notes:")
        for note in input_notes:
            text_lines.append(f"- {note}")
        text_lines.append("")

    text_lines.extend(usage_text.splitlines())

    return (
        {
            "data": {
                "template": args.template,
                "variables": variables,
                "validation_rules": validation_rules,
                "input_notes": input_notes,
                "usage": usage_text,
            },
            "sections": [
                {
                    "type": "table",
                    "name": "variables",
                    "fields": ["name", "required", "description", "shape", "example", "validation"],
                    "rows": variable_rows,
                    "empty": "This BOF takes no build-time inputs.",
                },
                {
                    "type": "messages",
                    "name": "validation_rules",
                    "items": validation_rules,
                },
                {
                    "type": "messages",
                    "name": "input_notes",
                    "items": input_notes,
                },
            ],
            "text_lines": text_lines,
        },
        default_format,
    )


def audit_command(
    argv: list[str],
    *,
    binary_name: str = "nano-bofs",
    default_format: str = "text",
) -> tuple[dict[str, Any], str]:
    parser = NanoArgumentParser(prog=f"{binary_name} audit")
    add_output_arguments(parser)
    parser.add_argument(
        "query",
        nargs="?",
        help="Optional template substring filter.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show every template instead of only the ones missing docs metadata.",
    )
    args = parser.parse_args(argv)

    templates = discover_templates()
    if args.query:
        needle = args.query.lower()
        templates = [name for name in templates if needle in name.lower()]

    if not templates:
        message = f"No templates matched: {args.query}" if args.query else "No templates found."
        return (
            {
                "data": {
                    "query": args.query,
                    "rows": [],
                    "templates_checked": 0,
                    "templates_shown": 0,
                    "message": message,
                },
                "sections": [
                    {
                        "type": "messages",
                        "name": "audit",
                        "items": [message],
                    }
                ],
                "text_lines": [message],
            },
            default_format,
        )

    rows: list[dict[str, object]] = []
    for name in templates:
        module = load_template_module(name)
        variables, validation_rules, input_notes = _resolve_template_docs(name, module, binary_name=binary_name)
        has_variables = hasattr(module, "VARIABLES") or bool(variables)
        has_validation = bool(validation_rules)
        has_notes = bool(input_notes)
        rows.append(
            {
                "template": name,
                "variables": "yes" if has_variables else "no",
                "validation": "yes" if has_validation else "no",
                "notes": "yes" if has_notes else "no",
                "complete": has_variables and has_validation and has_notes,
            }
        )

    filtered_rows = rows if args.all else [row for row in rows if not bool(row["complete"])]
    if not filtered_rows:
        message = "All matching templates expose VARIABLES, VALIDATION_RULES, and INPUT_NOTES."
        return (
            {
                "data": {
                    "query": args.query,
                    "rows": [],
                    "templates_checked": len(rows),
                    "templates_shown": 0,
                    "message": message,
                },
                "sections": [
                    {
                        "type": "messages",
                        "name": "audit",
                        "items": [message],
                    }
                ],
                "text_lines": [message],
            },
            default_format,
        )

    text_lines = ["template  variables  validation  notes"]
    for row in filtered_rows:
        text_lines.append(
            f"{row['template']}  {row['variables']}  {row['validation']}  {row['notes']}"
        )
    text_lines.extend(
        [
            "",
            f"templates checked: {len(rows)}",
            f"templates shown:   {len(filtered_rows)}",
        ]
    )

    return (
        {
            "data": {
                "query": args.query,
                "rows": filtered_rows,
                "templates_checked": len(rows),
                "templates_shown": len(filtered_rows),
            },
            "sections": [
                {
                    "type": "table",
                    "name": "audit",
                    "fields": ["template", "variables", "validation", "notes"],
                    "rows": filtered_rows,
                    "empty": "No templates matched.",
                },
                {
                    "type": "fields",
                    "name": "summary",
                    "fields": {
                        "templates_checked": len(rows),
                        "templates_shown": len(filtered_rows),
                    },
                },
            ],
            "text_lines": text_lines,
        },
        default_format,
    )


def list_command(
    argv: list[str],
    *,
    binary_name: str = "nano-bofs",
    default_format: str = "text",
) -> tuple[dict[str, Any], str]:
    parser = NanoArgumentParser(prog=f"{binary_name} list")
    add_output_arguments(parser)
    parser.parse_args(argv)

    rows = []
    text_lines = []
    for name in discover_templates():
        module = load_template_module(name)
        description = getattr(module, "DESCRIPTION", "")
        rows.append({"name": name, "description": description})
        if description:
            text_lines.append(f"{name}: {description}")
        else:
            text_lines.append(name)

    return (
        {
            "data": {
                "templates": rows,
            },
            "sections": [
                {
                    "type": "table",
                    "name": "templates",
                    "fields": ["name", "description"],
                    "rows": rows,
                    "empty": "0 templates found.",
                }
            ],
            "text_lines": text_lines,
        },
        default_format,
    )


def history_command(
    argv: list[str],
    *,
    binary_name: str = "nano-bofs",
    default_format: str = "text",
) -> tuple[dict[str, Any], str]:
    parser = NanoArgumentParser(prog=f"{binary_name} history")
    add_output_arguments(parser)
    parser.add_argument(
        "query",
        nargs="?",
        metavar="QUERY|all",
        help="Optional BOF name or full/partial MD5 to search for. Use 'all' to show every entry.",
    )
    slice_group = parser.add_mutually_exclusive_group()
    slice_group.add_argument(
        "--first",
        type=int,
        metavar="N",
        help="Show the first N entries.",
    )
    slice_group.add_argument(
        "--last",
        type=int,
        metavar="N",
        help="Show the last N entries.",
    )
    args = parser.parse_args(argv)

    if args.first is not None and args.first <= 0:
        raise CliError("--first must be greater than 0", code=2, usage=parser.format_usage().rstrip())
    if args.last is not None and args.last <= 0:
        raise CliError("--last must be greater than 0", code=2, usage=parser.format_usage().rstrip())

    config = load_config_or_raise()
    entries = load_history_entries(config)
    if not entries:
        message = "No build history found."
        return (
            {
                "data": {
                    "query": args.query,
                    "entries": [],
                    "message": message,
                },
                "sections": [
                    {
                        "type": "messages",
                        "name": "history",
                        "items": [message],
                    }
                ],
                "text_lines": [message],
            },
            default_format,
        )

    selected_entries = select_history_entries(
        entries,
        query=args.query,
        first=args.first,
        last=args.last,
    )
    if not selected_entries:
        message = f"No build history matched: {args.query}" if args.query else "No build history found."
        return (
            {
                "data": {
                    "query": args.query,
                    "entries": [],
                    "message": message,
                },
                "sections": [
                    {
                        "type": "messages",
                        "name": "history",
                        "items": [message],
                    }
                ],
                "text_lines": [message],
            },
            default_format,
        )

    normalized_entries = [normalize_history_entry(entry) for entry in selected_entries]
    text_lines: list[str] = []
    for index, row in enumerate(normalized_entries):
        text_lines.append(f"{row['built_at']}  {row['template']}  {row['architecture']}")
        text_lines.append(f"  artifact: {row['artifact']}")
        text_lines.append(f"  md5:      {row['md5']}")
        text_lines.append(f"  backend:  {row['backend']}")
        if row["inputs"]:
            text_lines.append(f"  inputs:   {json.dumps(row['inputs'], sort_keys=True)}")
        if row["final"]:
            text_lines.append(f"  final:    {json.dumps(row['final'], sort_keys=True)}")
        if index != len(normalized_entries) - 1:
            text_lines.append("")

    return (
        {
            "data": {
                "query": args.query,
                "entries": normalized_entries,
            },
            "sections": [
                {
                    "type": "table",
                    "name": "history",
                    "fields": ["built_at", "template", "architecture", "backend", "md5_suffix"],
                    "rows": normalized_entries,
                    "empty": "0 build history entries found.",
                }
            ],
            "text_lines": text_lines,
        },
        default_format,
    )


def config_command(
    argv: list[str],
    *,
    binary_name: str = "nano-bofs",
    default_format: str = "text",
) -> tuple[dict[str, Any], str]:
    parser = NanoArgumentParser(prog=f"{binary_name} config")
    add_output_arguments(parser)
    subparsers = parser.add_subparsers(dest="config_command", required=True)
    path_parser = subparsers.add_parser("path", help="Show config file paths and the resolved state directory.")
    add_output_arguments(path_parser)
    show_parser = subparsers.add_parser("show", help="Show the resolved config values.")
    add_output_arguments(show_parser)
    args = parser.parse_args(argv)

    config = load_config_or_raise()
    if args.config_command == "path":
        data = {
            "user_config": str(config.user_config_path),
            "project_config": str(config.project_config_path) if config.project_config_path else None,
            "project_local_config": str(config.project_local_config_path) if config.project_local_config_path else None,
            "state_dir": str(config.state_dir),
            "output_dir": str(config.output_dir),
        }
        text_lines = [
            f"user config:    {config.user_config_path}",
            f"project config: {config.project_config_path}" if config.project_config_path else "project config: not found",
            f"local config:   {config.project_local_config_path}" if config.project_local_config_path else "local config:   not found",
            f"state dir:      {config.state_dir}",
            f"output dir:     {config.output_dir}",
        ]
        return (
            {
                "data": data,
                "sections": [
                    {
                        "type": "fields",
                        "fields": data,
                    }
                ],
                "text_lines": text_lines,
            },
            default_format,
        )

    if args.config_command == "show":
        data = {
            "state_dir": str(config.state_dir),
            "output_dir": str(config.output_dir),
            "default_backend": config.default_backend,
            "docker_image": config.docker_image,
        }
        text_lines = [
            "resolved config:",
            f"  state_dir:       {config.state_dir}",
            f"  output_dir:      {config.output_dir}",
            f"  default_backend: {config.default_backend}",
            f"  docker_image:    {config.docker_image}",
        ]
        return (
            {
                "data": data,
                "sections": [
                    {
                        "type": "fields",
                        "name": "resolved_config",
                        "fields": data,
                    }
                ],
                "text_lines": text_lines,
            },
            default_format,
        )

    raise CliError(f"unknown config command: {args.config_command}", code=2)


def build_main_parser(binary_name: str) -> NanoArgumentParser:
    parser = NanoArgumentParser(prog=binary_name, description=CLI_DESCRIPTION)
    add_output_arguments(parser)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("list", help="List available BOF templates.", add_help=False)
    subparsers.add_parser("build", help="Render a BOF template.", add_help=False)
    subparsers.add_parser("vars", help="List the variables for a BOF template.", add_help=False)
    subparsers.add_parser("audit", help="Audit template input-doc coverage.", add_help=False)
    subparsers.add_parser("history", help="Show BOF build history.", add_help=False)
    subparsers.add_parser("config", help="Show config paths and resolved values.", add_help=False)
    return parser


def _main(argv: list[str] | None = None, *, binary_name: str | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    resolved_binary_name = binary_name or normalize_binary_name(sys.argv[0])
    default_format = "toon" if resolved_binary_name == "nano-bofsx" else "text"

    try:
        cleaned_argv, selected_format = extract_output_format(raw_argv, default_format)
        parser = build_main_parser(resolved_binary_name)
        args, remaining = parser.parse_known_args(cleaned_argv)

        if args.command is None:
            if resolved_binary_name == "nano-bofsx":
                print(render_payload(build_dashboard_payload(resolved_binary_name), selected_format))
                return 0
            parser.print_help()
            return 0

        if args.command == "list":
            payload, format_name = list_command(remaining, binary_name=resolved_binary_name, default_format=selected_format)
        elif args.command == "build":
            payload, format_name = build_command(remaining, binary_name=resolved_binary_name, default_format=selected_format)
        elif args.command == "vars":
            payload, format_name = vars_command(remaining, binary_name=resolved_binary_name, default_format=selected_format)
        elif args.command == "audit":
            payload, format_name = audit_command(remaining, binary_name=resolved_binary_name, default_format=selected_format)
        elif args.command == "history":
            payload, format_name = history_command(remaining, binary_name=resolved_binary_name, default_format=selected_format)
        elif args.command == "config":
            payload, format_name = config_command(remaining, binary_name=resolved_binary_name, default_format=selected_format)
        else:
            raise CliError(f"unknown command: {args.command}", code=2)

        print(render_payload(payload, format_name))
        return 0
    except CliError as exc:
        print(
            render_error(
                exc.message,
                format_name=default_format if resolved_binary_name == "nano-bofsx" else "text"
                if not raw_argv
                else selected_format if "selected_format" in locals() else default_format,
                code=exc.code,
                usage=exc.usage,
                help_items=exc.help_items,
            )
        )
        return exc.code


def main(argv: list[str] | None = None) -> int:
    return _main(argv, binary_name="nano-bofs")


def main_axi(argv: list[str] | None = None) -> int:
    return _main(argv, binary_name="nano-bofsx")


if __name__ == "__main__":
    raise SystemExit(main())
