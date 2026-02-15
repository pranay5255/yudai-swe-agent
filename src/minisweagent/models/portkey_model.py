import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Literal

import litellm
from pydantic import BaseModel
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from minisweagent.exceptions import FormatError
from minisweagent.models.utils.openai_multimodal import expand_multimodal_content
from minisweagent.models.utils.textbased import format_text_observation_messages, parse_text_actions
from minisweagent.models import GLOBAL_MODEL_STATS
from minisweagent.models.utils.cache_control import set_cache_control

logger = logging.getLogger("portkey_model")

try:
    from portkey_ai import Portkey
except ImportError:
    raise ImportError(
        "The portkey-ai package is required to use PortkeyModel. Please install it with: pip install portkey-ai"
    )


class PortkeyModelConfig(BaseModel):
    model_name: str
    model_kwargs: dict[str, Any] = {}
    litellm_model_registry: Path | str | None = os.getenv("LITELLM_MODEL_REGISTRY_PATH")
    """We currently use litellm to calculate costs. Here you can register additional models to litellm's model registry.
    Note that this might change if we get better support for Portkey and change how we calculate costs.
    """
    litellm_model_name_override: str = ""
    """We currently use litellm to calculate costs. Here you can override the model name to use for litellm in case it
    doesn't match the Portkey model name.
    Note that this might change if we get better support for Portkey and change how we calculate costs.
    """
    set_cache_control: Literal["default_end"] | None = None
    """Set explicit cache control markers, for example for Anthropic models"""
    cost_tracking: Literal["default", "ignore_errors"] = os.getenv("MSWEA_COST_TRACKING", "default")
    """Cost tracking mode for this model. Can be "default" or "ignore_errors" (ignore errors/missing cost info)"""
    format_error_template: str = (
        "Please always provide EXACTLY ONE action in triple backticks, found {{actions|length}} actions."
    )
    observation_template: str = "{{ output.output }}"
    # Python regex string (not YAML-escaped). Keep single backslashes so \s/\n work.
    action_regex: str = r"```(?:mswea_bash_command|bash|sh)\s*\n(.*?)\n```"
    multimodal_regex: str | None = None


class PortkeyModel:
    def __init__(self, *, config_class: type = PortkeyModelConfig, **kwargs):
        self.config = config_class(**kwargs)
        self.cost = 0.0
        self.n_calls = 0
        if self.config.litellm_model_registry and Path(self.config.litellm_model_registry).is_file():
            litellm.utils.register_model(json.loads(Path(self.config.litellm_model_registry).read_text()))

        self._api_key = os.getenv("PORTKEY_API_KEY")
        if not self._api_key:
            raise ValueError(
                "Portkey API key is required. Set it via the "
                "PORTKEY_API_KEY environment variable. You can permanently set it with "
                "`mini-extra config set PORTKEY_API_KEY YOUR_KEY`."
            )

        virtual_key = os.getenv("PORTKEY_VIRTUAL_KEY")
        client_kwargs = {"api_key": self._api_key}
        if virtual_key:
            client_kwargs["virtual_key"] = virtual_key

        self.client = Portkey(**client_kwargs)

    def _prepare_messages_for_api(self, messages: list[dict]) -> list[dict]:
        allowed_keys = {"role", "content", "tool_calls", "tool_call_id", "name"}
        return [{k: v for k, v in msg.items() if k in allowed_keys} for msg in messages]

    @retry(
        reraise=True,
        stop=stop_after_attempt(int(os.getenv("MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT", "10"))),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        retry=retry_if_not_exception_type((KeyboardInterrupt, TypeError, ValueError)),
    )
    def _query(self, messages: list[dict[str, str]], **kwargs):
        return self.client.chat.completions.create(
            model=self.config.model_name,
            messages=messages,
            **(self.config.model_kwargs | kwargs),
        )

    def query(self, messages: list[dict], tools: list[dict] | None = None, **kwargs) -> dict:
        prepared = self._prepare_messages_for_api(messages)
        if self.config.set_cache_control:
            prepared = set_cache_control(prepared, mode=self.config.set_cache_control)
        response = self._query(prepared, **kwargs)
        content = response.choices[0].message.content or ""
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

    def format_message(self, role: str, content: str, **kwargs) -> dict:
        return {"role": role, "content": expand_multimodal_content(content, self.config.multimodal_regex), **kwargs}

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

    def _calculate_cost(self, response) -> dict:
        response_for_cost_calc = response.model_copy()
        if self.config.litellm_model_name_override:
            if response_for_cost_calc.model:
                response_for_cost_calc.model = self.config.litellm_model_name_override
        prompt_tokens = response_for_cost_calc.usage.prompt_tokens
        if prompt_tokens is None:
            logger.warning(
                f"Prompt tokens are None for model {self.config.model_name}. Setting to 0. Full response: {response_for_cost_calc.model_dump()}"
            )
            prompt_tokens = 0
        total_tokens = response_for_cost_calc.usage.total_tokens
        completion_tokens = response_for_cost_calc.usage.completion_tokens
        if completion_tokens is None:
            logger.warning(
                f"Completion tokens are None for model {self.config.model_name}. Setting to 0. Full response: {response_for_cost_calc.model_dump()}"
            )
            completion_tokens = 0
        if total_tokens - prompt_tokens - completion_tokens != 0:
            logger.warning(
                f"WARNING: Total tokens - prompt tokens - completion tokens != 0: {response_for_cost_calc.model_dump()}."
                " This is probably a portkey bug or incompatibility with litellm cost tracking. "
                "Setting prompt tokens based on total tokens and completion tokens. You might want to double check your costs. "
                f"Full response: {response_for_cost_calc.model_dump()}"
            )
            response_for_cost_calc.usage.prompt_tokens = total_tokens - completion_tokens
        try:
            cost = litellm.cost_calculator.completion_cost(
                response_for_cost_calc, model=self.config.litellm_model_name_override or None
            )
            assert cost >= 0.0, f"Cost is negative: {cost}"
        except Exception as e:
            cost = 0.0
            if self.config.cost_tracking != "ignore_errors":
                msg = (
                    f"Error calculating cost for model {self.config.model_name} based on {response_for_cost_calc.model_dump()}: {e}. "
                    "You can ignore this issue from your config file with cost_tracking: 'ignore_errors' or "
                    "globally with export MSWEA_COST_TRACKING='ignore_errors' to ignore this error. "
                    "Alternatively check the 'Cost tracking' section in the documentation at "
                    "https://klieret.short.gy/mini-local-models. "
                    "Still stuck? Please open a github issue at https://github.com/SWE-agent/mini-swe-agent/issues/new/choose!"
                )
                logger.critical(msg)
                raise RuntimeError(msg) from e
        return {"cost": cost}

    def _record_cost(self, cost: float) -> None:
        self.n_calls += 1
        self.cost += cost
        GLOBAL_MODEL_STATS.add(cost)
