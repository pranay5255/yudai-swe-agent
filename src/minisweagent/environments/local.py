import os
import platform
import subprocess
from typing import Any

from pydantic import BaseModel

from minisweagent.models.utils.actions_toolcall import BASH_TOOL
from minisweagent.utils.actions import get_action_command


class LocalEnvironmentConfig(BaseModel):
    cwd: str = ""
    env: dict[str, str] = {}
    timeout: int = 30


class LocalEnvironment:
    def __init__(self, *, config_class: type = LocalEnvironmentConfig, **kwargs):
        """This class executes bash commands directly on the local machine."""
        self.config = config_class(**kwargs)

    def execute(self, action: dict | str, cwd: str = "", *, timeout: int | None = None) -> dict[str, Any]:
        """Execute a command in the local environment and return the result as a dict."""
        command = get_action_command(action)
        cwd = cwd or self.config.cwd or os.getcwd()
        try:
            result = subprocess.run(
                command,
                shell=True,
                text=True,
                cwd=cwd,
                env=os.environ | self.config.env,
                timeout=timeout or self.config.timeout,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            return {"output": result.stdout, "returncode": result.returncode, "command": command}
        except subprocess.TimeoutExpired as e:
            output = e.output.decode("utf-8", errors="replace") if isinstance(e.output, bytes) else (e.output or "")
            return {"output": output, "returncode": 124, "command": command, "timed_out": True}

    def get_template_vars(self) -> dict[str, Any]:
        return self.config.model_dump() | platform.uname()._asdict() | os.environ

    def get_tools(self) -> list[dict]:
        return [BASH_TOOL]

    def serialize(self) -> dict[str, Any]:
        return self.config.model_dump()
