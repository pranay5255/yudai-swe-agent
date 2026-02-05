import json
import logging
import os
import time
from typing import Any, Literal

import requests
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

logger = logging.getLogger("openrouter_model")


class OpenRouterModelConfig(BaseModel):
    model_name: str
    model_kwargs: dict[str, Any] = {}
    set_cache_control: Literal["default_end"] | None = None
    """Set explicit cache control markers, for example for Anthropic models"""
    cost_tracking: Literal["default", "ignore_errors"] = os.getenv("MSWEA_COST_TRACKING", "default")
    """Cost tracking mode for this model. Can be "default" or "ignore_errors" (ignore errors/missing cost info)"""
    format_error_template: str = (
        "Please always provide EXACTLY ONE action in triple backticks, found {{actions|length}} actions."
    )
    observation_template: str = "{{ output.output }}"
    action_regex: str = r"```mswea_bash_command\\s*\\n(.*?)\\n```"
    multimodal_regex: str | None = None


class OpenRouterAPIError(Exception):
    """Custom exception for OpenRouter API errors."""


class OpenRouterAuthenticationError(Exception):
    """Custom exception for OpenRouter authentication errors."""


class OpenRouterRateLimitError(Exception):
    """Custom exception for OpenRouter rate limit errors."""


class OpenRouterModel:
    def __init__(self, **kwargs):
        self.config = OpenRouterModelConfig(**kwargs)
        self.cost = 0.0
        self.n_calls = 0
        self._api_url = "https://openrouter.ai/api/v1/chat/completions"
        self._api_key = os.getenv("OPENROUTER_API_KEY", "")

    def _prepare_messages_for_api(self, messages: list[dict]) -> list[dict]:
        allowed_keys = {"role", "content", "tool_calls", "tool_call_id", "name"}
        return [{k: v for k, v in msg.items() if k in allowed_keys} for msg in messages]

    @retry(
        reraise=True,
        stop=stop_after_attempt(int(os.getenv("MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT", "10"))),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        retry=retry_if_not_exception_type((OpenRouterAuthenticationError, KeyboardInterrupt)),
    )
    def _query(self, messages: list[dict[str, Any]], **kwargs):
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "usage": {"include": True},
            **(self.config.model_kwargs | kwargs),
        }

        try:
            response = requests.post(self._api_url, headers=headers, data=json.dumps(payload), timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                error_msg = (
                    "Authentication failed. You can permanently set your API key with "
                    "`mini-extra config set OPENROUTER_API_KEY YOUR_KEY`."
                )
                raise OpenRouterAuthenticationError(error_msg) from e
            if response.status_code == 429:
                raise OpenRouterRateLimitError("Rate limit exceeded") from e
            raise OpenRouterAPIError(f"HTTP {response.status_code}: {response.text}") from e
        except requests.exceptions.RequestException as e:
            raise OpenRouterAPIError(f"Request failed: {e}") from e

    def query(self, messages: list[dict], tools: list[dict] | None = None, **kwargs) -> dict:
        response = self._query(self._prepare_messages_for_api(messages), **kwargs)
        content = response["choices"][0]["message"]["content"] or ""
        usage = response.get("usage", {})
        cost = usage.get("cost", 0.0)
        if cost <= 0.0 and self.config.cost_tracking != "ignore_errors":
            raise RuntimeError(
                f"No valid cost information available from OpenRouter API for model {self.config.model_name}: "
                f"Usage {usage}, cost {cost}. Cost must be > 0.0. Set cost_tracking: 'ignore_errors' in your config file or "
                "export MSWEA_COST_TRACKING='ignore_errors' to ignore cost tracking errors "
                "(for example for free/local models), more information at https://klieret.short.gy/mini-local-models "
                "for more details. Still stuck? Please open a github issue at https://github.com/SWE-agent/mini-swe-agent/issues/new/choose!"
            )

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
                extra = {"response": response, "cost": cost, "timestamp": time.time()}
                self._record_cost(cost)
                raise FormatError(str(e), extra=extra) from e

        self._record_cost(cost)
        return {
            "content": content,
            "extra": {
                "response": response,
                "actions": actions,
                "cost": cost,
                "timestamp": time.time(),
            },
        }

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

    def _record_cost(self, cost: float) -> None:
        self.n_calls += 1
        self.cost += cost
        GLOBAL_MODEL_STATS.add(cost)

<<<<<<< HEAD
        if "error" in response:
            error = response["error"]
            raise OpenRouterAPIError(
                f"OpenRouter API error: {error.get('message', 'Unknown error')} (code: {error.get('code', 'unknown')})"
            )

        if "choices" not in response or not response["choices"]:
            raise OpenRouterAPIError(f"Invalid OpenRouter API response: missing 'choices' field. Response: {response}")

        return {
            "content": response["choices"][0]["message"]["content"] or "",
            "extra": {
                "response": response,  # already is json
            },
        }
=======
>>>>>>> ec8042e (feat: v2 tool-calling agent flow)

class OpenRouterTextBasedModel(OpenRouterModel):
    pass


class OpenRouterResponseModel(OpenRouterModel):
    pass
