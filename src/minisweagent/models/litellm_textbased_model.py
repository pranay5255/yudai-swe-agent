import time
from collections.abc import Callable

from minisweagent.exceptions import FormatError
from minisweagent.models.litellm_model import LitellmModel, LitellmModelConfig
from minisweagent.models.utils.textbased import format_text_observation_messages, parse_text_actions


class LitellmTextBasedModelConfig(LitellmModelConfig):
    # Python regex string (not YAML-escaped). Keep single backslashes so \s/\n work.
    action_regex: str = r"```(?:mswea_bash_command|bash|sh)\s*\n(.*?)\n```"


class LitellmTextBasedModel(LitellmModel):
    def __init__(self, *, config_class: Callable = LitellmTextBasedModelConfig, **kwargs):
        super().__init__(config_class=config_class, **kwargs)

    def query(self, messages: list[dict], tools: list[dict] | None = None, **kwargs) -> dict:
        response = self._query(self._prepare_messages_for_api(messages), **kwargs)
        content = response.choices[0].message.content or ""  # type: ignore[index]
        cost_info = self._calculate_cost(response)
        cost = cost_info.get("cost", 0.0) or 0.0
        actions = []
        if tools is not None:
            try:
                actions = parse_text_actions(
                    {"content": content},
                    action_regex=self.config.action_regex,
                    format_error_template=self.config.format_error_template,
                    template_vars=self.config.model_dump(),
                )
            except FormatError as e:
                extra = {"response": response.model_dump(), "timestamp": time.time()}
                extra.update(cost_info)
                self._record_cost(cost)
                raise FormatError(str(e), extra=extra) from e
        extra = {
            "response": response.model_dump(),
            "actions": actions,
            "timestamp": time.time(),
        }
        extra.update(cost_info)
        self._record_cost(cost)
        return {"content": content, "extra": extra}

    def format_observation_messages(self, observation: list[dict], *, message: dict | None = None) -> list[dict]:
        return format_text_observation_messages(
            observation,
            observation_template=self.config.observation_template,
            template_vars=self.config.model_dump(),
        )
