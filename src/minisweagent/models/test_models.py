import logging
import time
from typing import Any

from pydantic import BaseModel

from minisweagent.exceptions import FormatError
from minisweagent.models.utils.openai_multimodal import expand_multimodal_content
from minisweagent.models.utils.textbased import format_text_observation_messages, parse_text_actions
from minisweagent.models import GLOBAL_MODEL_STATS


class DeterministicModelConfig(BaseModel):
    outputs: list[str]
    model_name: str = "deterministic"
    cost_per_call: float = 1.0
    format_error_template: str = (
        "Please always provide EXACTLY ONE action in triple backticks, found {{actions|length}} actions."
    )
    observation_template: str = "{{ output.output }}"
    # NOTE: This is a Python regex string (not a YAML-escaped string). Use single
    # backslashes so \s and \n are interpreted by the regex engine.
    action_regex: str = r"```(?:mswea_bash_command|bash|sh)\s*\n(.*?)\n```"


class DeterministicModel:
    def __init__(self, **kwargs):
        """
        Initialize with a list of outputs to return in sequence.
        """
        self.config = DeterministicModelConfig(**kwargs)
        self.current_index = -1
        self.cost_per_call = self.config.cost_per_call
        self.cost = 0.0
        self.n_calls = 0

    def query(self, messages: list[dict], tools: list[dict] | None = None, **kwargs) -> dict:
        self.current_index += 1
        output = self.config.outputs[self.current_index]
        if "/sleep" in output:
            print("SLEEPING")
            time.sleep(float(output.split("/sleep")[1]))
            return self.query(messages, **kwargs)
        if "/warning" in output:
            logging.warning(output.split("/warning")[1])
            return self.query(messages, **kwargs)
        try:
            actions = parse_text_actions(
                {"content": output},
                action_regex=self.config.action_regex,
                format_error_template=self.config.format_error_template,
                template_vars=self.config.model_dump(),
            )
        except FormatError as e:
            self._record_cost(self.cost_per_call)
            raise FormatError(str(e), extra={"cost": self.cost_per_call}) from e
        self._record_cost(self.cost_per_call)
        return {"content": output, "extra": {"actions": actions, "cost": self.cost_per_call}}

    def format_message(self, role: str, content: str, **kwargs) -> dict:
        return {"role": role, "content": expand_multimodal_content(content), **kwargs}

    def format_observation_messages(self, observation: list[dict], *, message: dict | None = None) -> list[dict]:
        return format_text_observation_messages(
            observation,
            observation_template=self.config.observation_template,
            template_vars=self.config.model_dump(),
        )

    def get_template_vars(self) -> dict[str, Any]:
        return self.config.model_dump() | {"n_model_calls": self.n_calls, "model_cost": self.cost}

    def serialize(self) -> dict[str, Any]:
        return self.config.model_dump()

    def _record_cost(self, cost: float) -> None:
        self.n_calls += 1
        self.cost += cost
        GLOBAL_MODEL_STATS.add(cost)
