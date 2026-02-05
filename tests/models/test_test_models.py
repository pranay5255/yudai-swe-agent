import logging
import time

from minisweagent.models.test_models import DeterministicModel, DeterministicModelConfig


def test_basic_functionality_and_cost_tracking(reset_global_stats):
    """Test basic model functionality, cost tracking, and default configuration."""
    model = DeterministicModel(
        outputs=[
            "```bash\necho 'Hello'\n```",
            "```bash\necho 'World'\n```",
        ]
    )

    # Test first call with defaults
    result = model.query([{"role": "user", "content": "test"}])
    assert result["content"] == "```bash\necho 'Hello'\n```"
    assert model.n_calls == 1
    assert model.cost == 1.0
    # Test second call and sequential outputs
    result = model.query([{"role": "user", "content": "test"}])
    assert result["content"] == "```bash\necho 'World'\n```"
    assert model.n_calls == 2
    assert model.cost == 2.0


def test_custom_cost_and_multiple_models(reset_global_stats):
    """Test custom cost configuration and global tracking across multiple models."""
    model1 = DeterministicModel(outputs=["```bash\necho 'Response1'\n```"], cost_per_call=2.5)
    model2 = DeterministicModel(outputs=["```bash\necho 'Response2'\n```"], cost_per_call=3.0)

    assert model1.query([{"role": "user", "content": "test"}])["content"] == "```bash\necho 'Response1'\n```"
    assert model1.cost == 2.5

    assert model2.query([{"role": "user", "content": "test"}])["content"] == "```bash\necho 'Response2'\n```"
    assert model2.cost == 3.0


def test_config_dataclass():
    """Test DeterministicModelConfig with custom values."""
    config = DeterministicModelConfig(outputs=["Test"], model_name="custom", cost_per_call=5.0)

    assert config.cost_per_call == 5.0
    assert config.model_name == "custom"

    model = DeterministicModel(**config.__dict__)
    assert model.config.cost_per_call == 5.0


def test_sleep_and_warning_commands(caplog):
    """Test special /sleep and /warning command handling."""
    # Test sleep command - processes sleep then returns actual output (counts as 1 call)
    model = DeterministicModel(outputs=["/sleep0.1", "```bash\necho 'After sleep'\n```"])
    start_time = time.time()
    assert model.query([{"role": "user", "content": "test"}])["content"] == "```bash\necho 'After sleep'\n```"
    assert time.time() - start_time >= 0.1
    assert model.n_calls == 1  # Sleep no longer counts as separate call

    # Test warning command - processes warning then returns actual output (counts as 1 call)
    model2 = DeterministicModel(outputs=["/warningTest message", "```bash\necho 'After warning'\n```"])
    with caplog.at_level(logging.WARNING):
        assert model2.query([{"role": "user", "content": "test"}])["content"] == "```bash\necho 'After warning'\n```"
    assert model2.n_calls == 1  # Warning no longer counts as separate call
    assert "Test message" in caplog.text
