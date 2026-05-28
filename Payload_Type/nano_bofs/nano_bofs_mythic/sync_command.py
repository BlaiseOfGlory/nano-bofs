from mythic_container.MythicCommandBase import CommandAttributes
from mythic_container.MythicCommandBase import CommandBase
from mythic_container.MythicCommandBase import PTTaskCreateTaskingMessageResponse
from mythic_container.MythicCommandBase import PTTaskMessageAllData
from mythic_container.MythicCommandBase import PTTaskProcessResponseMessageResponse
from mythic_container.MythicCommandBase import SupportedOS
from mythic_container.MythicCommandBase import TaskArguments
from mythic_container.MythicRPC import MythicRPCResponseCreateMessage
from mythic_container.MythicRPC import SendMythicRPCResponseCreate
from mythic_container.PayloadBuilder import SendMythicRPCSyncPayloadType

from nano_bofs_mythic.generated_commands import get_generated_command_classes


class NanoBofsSyncArguments(TaskArguments):
    def __init__(self, command_line, **kwargs):
        super().__init__(command_line, **kwargs)
        self.args = []

    async def parse_arguments(self):
        if self.command_line.strip():
            raise Exception("nanobofs_sync takes no arguments.")


class NanoBofsSyncCommand(CommandBase):
    cmd = "nanobofs_sync"
    needs_admin = False
    help_cmd = "nanobofs_sync"
    description = "Re-sync the dynamic nano-bofs augmentation commands."
    version = 1
    author = "@BlaiseOfGlory"
    attackmapping: list[str] = []
    script_only = True
    argument_class = NanoBofsSyncArguments
    attributes = CommandAttributes(
        supported_os=[SupportedOS.Windows],
        builtin=True,
        suggested_command=False,
        load_only=False,
    )

    async def create_go_tasking(self, taskData: PTTaskMessageAllData) -> PTTaskCreateTaskingMessageResponse:
        success = await SendMythicRPCSyncPayloadType("nano_bofs", get_generated_command_classes())
        if not success:
            return PTTaskCreateTaskingMessageResponse(
                TaskID=taskData.Task.ID,
                Success=False,
                Error="failed to re-sync nano_bofs payload data",
                Completed=True,
                TaskStatus="error",
            )
        await SendMythicRPCResponseCreate(
            MythicRPCResponseCreateMessage(
                TaskID=taskData.Task.ID,
                Response=b"Re-synced dynamic nano_bofs commands.\n",
            )
        )
        return PTTaskCreateTaskingMessageResponse(
            TaskID=taskData.Task.ID,
            Success=True,
            Completed=True,
            TaskStatus="completed",
        )

    async def process_response(self, task: PTTaskMessageAllData, response: any) -> PTTaskProcessResponseMessageResponse:
        return PTTaskProcessResponseMessageResponse(TaskID=task.Task.ID, Success=True)
