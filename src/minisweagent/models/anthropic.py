from typing import Literal

from minisweagent.models.litellm_model import LitellmModel, LitellmModelConfig


class AnthropicModelConfig(LitellmModelConfig):
    set_cache_control: Literal["default_end"] | None = "default_end"
    """Set explicit cache control markers, for example for Anthropic models"""


class AnthropicModel(LitellmModel):
    """Legacy wrapper around the LitellmModel class for backwards compatibility."""

    def __init__(self, *, config_class: type = AnthropicModelConfig, **kwargs):
        super().__init__(config_class=config_class, **kwargs)
