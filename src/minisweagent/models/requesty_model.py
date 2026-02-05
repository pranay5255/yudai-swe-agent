import json
import logging
import os
import time
from typing import Any

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

logger = logging.getLogger("requesty_model")


class RequestyModelConfig(BaseModel):
    model_name: str
    model_kwargs: dict[str, Any] = {}
    format_error_template: str = (
        "Please always provide EXACTLY ONE action in triple backticks, found {{actions|length}} actions."
    )
    observation_template: str = "{{ output.output }}"
    action_regex: str = r"```mswea_bash_command\\s*\\n(.*?)\\n```"
    multimodal_regex: str | None = None


class RequestyAPIError(Exception):
    """Custom exception for Requesty API errors."""


class RequestyAuthenticationError(Exception):
    """Custom exception for Requesty authentication errors."""


class RequestyRateLimitError(Exception):
    """Custom exception for Requesty rate limit errors."""


class RequestyModel:
    def __init__(self, **kwargs):
        self.config = RequestyModelConfig(**kwargs)
        self.cost = 0.0
        self.n_calls = 0
        self._api_url = "https://router.requesty.ai/v1/chat/completions"
        self._api_key = os.getenv("REQUESTY_API_KEY", "")

    def _prepare_messages_for_api(self, messages: list[dict]) -> list[dict]:
        allowed_keys = {"role", "content", "tool_calls", "tool_call_id", "name"}
        return [{k: v for k, v in msg.items() if k in allowed_keys} for msg in messages]

    @retry(
        reraise=True,
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        retry=retry_if_not_exception_type((RequestyAuthenticationError, KeyboardInterrupt)),
    )
    def _query(self, messages: list[dict[str, str]], **kwargs):
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/SWE-agent/mini-swe-agent",
            "X-Title": "mini-swe-agent",
        }

        payload = {
            "model": self.config.model_name,
            "messages": messages,
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
                    "`mini-extra config set REQUESTY_API_KEY YOUR_KEY`."
                )
                raise RequestyAuthenticationError(error_msg) from e
            if response.status_code == 429:
                raise RequestyRateLimitError("Rate limit exceeded") from e
            raise RequestyAPIError(f"HTTP {response.status_code}: {response.text}") from e
        except requests.exceptions.RequestException as e:
            raise RequestyAPIError(f"Request failed: {e}") from e

    def query(self, messages: list[dict], tools: list[dict] | None = None, **kwargs) -> dict:
        response = self._query(self._prepare_messages_for_api(messages), **kwargs)
        content = response["choices"][0]["message"]["content"] or ""
        usage = response.get("usage", {})
        cost = usage.get("cost", 0.0)
        if cost == 0.0:
            raise RequestyAPIError(
                f"No cost information available from Requesty API for model {self.config.model_name}. "
                "Cost tracking is required but not provided by the API response."
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

<<<<<<< HEAD
        if "error" in response:
            error = response["error"]
            raise RequestyAPIError(
                f"Requesty API error: {error.get('message', 'Unknown error')} (code: {error.get('code', 'unknown')})"
            )

        if "choices" not in response or not response["choices"]:
            raise RequestyAPIError(f"Invalid Requesty API response: missing 'choices' field. Response: {response}")

=======
        self._record_cost(cost)
>>>>>>> ec8042e (feat: v2 tool-calling agent flow)
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
