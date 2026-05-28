from __future__ import annotations

import json
from pathlib import Path

from mythic_container.MythicCommandBase import CommandAttributes
from mythic_container.MythicCommandBase import CommandBase
from mythic_container.MythicCommandBase import CommandParameter
from mythic_container.MythicCommandBase import PTTaskCreateTaskingMessageResponse
from mythic_container.MythicCommandBase import PTTaskMessageAllData
from mythic_container.MythicCommandBase import PTTaskProcessResponseMessageResponse
from mythic_container.MythicCommandBase import ParameterGroupInfo
from mythic_container.MythicCommandBase import ParameterType
from mythic_container.MythicCommandBase import SupportedOS
from mythic_container.MythicCommandBase import TaskArguments
from mythic_container.MythicRPC import MythicRPCFileCreateMessage
from mythic_container.MythicRPC import MythicRPCFileSearchMessage
from mythic_container.MythicRPC import MythicRPCResponseCreateMessage
from mythic_container.MythicRPC import SendMythicRPCFileCreate
from mythic_container.MythicRPC import SendMythicRPCFileSearch
from mythic_container.MythicRPC import SendMythicRPCResponseCreate
from nano_bofs.template_catalog import TemplateDefinition
from nano_bofs.template_catalog import TemplateVariable
from nano_bofs.template_catalog import build_template
from nano_bofs.template_catalog import load_mythic_template_definitions


APOLLO_PAYLOAD_TYPE = "apollo"
APOLLO_EXECUTE_COFF_COMMAND = "execute_coff"
DEFAULT_EXECUTE_TIMEOUT = 30
NEW_GROUP = "New"
MYTHIC_DEFINITIONS = load_mythic_template_definitions()
GENERATED_COMMAND_CLASSES: list[type[CommandBase]] = []


def get_generated_command_classes() -> list[type[CommandBase]]:
    return list(GENERATED_COMMAND_CLASSES)


def _normalize_callback_architecture(raw_value: str) -> str:
    value = raw_value.strip().lower()
    if value in {"x64", "amd64", "x86_64"}:
        return "x64"
    if value in {"x86", "i386", "386"}:
        return "x86"
    raise ValueError(f"unsupported callback architecture for nano-bofs BOF execution: {raw_value}")


def _parameter_type_for(variable: TemplateVariable) -> ParameterType:
    if variable.mythic_parameter_type == "Number":
        return ParameterType.Number
    return ParameterType.String


def _parameter_group(required: bool, position: int) -> list[ParameterGroupInfo]:
    return [
        ParameterGroupInfo(
            required=required,
            group_name="Default",
            ui_position=position,
        )
    ]


def _help_usage(definition: TemplateDefinition) -> str:
    parts = [f"nb_{definition.name}"]
    for variable in definition.variables:
        token = variable.name
        if variable.required:
            parts.append(f"<{token}>")
        else:
            parts.append(f"[{token}]")
    return " ".join(parts)


def _command_description(definition: TemplateDefinition) -> str:
    sections: list[str] = [definition.description]
    if definition.validation_rules:
        sections.append("Validation: " + " ".join(definition.validation_rules))
    if definition.input_notes:
        sections.append("Notes: " + " ".join(definition.input_notes))
    return "\n".join(section for section in sections if section.strip())


def _parameter_description(variable: TemplateVariable) -> str:
    parts: list[str] = [variable.description]
    if variable.shape:
        parts.append(f"Shape: {variable.shape}")
    if variable.example:
        parts.append(f"Example: {variable.example}")
    if variable.mythic_default_value not in (None, ""):
        parts.append(f"Default: {variable.mythic_default_value}")
    if variable.validation:
        parts.append("Validation: " + " ".join(variable.validation))
    return " ".join(part for part in parts if part.strip())


def _display_params(definition: TemplateDefinition, user_inputs: dict[str, object]) -> str:
    parts: list[str] = []
    for variable in definition.variables:
        if variable.name not in user_inputs:
            continue
        value = user_inputs[variable.name]
        if value is None or value == "":
            continue
        parts.append(f"-{variable.name} {value}")
    return " ".join(parts)


def _artifact_comment(definition: TemplateDefinition, md5_suffix: str, architecture: str) -> str:
    return f"nano-bofs {definition.name} {architecture} {md5_suffix}"


def _user_inputs_from_task_args(task_args: TaskArguments, definition: TemplateDefinition) -> dict[str, object]:
    values_by_name: dict[str, object] = {}
    for parameter in task_args.to_json():
        if not isinstance(parameter, dict):
            continue
        name = parameter.get("name")
        if not isinstance(name, str):
            continue
        values_by_name[name] = parameter.get("value")

    user_inputs: dict[str, object] = {}
    for variable in definition.variables:
        value = values_by_name.get(variable.name)
        if value is None or value == "":
            continue
        user_inputs[variable.name] = value
    return user_inputs


def _tasking_error(task_id: int, message: str) -> PTTaskCreateTaskingMessageResponse:
    return PTTaskCreateTaskingMessageResponse(
        TaskID=task_id,
        Success=False,
        Error=message,
        Completed=True,
        TaskStatus="error",
    )


async def _ensure_registered_bof(task_data: PTTaskMessageAllData, definition: TemplateDefinition, user_inputs: dict[str, object]) -> tuple[str, str]:
    architecture = _normalize_callback_architecture(task_data.Callback.Architecture)
    result = build_template(definition.name, user_inputs, architecture)
    filename = Path(result.artifact_path).name
    comment = _artifact_comment(definition, result.md5_suffix, architecture)
    search = await SendMythicRPCFileSearch(
        MythicRPCFileSearchMessage(
            TaskID=task_data.Task.ID,
            Filename=filename,
            Comment=comment,
            LimitByCallback=False,
            MaxResults=1,
        )
    )
    if not search.Success:
        raise Exception(search.Error)
    if search.Files:
        return search.Files[0].AgentFileID, json.dumps(
            {
                "artifact": filename,
                "backend": result.backend,
                "md5_suffix": result.md5_suffix,
                "source_path": str(result.tracked_source_path),
            },
            sort_keys=True,
        )
    upload = await SendMythicRPCFileCreate(
        MythicRPCFileCreateMessage(
            TaskID=task_data.Task.ID,
            FileContents=result.artifact_path.read_bytes(),
            DeleteAfterFetch=False,
            Filename=filename,
            IsScreenshot=False,
            IsDownloadFromAgent=False,
            Comment=comment,
        )
    )
    if not upload.Success:
        raise Exception(upload.Error)
    return upload.AgentFileId, json.dumps(
        {
            "artifact": filename,
            "backend": result.backend,
            "md5_suffix": result.md5_suffix,
            "source_path": str(result.tracked_source_path),
        },
        sort_keys=True,
    )


def _generate_argument_class(definition: TemplateDefinition) -> type[TaskArguments]:
    class GeneratedArguments(TaskArguments):
        def __init__(self, command_line, **kwargs):
            super().__init__(command_line, **kwargs)
            self.args = [
                CommandParameter(
                    name=variable.name,
                    cli_name=variable.name,
                    display_name=variable.modal_display_name,
                    type=_parameter_type_for(variable),
                    description=_parameter_description(variable),
                    choices=list(variable.choices),
                    default_value=(
                        variable.mythic_default_value
                        if variable.mythic_default_value is not None
                        else (None if variable.required else "")
                    ),
                    parameter_group_info=_parameter_group(variable.required, position),
                )
                for position, variable in enumerate(definition.variables, start=1)
            ]

        async def parse_arguments(self):
            if not self.command_line.strip():
                self.load_args_from_json_string("{}")
                return
            if self.command_line.lstrip().startswith("{"):
                self.load_args_from_json_string(self.command_line)
                return
            raise Exception(f"{definition.name} expects Mythic JSON arguments from the UI.")

    GeneratedArguments.__name__ = f"{definition.name.title().replace('_', '')}Arguments"
    return GeneratedArguments


def _generate_command_class(definition: TemplateDefinition) -> type[CommandBase]:
    argument_class = _generate_argument_class(definition)

    class GeneratedCommand(CommandBase):
        cmd = f"nb_{definition.name}"
        needs_admin = False
        help_cmd = _help_usage(definition)
        description = _command_description(definition)
        version = 1
        author = "@BlaiseOfGlory"
        attackmapping: list[str] = []
        attributes = CommandAttributes(
            supported_os=[SupportedOS.Windows],
            builtin=False,
            suggested_command=True,
            load_only=False,
        )

        async def create_go_tasking(self, taskData: PTTaskMessageAllData) -> PTTaskCreateTaskingMessageResponse:
            response = PTTaskCreateTaskingMessageResponse(
                TaskID=taskData.Task.ID,
                Success=True,
            )
            user_inputs = _user_inputs_from_task_args(taskData.args, definition)

            await SendMythicRPCResponseCreate(
                MythicRPCResponseCreateMessage(
                    TaskID=taskData.Task.ID,
                    Response=f"[*] Building {definition.name} for {taskData.Callback.Architecture}...\n".encode(),
                )
            )
            try:
                file_id, build_stdout = await _ensure_registered_bof(taskData, definition, user_inputs)
            except ValueError as exc:
                return _tasking_error(taskData.Task.ID, str(exc))
            except Exception as exc:
                return _tasking_error(taskData.Task.ID, f"failed to prepare {definition.name}: {exc}")

            for variable in definition.variables:
                taskData.args.remove_arg(variable.name)
            new_group = [
                ParameterGroupInfo(required=True, group_name=NEW_GROUP, ui_position=1)
            ]
            taskData.args.add_arg("bof_file", file_id, type=ParameterType.File, parameter_group_info=new_group)
            taskData.args.add_arg(
                "function_name",
                definition.bof_entrypoint,
                type=ParameterType.String,
                parameter_group_info=[ParameterGroupInfo(required=False, group_name=NEW_GROUP, ui_position=2)],
            )
            taskData.args.add_arg(
                "timeout",
                DEFAULT_EXECUTE_TIMEOUT,
                type=ParameterType.Number,
                parameter_group_info=[ParameterGroupInfo(required=False, group_name=NEW_GROUP, ui_position=3)],
            )
            taskData.args.add_arg(
                "coff_arguments",
                [],
                type=ParameterType.TypedArray,
                parameter_group_info=[ParameterGroupInfo(required=False, group_name=NEW_GROUP, ui_position=4)],
            )

            response.CommandName = APOLLO_EXECUTE_COFF_COMMAND
            response.ReprocessAtNewCommandPayloadType = APOLLO_PAYLOAD_TYPE
            response.ParameterGroupName = NEW_GROUP
            response.DisplayParams = _display_params(definition, user_inputs)
            response.Stdout = build_stdout
            return response

        async def process_response(self, task: PTTaskMessageAllData, response: any) -> PTTaskProcessResponseMessageResponse:
            return PTTaskProcessResponseMessageResponse(TaskID=task.Task.ID, Success=True)

    GeneratedCommand.__name__ = f"{definition.name.title().replace('_', '')}Command"
    GeneratedCommand.argument_class = argument_class
    return GeneratedCommand


for template_definition in MYTHIC_DEFINITIONS:
    generated = _generate_command_class(template_definition)
    GENERATED_COMMAND_CLASSES.append(generated)
    globals()[generated.__name__] = generated
