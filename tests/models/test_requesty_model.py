import json
import os
from unittest.mock import patch

import pytest

from minisweagent.models import GLOBAL_MODEL_STATS
from minisweagent.models.requesty_model import RequestyAPIError, RequestyModel


@pytest.fixture
def mock_response():
    """Create a mock successful Requesty API response."""
    return {
        "choices": [{"message": {"content": "```mswea_bash_command\necho 'hi'\n```"}}],
        "usage": {
            "prompt_tokens": 16,
            "completion_tokens": 13,
            "total_tokens": 29,
            "cost": 0.000243,
        },
    }


def test_requesty_model_successful_query(mock_response):
    """Test successful Requesty API query with cost tracking."""
    with patch.dict(os.environ, {"REQUESTY_API_KEY": "test-key"}):
        model = RequestyModel(model_name="openai/gpt-4.1-mini", model_kwargs={"temperature": 0.7})

        initial_cost = GLOBAL_MODEL_STATS.cost

        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status.return_value = None

            messages = [{"role": "user", "content": "Hello! What is 2+2?"}]
            result = model.query(messages)

            mock_post.assert_called_once()
            call_args = mock_post.call_args

            assert call_args[0][0] == "https://router.requesty.ai/v1/chat/completions"

            headers = call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer test-key"
            assert headers["Content-Type"] == "application/json"
            assert headers["HTTP-Referer"] == "https://github.com/SWE-agent/mini-swe-agent"
            assert headers["X-Title"] == "mini-swe-agent"

            payload = json.loads(call_args[1]["data"])
            assert payload["model"] == "openai/gpt-4.1-mini"
            assert payload["messages"] == messages
            assert payload["temperature"] == 0.7

            assert result["content"] == "```mswea_bash_command\necho 'hi'\n```"
            assert result["extra"]["response"] == mock_response
            assert model.cost == 0.000243
            assert model.n_calls == 1
            assert GLOBAL_MODEL_STATS.cost == initial_cost + 0.000243


def test_requesty_model_api_error_response():
    """Test structured API error responses are surfaced before accessing choices."""
    with patch.dict(os.environ, {"REQUESTY_API_KEY": "test-key"}):
        model = RequestyModel(model_name="openai/gpt-4.1-mini")

        with patch.object(
            model,
            "_query",
            return_value={"error": {"message": "Upstream failure", "code": "upstream_error"}},
        ):
            with pytest.raises(RequestyAPIError, match="Upstream failure"):
                model.query([{"role": "user", "content": "test"}])


def test_requesty_model_missing_choices_raises():
    """Test Requesty rejects responses without choices instead of raising KeyError."""
    with patch.dict(os.environ, {"REQUESTY_API_KEY": "test-key"}):
        model = RequestyModel(model_name="openai/gpt-4.1-mini")

        with patch.object(model, "_query", return_value={"usage": {"cost": 0.000243}}):
            with pytest.raises(RequestyAPIError, match="missing 'choices' field"):
                model.query([{"role": "user", "content": "test"}])


def test_requesty_model_no_cost_information(mock_response):
    """Test error when cost information is missing."""
    with patch.dict(os.environ, {"REQUESTY_API_KEY": "test-key"}):
        model = RequestyModel(model_name="openai/gpt-4.1-mini")

        response_without_cost = {"choices": mock_response["choices"], "usage": {}}
        with patch.object(model, "_query", return_value=response_without_cost):
            with pytest.raises(RequestyAPIError, match="No cost information available"):
                model.query([{"role": "user", "content": "test"}])
