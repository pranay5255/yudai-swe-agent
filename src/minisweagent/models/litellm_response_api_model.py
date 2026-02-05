import logging
from collections.abc import Callable

import litellm
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from minisweagent.exceptions import FormatError
from minisweagent.models.litellm_textbased_model import LitellmTextBasedModel, LitellmTextBasedModelConfig
from minisweagent.models.utils.openai_utils import coerce_responses_text
from minisweagent.models.utils.retry import abort_exceptions

logger = logging.getLogger("litellm_response_api_model")


class LitellmResponseModelConfig(LitellmTextBasedModelConfig):
    pass


class LitellmResponseModel(LitellmTextBasedModel):
    def __init__(self, *, config_class: Callable = LitellmResponseModelConfig, **kwargs):
        super().__init__(config_class=config_class, **kwargs)
        self._previous_response_id: str | None = None

    @retry(
        reraise=True,
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        retry=retry_if_not_exception_type(abort_exceptions()),
    )
    def _query(self, messages: list[dict], **kwargs):
        try:
            clean_messages = [{"role": msg["role"], "content": msg["content"]} for msg in messages]
            resp = litellm.responses(
                model=self.config.model_name,
                input=clean_messages if self._previous_response_id is None else clean_messages[-1:],
                previous_response_id=self._previous_response_id,
                **(self.config.model_kwargs | kwargs),
            )
            self._previous_response_id = getattr(resp, "id", None)
            return resp
        except litellm.exceptions.AuthenticationError as e:
            e.message += " You can permanently set your API key with `mini-extra config set KEY VALUE`."
            raise e

    def query(self, messages: list[dict], tools: list[dict] | None = None, **kwargs) -> dict:
        response = self._query(self._prepare_messages_for_api(messages), **kwargs)
        content = coerce_responses_text(response)
        cost_info = self._calculate_cost(response)
        cost = cost_info.get("cost", 0.0) or 0.0
        actions = []
        if tools is not None:
            try:
                actions = self._parse_actions_from_content(content)
            except FormatError as e:
                extra = {"response": response.model_dump()}
                extra.update(cost_info)
                self._record_cost(cost)
                raise FormatError(str(e), extra=extra) from e
        extra = {
            "response": response.model_dump(),
            "actions": actions,
        }
        extra.update(cost_info)
        self._record_cost(cost)
        return {"content": content, "extra": extra}

    def _parse_actions_from_content(self, content: str) -> list[dict]:
        from minisweagent.models.utils.textbased import parse_text_actions

        return parse_text_actions(
            {"content": content},
            action_regex=self.config.action_regex,
            format_error_template=self.config.format_error_template,
            template_vars=self.config.model_dump(),
        )


# Backwards compatibility
LitellmResponseAPIModel = LitellmResponseModel
