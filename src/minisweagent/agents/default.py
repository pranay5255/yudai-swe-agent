"""Basic agent class. See https://mini-swe-agent.com/latest/advanced/control_flow/ for visual explanation."""

import time

from jinja2 import StrictUndefined, Template
from pydantic import BaseModel

from minisweagent import Environment, Model, __version__
from minisweagent.exceptions import FormatError, InterruptAgentFlow, LimitsExceeded, Submitted, UserInterruption


class AgentConfig(BaseModel):
    # Check the config files in minisweagent/config for example settings
    system_template: str
    instance_template: str
    step_limit: int = 0
    cost_limit: float = 3.0


def _get_class_name_with_module(obj) -> str:
    """Get the full class name with module path."""
    return f"{obj.__class__.__module__}.{obj.__class__.__name__}"


class RunResult(dict):
    """Dict-like run result that also supports tuple unpacking."""

    def __iter__(self):
        yield self.get("exit_status")
        yield self.get("submission")


class DefaultAgent:
    def __init__(self, model: Model, env: Environment, *, config_class: type = AgentConfig, **kwargs):
        self.config = config_class(**kwargs)
        self.messages: list[dict] = []
        self.model = model
        self.env = env
        self.extra_template_vars = {}
        self.cost = 0.0
        self.n_calls = 0

    def render_template(self, template: str, **kwargs) -> str:
        template_vars = self.config.model_dump() | self.env.get_template_vars() | self.model.get_template_vars()
        return Template(template, undefined=StrictUndefined).render(
            **kwargs, **template_vars, **self.extra_template_vars
        )

    def add_message(self, role: str, content: str, **kwargs):
        self.messages.append(self.model.format_message(role, content, timestamp=time.time(), **kwargs))

    def run(self, task: str, **kwargs) -> RunResult:
        """Run step() until agent is finished. Return exit info dict."""
        self.extra_template_vars |= {"task": task, **kwargs}
        self.messages = []
        self.add_message("system", self.render_template(self.config.system_template))
        self.add_message("user", self.render_template(self.config.instance_template))
        while True:
            try:
                self.step()
            except InterruptAgentFlow as e:
                message = self.model.format_message(
                    "user", str(e), timestamp=time.time(), **getattr(e, "extra", {})
                )
                self.messages.append(message)
                if isinstance(e, Submitted):
                    return RunResult({
                        "submission": str(e),
                        "exit_status": type(e).__name__,
                        **e.extra,
                    })
                if isinstance(e, FormatError):
                    self.cost += e.extra.get("cost", 0.0) or 0.0
                    self.n_calls += 1
                    continue
                if isinstance(e, UserInterruption):
                    continue
                return RunResult({"exit_status": type(e).__name__, **e.extra})

    def step(self) -> list[dict]:
        """Query the LM, execute the actions, return the observations."""
        response_message = self.query()
        return self.get_observations(response_message)

    def query(self) -> dict:
        """Query the model and return the response message."""
        if 0 < self.config.step_limit <= self.n_calls or 0 < self.config.cost_limit <= self.cost:
            raise LimitsExceeded("Limits exceeded.")
        response = self.model.query(self.messages, tools=self.env.get_tools())
        message = self.model.format_message(
            "assistant",
            response.get("content", ""),
            timestamp=time.time(),
            **response.get("extra", {}),
        )
        self.messages.append(message)
        cost = response.get("extra", {}).get("cost", 0.0) or 0.0
        self.cost += cost
        self.n_calls += 1
        return message

    def get_observations(self, message: dict) -> list[dict]:
        """Execute the actions and return the observations."""
        actions = message.get("actions", [])
        outputs: list[dict] = []
        for action in actions:
            outputs.append(self.execute_action(action))
        observation_messages = self.model.format_observation_messages(outputs, message=message)
        for obs in observation_messages:
            obs.setdefault("timestamp", time.time())
        self.messages.extend(observation_messages)
        return outputs

    def execute_action(self, action: dict) -> dict:
        output = self.env.execute(action)
        self.has_finished(output)
        return output

    def has_finished(self, output: dict[str, str]):
        """Raises Submitted exception with final output if the agent has finished its task."""
        lines = output.get("output", "").lstrip().splitlines(keepends=True)
        if lines and lines[0].strip() == "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT":
            raise Submitted("".join(lines[1:]))

    def save(self, *, exit_info: dict | None = None, **kwargs) -> dict:
        data = {
            "info": {
                "exit_status": "unknown",
                "submission": "",
                "model_stats": {
                    "cost": self.cost,
                    "api_calls": self.n_calls,
                },
                "mini_version": __version__,
            },
            "messages": self.messages,
            "trajectory_format": "mini-swe-agent-2",
        }
        if exit_info:
            data["info"].update(exit_info)
        data["info"]["config"] = {
            "agent": self.config.model_dump(),
            "model": self.model.serialize(),
            "environment": self.env.serialize(),
            "agent_type": _get_class_name_with_module(self),
            "model_type": _get_class_name_with_module(self.model),
            "environment_type": _get_class_name_with_module(self.env),
        }
        return data | kwargs
