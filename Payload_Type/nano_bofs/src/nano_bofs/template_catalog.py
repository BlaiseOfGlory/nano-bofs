from __future__ import annotations

import argparse
import importlib.util
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from nano_bofs.builder import artifact_paths
from nano_bofs.builder import build_artifacts
from nano_bofs.builder import create_staging_dir
from nano_bofs.builder import source_path
from nano_bofs.config import ResolvedConfig
from nano_bofs.config import load_config
from nano_bofs.input_validation import VARIABLE_DOC_FALLBACKS
from nano_bofs.input_validation import normalize_optional_boolish
from nano_bofs.pathing import discover_workspace_root


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = discover_workspace_root(Path(__file__).resolve(), PROJECT_ROOT)
VENDORED_TEMPLATES_ROOT = PROJECT_ROOT / "templates"
REPO_TEMPLATES_ROOT = REPO_ROOT / "templates"
BAKED_TEMPLATES_ROOT = Path("/opt/nano-bofs-base/templates")
PILOT_TEMPLATE_NAMES = ("adcs_enum", "probe", "wmi_query", "ipconfig")


class CatalogArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(message)

    def exit(self, status: int = 0, message: str | None = None) -> None:
        if status == 0:
            raise SystemExit(0)
        raise ValueError((message or "").strip())


@dataclass(frozen=True)
class TemplateVariable:
    name: str
    required: bool
    description: str
    shape: str
    example: str
    validation: tuple[str, ...]
    choices: tuple[object, ...]
    modal_display_name: str
    mythic_parameter_type: str
    placeholder: str
    mythic_default_value: object | None


@dataclass(frozen=True)
class TemplateDefinition:
    name: str
    description: str
    variables: tuple[TemplateVariable, ...]
    validation_rules: tuple[str, ...]
    input_notes: tuple[str, ...]
    artifact_basename: str
    bof_entrypoint: str
    mythic_enabled: bool


@dataclass(frozen=True)
class TemplateBuildResult:
    template: str
    architecture: str
    backend: str
    artifact_path: Path
    tracked_source_path: Path
    tracked_artifact_path: Path
    build_dir: Path
    md5: str
    md5_suffix: str
    metadata: dict[str, object]
    bof_entrypoint: str


def discover_templates() -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for templates_root in _template_roots():
        for child in sorted(templates_root.iterdir()):
            if child.is_dir() and (child / "parser.py").exists() and child.name not in seen:
                names.append(child.name)
                seen.add(child.name)
    return names


def load_template_module(name: str) -> ModuleType:
    parser_path = _resolve_template_parser_path(name)
    if parser_path is None:
        raise ValueError(f"unknown template: {name}")
    module_name = f"nano_bofs_template_{name}"
    spec = importlib.util.spec_from_file_location(module_name, parser_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"failed to load parser module for {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_template_definition(name: str) -> TemplateDefinition:
    module = load_template_module(name)
    parser = _create_template_parser(module)
    variables = _mythic_variables_for(module, parser)
    validation_rules = _as_list_of_strings(getattr(module, "VALIDATION_RULES", []))
    input_notes = _as_list_of_strings(getattr(module, "INPUT_NOTES", []))
    if not variables:
        validation_rules = validation_rules or (
            "This template takes no build-time inputs.",
            "The generated BOF takes no runtime arguments.",
        )
        input_notes = input_notes or (f"Build `{name}` directly without supplying arguments.",)
    else:
        validation_rules = validation_rules or (
            "Inputs are validated at build time before BOF source rendering.",
            "The generated BOF takes no runtime arguments.",
        )
    return TemplateDefinition(
        name=name,
        description=str(getattr(module, "DESCRIPTION", "")).strip(),
        variables=tuple(_materialize_variable_docs(variables)),
        validation_rules=tuple(validation_rules),
        input_notes=tuple(input_notes),
        artifact_basename=str(getattr(module, "NAME", name)),
        bof_entrypoint=str(getattr(module, "BOF_ENTRYPOINT", "go")),
        mythic_enabled=_get_mythic_enabled(module),
    )


def load_pilot_template_definitions() -> list[TemplateDefinition]:
    return [
        definition
        for definition in (load_template_definition(name) for name in PILOT_TEMPLATE_NAMES)
        if definition.mythic_enabled
    ]


def load_mythic_template_definitions() -> list[TemplateDefinition]:
    return [
        definition
        for definition in (load_template_definition(name) for name in discover_templates())
        if definition.mythic_enabled and _is_mythic_ready(load_template_module(definition.name))
    ]


def parse_template_inputs(template_name: str, raw_inputs: dict[str, object]) -> argparse.Namespace:
    module = load_template_module(template_name)
    parse_mythic_inputs = getattr(module, "parse_mythic_inputs", None)
    if callable(parse_mythic_inputs):
        parsed_args = parse_mythic_inputs(dict(raw_inputs))
        if not isinstance(parsed_args, argparse.Namespace):
            raise ValueError(f"{template_name} parse_mythic_inputs must return argparse.Namespace.")
        return parsed_args
    parser = _create_template_parser(module)
    positional_actions = [
        action
        for action in parser._actions
        if not action.option_strings
        and not isinstance(action, argparse._HelpAction)
        and action.dest != argparse.SUPPRESS
    ]
    supplied_indexes = [
        index
        for index, action in enumerate(positional_actions)
        if _value_was_supplied(raw_inputs, action.dest)
    ]
    last_supplied_index = max(supplied_indexes, default=-1)
    argv: list[str] = []
    for index, action in enumerate(positional_actions):
        has_value = _value_was_supplied(raw_inputs, action.dest)
        if has_value:
            argv.append(str(raw_inputs[action.dest]))
            continue
        if index <= last_supplied_index:
            if action.default is argparse.SUPPRESS or action.default is None:
                raise ValueError(f"{action.dest} is required when later positional values are supplied.")
            argv.append(str(action.default))
            continue
        if _is_required_action(action):
            raise ValueError(f"{action.dest} is required.")
    for action in parser._actions:
        if isinstance(action, argparse._HelpAction) or not action.option_strings:
            continue
        if not _value_was_supplied(raw_inputs, action.dest):
            continue
        option = _preferred_option_string(action.option_strings)
        value = raw_inputs[action.dest]
        if isinstance(action, argparse._StoreTrueAction):
            if normalize_optional_boolish(value, label=action.dest):
                argv.append(option)
            continue
        if isinstance(action, argparse._StoreFalseAction):
            if not normalize_optional_boolish(value, label=action.dest):
                argv.append(option)
            continue
        if isinstance(value, list):
            if not value:
                continue
            argv.append(option)
            argv.extend(str(item) for item in value)
            continue
        argv.extend([option, str(value)])
    return parser.parse_args(argv)


def build_template(
    template_name: str,
    raw_inputs: dict[str, object],
    architecture: str,
    *,
    backend: str | None = None,
    config: ResolvedConfig | None = None,
) -> TemplateBuildResult:
    resolved_config = config or load_config()
    module = load_template_module(template_name)
    definition = load_template_definition(template_name)
    parsed_args = parse_template_inputs(template_name, raw_inputs)
    plan = module.build_plan(parsed_args)
    requested_output_paths = artifact_paths(
        resolved_config.output_dir,
        str(plan["artifact_basename"]),
        architecture,
    )
    staging_dir = create_staging_dir(resolved_config, template_name)
    rendered_source_path = source_path(staging_dir, str(plan["source_name"]))
    rendered_source_path.parent.mkdir(parents=True, exist_ok=True)
    rendered_source_path.write_text(module.render_plan(plan), encoding="utf-8", newline="\n")
    selected_backend, build_records = build_artifacts(
        config=resolved_config,
        template_name=template_name,
        build_spec=dict(plan["build"]),
        source_path_value=rendered_source_path,
        requested_output_paths=requested_output_paths,
        backend=backend or resolved_config.default_backend,
        user_inputs=dict(vars(parsed_args)),
        metadata=dict(plan.get("metadata", {})),
    )
    record = build_records[architecture]
    return TemplateBuildResult(
        template=template_name,
        architecture=architecture,
        backend=selected_backend,
        artifact_path=Path(record["path"]),
        tracked_source_path=Path(record["source_path"]),
        tracked_artifact_path=Path(record["build_artifact"]),
        build_dir=Path(record["build_dir"]),
        md5=record["md5"],
        md5_suffix=record["md5_suffix"],
        metadata=dict(plan.get("metadata", {})),
        bof_entrypoint=definition.bof_entrypoint,
    )


def _create_template_parser(module: ModuleType) -> CatalogArgumentParser:
    parser = CatalogArgumentParser(
        prog=str(getattr(module, "NAME", "template")),
        description=getattr(module, "DESCRIPTION", None),
        add_help=False,
    )
    module.add_arguments(parser)
    return parser


def _template_roots() -> list[Path]:
    roots: list[Path] = []
    seen: set[Path] = set()
    for root in (REPO_TEMPLATES_ROOT, VENDORED_TEMPLATES_ROOT, BAKED_TEMPLATES_ROOT):
        resolved = root.resolve(strict=False)
        if resolved in seen or not root.exists():
            continue
        roots.append(root)
        seen.add(resolved)
    return roots


def _resolve_template_parser_path(name: str) -> Path | None:
    for templates_root in _template_roots():
        parser_path = templates_root / name / "parser.py"
        if parser_path.exists():
            return parser_path
    return None


def _get_mythic_enabled(module: ModuleType) -> bool:
    value = getattr(module, "MYTHIC_ENABLED", True)
    if not isinstance(value, bool):
        raise ValueError(
            f"{getattr(module, 'NAME', module.__name__)} MYTHIC_ENABLED must be a boolean when set."
        )
    return value


def _mythic_variables_for(
    module: ModuleType,
    parser: argparse.ArgumentParser,
) -> list[dict[str, object]]:
    mythic_variables = _as_list_of_dicts(getattr(module, "MYTHIC_VARIABLES", []))
    if mythic_variables:
        return _apply_variable_fallbacks(mythic_variables)
    return _apply_variable_fallbacks(
        _merge_variables(
            _as_list_of_dicts(getattr(module, "VARIABLES", [])),
            _inferred_variables_from_parser(parser),
        )
    )


def _is_mythic_ready(module: ModuleType) -> bool:
    if callable(getattr(module, "parse_mythic_inputs", None)) and _as_list_of_dicts(
        getattr(module, "MYTHIC_VARIABLES", [])
    ):
        return True
    parser = _create_template_parser(module)
    if any(isinstance(action, argparse._SubParsersAction) for action in parser._actions):
        return False
    variables = _merge_variables(
        _as_list_of_dicts(getattr(module, "VARIABLES", [])),
        _inferred_variables_from_parser(parser),
    )
    return not any(str(variable.get("name", "")).strip() == "arguments" for variable in variables)


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
        if action.option_strings or not action.dest or action.dest == argparse.SUPPRESS:
            continue
        inferred.append(
            {
                "name": action.dest,
                "required": _is_required_action(action),
                "description": action.help or "",
            }
        )
    return inferred


def _merge_variables(
    module_variables: list[dict[str, object]],
    parser_variables: list[dict[str, object]],
) -> list[dict[str, object]]:
    merged: list[dict[str, object]] = []
    index_by_name: dict[str, int] = {}
    for item in module_variables + parser_variables:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        if name in index_by_name:
            merged[index_by_name[name]] = {**merged[index_by_name[name]], **item}
            continue
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
        validation = merged.get("validation")
        if not isinstance(validation, list) or not any(isinstance(item, str) and item.strip() for item in validation):
            if "validation" in fallback:
                merged["validation"] = list(fallback["validation"])
        resolved.append(merged)
    return resolved


def _materialize_variable_docs(variables: list[dict[str, object]]) -> list[TemplateVariable]:
    docs: list[TemplateVariable] = []
    for variable in variables:
        name = str(variable.get("name", "")).strip()
        docs.append(
            TemplateVariable(
                name=name,
                required=bool(variable.get("required", False)),
                description=str(variable.get("description", "")).strip(),
                shape=str(variable.get("shape", "")).strip(),
                example=str(variable.get("example", "")).strip(),
                validation=tuple(
                    item.strip()
                    for item in variable.get("validation", [])
                    if isinstance(item, str) and item.strip()
                ),
                choices=tuple(variable.get("choices", []))
                if isinstance(variable.get("choices"), list)
                else tuple(),
                modal_display_name=str(
                    variable.get("modal_display_name", name.replace("_", " ").title())
                ).strip(),
                mythic_parameter_type=str(
                    variable.get("mythic_parameter_type", "String")
                ).strip(),
                placeholder=str(variable.get("placeholder", "")).strip(),
                mythic_default_value=variable.get("mythic_default_value"),
            )
        )
    return docs


def _value_was_supplied(raw_inputs: dict[str, object], name: str) -> bool:
    if name not in raw_inputs:
        return False
    value = raw_inputs[name]
    if value is None:
        return False
    return not (isinstance(value, str) and value == "")


def _preferred_option_string(option_strings: list[str]) -> str:
    long_options = [option for option in option_strings if option.startswith("--")]
    if long_options:
        return long_options[0]
    return option_strings[0]
