import random

from pydantic import BaseModel

from minisweagent import Model
from minisweagent.models import get_model


class RouletteModelConfig(BaseModel):
    model_kwargs: list[dict]
    """The models to choose from"""
    model_name: str = "roulette"


class RouletteModel:
    def __init__(self, *, config_class: type = RouletteModelConfig, **kwargs):
        """This "meta"-model randomly selects one of the models at every call"""
        self.config = config_class(**kwargs)
        self.models = [get_model(config=config) for config in self.config.model_kwargs]
        self._last_model: Model | None = None

    @property
    def cost(self) -> float:
        return sum(model.cost for model in self.models)

    @property
    def n_calls(self) -> int:
        return sum(model.n_calls for model in self.models)

    def get_template_vars(self) -> dict:
        return self.config.model_dump() | {"n_model_calls": self.n_calls, "model_cost": self.cost}

    def select_model(self) -> Model:
        return random.choice(self.models)

    def query(self, *args, **kwargs) -> dict:
        model = self.select_model()
        self._last_model = model
        response = model.query(*args, **kwargs)
        response["model_name"] = model.config.model_name
        return response

    def format_message(self, role: str, content: str, **kwargs) -> dict:
        # Use the first model as default formatter for system/user messages.
        return self.models[0].format_message(role, content, **kwargs)

    def format_observation_messages(self, observation: list[dict], *, message: dict | None = None) -> list[dict]:
        model = self._last_model or self.models[0]
        return model.format_observation_messages(observation, message=message)

    def serialize(self) -> dict:
        return self.config.model_dump()


class InterleavingModelConfig(BaseModel):
    model_kwargs: list[dict]
    sequence: list[int] | None = None
    """If set to 0, 0, 1, we will return the first model 2 times, then the second model 1 time,
    then the first model again, etc."""
    model_name: str = "interleaving"


class InterleavingModel(RouletteModel):
    def __init__(self, *, config_class: type = InterleavingModelConfig, **kwargs):
        """This "meta"-model alternates between the models in the sequence for every call"""
        super().__init__(config_class=config_class, **kwargs)

    def select_model(self) -> Model:
        if self.config.sequence is None:
            i_model = self.n_calls % len(self.models)
        else:
            i_model = self.config.sequence[self.n_calls % len(self.config.sequence)]
        return self.models[i_model]
