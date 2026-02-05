import json
import logging
import os
import time
from collections.abc import Callable
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
from minisweagent.models.utils.actions_toolcall import (
    BASH_TOOL,
    format_toolcall_observation_messages,
    parse_toolcall_actions,
)
from minisweagent.models import GLOBAL_MODEL_STATS
from minisweagent.models.utils.anthropic_utils import reorder_blocks
from minisweagent.models.utils.openai_multimodal import expand_multimodal_content
from minisweagent.models.utils.retry import abort_exceptions
from minisweagent.models.utils.cache_control import set_cache_control

logger = logging.getLogger("litellm_model")


class LitellmModelConfig(BaseModel):
    model_name: str
    model_kwargs: dict[str, Any] = {}
    litellm_model_registry: Path | str | None = os.getenv("LITELLM_MODEL_REGISTRY_PATH")
    set_cache_control: Literal["default_end"] | None = None
    """Set explicit cache control markers, for example for Anthropic models"""
    cost_tracking: Literal["default", "ignore_errors"] = os.getenv("MSWEA_COST_TRACKING", "default")
    """Cost tracking mode for this model. Can be "default" or "ignore_errors" (ignore errors/missing cost info)"""
    format_error_template: str = (
        "Please always provide EXACTLY ONE action in triple backticks, found {{actions|length}} actions."
    )
    observation_template: str = "{{ output.output }}"
    multimodal_regex: str | None = None


class LitellmModel:
    def __init__(self, *, config_class: Callable = LitellmModelConfig, **kwargs):
        self.config = config_class(**kwargs)
        self.cost = 0.0
        self.n_calls = 0
        if self.config.litellm_model_registry and Path(self.config.litellm_model_registry).is_file():
            litellm.utils.register_model(json.loads(Path(self.config.litellm_model_registry).read_text()))

    def _prepare_messages_for_api(self, messages: list[dict]) -> list[dict]:
        allowed_keys = {"role", "content", "tool_calls", "tool_call_id", "name"}
        prepared: list[dict] = []
        for message in messages:
            message = reorder_blocks(message)
            prepared.append({k: v for k, v in message.items() if k in allowed_keys})
        if self.config.set_cache_control:
            prepared = set_cache_control(prepared, mode=self.config.set_cache_control)
        return prepared

    @retry(
        reraise=True,
        stop=stop_after_attempt(int(os.getenv("MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT", "10"))),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        retry=retry_if_not_exception_type(abort_exceptions()),
    )
    def _query(self, messages: list[dict[str, Any]], **kwargs):
        try:
            return litellm.completion(model=self.config.model_name, messages=messages, **(self.config.model_kwargs | kwargs))
        except litellm.exceptions.AuthenticationError as e:
            e.message += " You can permanently set your API key with `mini-extra config set KEY VALUE`."
            raise e

    def _calculate_cost(self, response) -> dict:
        try:
            cost = litellm.cost_calculator.completion_cost(response, model=self.config.model_name)
            if cost < 0.0:
                raise ValueError(f"Cost must be >= 0.0, got {cost}")
        except Exception as e:
            cost = 0.0
            if self.config.cost_tracking != "ignore_errors":
                msg = (
                    f"Error calculating cost for model {self.config.model_name}: {e}, perhaps it's not registered? "
                    "You can ignore this issue from your config file with cost_tracking: 'ignore_errors' or "
                    "globally with export MSWEA_COST_TRACKING='ignore_errors'. "
                    "Alternatively check the 'Cost tracking' section in the documentation at "
                    "https://klieret.short.gy/mini-local-models. "
                    "Still stuck? Please open a github issue at https://github.com/SWE-agent/mini-swe-agent/issues/new/choose!"
                )
                logger.critical(msg)
                raise RuntimeError(msg) from e
        return {"cost": cost}

    def _parse_actions(self, response) -> list[dict]:
        message = response.choices[0].message  # type: ignore[index]
        tool_calls = getattr(message, "tool_calls", None) or getattr(message, "tool_call", None)
        template_vars = self.config.model_dump()
        return parse_toolcall_actions(
            tool_calls,
            format_error_template=self.config.format_error_template,
            template_vars=template_vars,
        )

    def query(self, messages: list[dict[str, Any]], tools: list[dict] | None = None, **kwargs) -> dict:
        use_tools = tools is not None
        response = self._query(
            self._prepare_messages_for_api(messages),
            **({"tools": tools or [BASH_TOOL]} if use_tools else {}),
            **kwargs,
        )
        tool_calls = response.choices[0].message.tool_calls if use_tools else []  # type: ignore[index]
        cost_info = self._calculate_cost(response)
        cost = cost_info.get("cost", 0.0) or 0.0
        try:
            actions = self._parse_actions(response) if use_tools else []
        except FormatError as e:
            extra = {
                "response": response.model_dump(),
                "tool_calls": tool_calls,
                "timestamp": time.time(),
            }
            extra.update(cost_info)
            self._record_cost(cost)
            raise FormatError(str(e), extra=extra) from e
        extra = {
            "response": response.model_dump(),
            "tool_calls": tool_calls,
            "actions": actions,
            "timestamp": time.time(),
        }
        extra.update(cost_info)
        self._record_cost(cost)
        return {
            "content": response.choices[0].message.content or "",  # type: ignore[index]
            "extra": extra,
        }

    def _record_cost(self, cost: float) -> None:
        self.n_calls += 1
        self.cost += cost
        GLOBAL_MODEL_STATS.add(cost)

    def format_message(self, role: str, content: str, **kwargs) -> dict:
        return {"role": role, "content": expand_multimodal_content(content, self.config.multimodal_regex), **kwargs}

    def format_observation_messages(self, observation: list[dict], *, message: dict | None = None) -> list[dict]:
        return format_toolcall_observation_messages(
            observation,
            message=message,
            observation_template=self.config.observation_template,
            template_vars=self.config.model_dump(),
        )

    def get_template_vars(self) -> dict[str, Any]:
        return self.config.model_dump() | {"n_model_calls": self.n_calls, "model_cost": self.cost}

    def serialize(self) -> dict[str, Any]:
        return self.config.model_dump()
