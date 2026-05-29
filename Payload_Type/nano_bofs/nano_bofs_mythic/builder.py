from pathlib import PurePath

from mythic_container.PayloadBuilder import AgentType
from mythic_container.PayloadBuilder import PayloadType
from mythic_container.PayloadBuilder import SupportedOS


class NanoBofs(PayloadType):
    name = "nano_bofs"
    file_extension = "bin"
    author = "@BlaiseOfGlory"
    supported_os = [SupportedOS.Windows]
    wrapper = False
    wrapped_payloads = []
    description = "Template-backed BOF command augmentation for Apollo callbacks."
    supports_dynamic_loading = True
    c2_profiles = []
    build_parameters = []
    build_steps = []
    agent_type = AgentType.CommandAugment
    command_augment_supported_agents = ["apollo"]
    semver = "0.1.2"
    agent_path = PurePath(".") / "nano_bofs_mythic"
    agent_icon_path = agent_path / "nano_bofs.svg"
    dark_mode_agent_icon_path = agent_icon_path
