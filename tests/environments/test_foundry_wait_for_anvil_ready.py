import logging
from types import SimpleNamespace

import pytest

from minisweagent.environments.foundry import FoundryEnvironment
from minisweagent.environments.foundry_v2 import FoundryEnvironmentV2


def _make_env(env_cls):
    env = env_cls.__new__(env_cls)
    env._foundry_config = SimpleNamespace(anvil_port=8545, image="test-image")  # noqa: SLF001
    env.logger = logging.getLogger(f"tests.{env_cls.__name__}")
    return env


@pytest.mark.parametrize("env_cls", [FoundryEnvironment, FoundryEnvironmentV2])
def test_wait_for_anvil_ready_uses_raw_output_for_failure_diagnosis(env_cls):
    env = _make_env(env_cls)

    def fake_execute(command: str, cwd: str = "", *, timeout: int | None = None):  # noqa: ARG001
        if command.startswith("pgrep "):
            return {"output": "anvil: started\n", "raw_output": "not_running\n", "returncode": 0}
        if command.startswith("cat /tmp/anvil.log"):
            return {
                "output": "anvil: started\n",
                "raw_output": "error: unexpected argument '--fork-retries' found\n",
                "returncode": 0,
            }
        raise AssertionError(f"Unexpected command: {command}")

    env.execute = fake_execute
    status = env._wait_for_anvil_ready(  # noqa: SLF001
        fork_url="https://rpc.example",
        block_number=1234,
        timeout=2,
    )

    assert status["running"] is False
    assert "--fork-retries" in status["error"]
    assert "anvil: started" not in status["error"]


@pytest.mark.parametrize("env_cls", [FoundryEnvironment, FoundryEnvironmentV2])
def test_wait_for_anvil_ready_reports_missing_cast_from_raw_output(env_cls):
    env = _make_env(env_cls)

    def fake_execute(command: str, cwd: str = "", *, timeout: int | None = None):  # noqa: ARG001
        if command.startswith("pgrep "):
            return {
                "output": "12345 anvil --port 8545\n",
                "raw_output": "12345 anvil --port 8545\n",
                "returncode": 0,
            }
        if command.startswith("cast chain-id"):
            return {
                "output": "anvil: started\n",
                "raw_output": "bash: cast: command not found\n",
                "returncode": 127,
            }
        raise AssertionError(f"Unexpected command: {command}")

    env.execute = fake_execute
    status = env._wait_for_anvil_ready(  # noqa: SLF001
        fork_url="https://rpc.example",
        block_number=1234,
        timeout=2,
    )

    assert status["running"] is False
    assert "`cast` is not available" in status["error"]
