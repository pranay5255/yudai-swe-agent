import asyncio
from typing import Any

from pydantic import BaseModel
from swerex.deployment.docker import DockerDeployment
from swerex.runtime.abstract import Command as RexCommand

from minisweagent.models.utils.actions_toolcall import BASH_TOOL
from minisweagent.utils.actions import get_action_command


class SwerexDockerEnvironmentConfig(BaseModel):
    image: str
    cwd: str = "/"
    """Working directory in which to execute commands."""
    timeout: int = 30
    """Timeout for executing commands in the container."""
    deployment_extra_kwargs: dict[str, Any] = {}
    """Extra kwargs to pass to DockerDeployment."""


class SwerexDockerEnvironment:
    def __init__(self, **kwargs):
        """This class executes bash commands in a Docker container using SWE-ReX for sandboxing."""
        self.config = SwerexDockerEnvironmentConfig(**kwargs)
        self.deployment = DockerDeployment(image=self.config.image, **self.config.deployment_extra_kwargs)
        asyncio.run(self.deployment.start())

    def execute(self, action: dict | str, cwd: str = "", *, timeout: int | None = None) -> dict[str, Any]:
        """Execute a command in the environment and return the raw output."""
        command = get_action_command(action)
        output = asyncio.run(
            self.deployment.runtime.execute(
                RexCommand(
                    command=command,
                    shell=True,
                    check=False,
                    cwd=cwd or self.config.cwd,
                    timeout=timeout or self.config.timeout,
                    merge_output_streams=True,
                )
            )
        )
        return {"output": output.stdout, "returncode": output.exit_code, "command": command}

    def get_template_vars(self) -> dict[str, Any]:
        return self.config.model_dump()

    def get_tools(self) -> list[dict]:
        return [BASH_TOOL]

    def serialize(self) -> dict[str, Any]:
        return self.config.model_dump()
