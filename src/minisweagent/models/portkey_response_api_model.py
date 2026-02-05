import logging
import os

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from minisweagent.exceptions import FormatError
from minisweagent.models.portkey_model import PortkeyModel, PortkeyModelConfig
from minisweagent.models.utils.cache_control import set_cache_control
from minisweagent.models.utils.openai_utils import coerce_responses_text

logger = logging.getLogger("portkey_response_api_model")


class PortkeyResponseModelConfig(PortkeyModelConfig):
    pass


class PortkeyResponseModel(PortkeyModel):
    def __init__(self, *, config_class: type = PortkeyResponseModelConfig, **kwargs):
        super().__init__(config_class=config_class, **kwargs)
        self._previous_response_id: str | None = None

    @retry(
        reraise=True,
        stop=stop_after_attempt(int(os.getenv("MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT", "10"))),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        retry=retry_if_not_exception_type((KeyboardInterrupt, TypeError, ValueError)),
    )
    def _query(self, messages: list[dict], **kwargs):
        input_messages = messages if self._previous_response_id is None else messages[-1:]
        resp = self.client.responses.create(
            model=self.config.model_name,
            input=input_messages,
            previous_response_id=self._previous_response_id,
            **(self.config.model_kwargs | kwargs),
        )
        self._previous_response_id = getattr(resp, "id", None)
        return resp

    def query(self, messages: list[dict], tools: list[dict] | None = None, **kwargs) -> dict:
        prepared = self._prepare_messages_for_api(messages)
        if self.config.set_cache_control:
            prepared = set_cache_control(prepared, mode=self.config.set_cache_control)
        response = self._query(prepared, **kwargs)
        content = coerce_responses_text(response)
        cost_info = self._calculate_cost(response)
        cost = cost_info.get("cost", 0.0) or 0.0
        actions = []
        if tools is not None:
            try:
                actions = self._parse_actions_from_content(content)
            except FormatError as e:
                extra = {"response": response.model_dump() if hasattr(response, "model_dump") else {}}
                extra.update(cost_info)
                self._record_cost(cost)
                raise FormatError(str(e), extra=extra) from e
        extra = {
            "response": response.model_dump() if hasattr(response, "model_dump") else {},
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
PortkeyResponseAPIModel = PortkeyResponseModel
