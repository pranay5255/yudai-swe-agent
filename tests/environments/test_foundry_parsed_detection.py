import pytest

from minisweagent.environments.extra.foundry_parsed import BlockchainCommandParser
from minisweagent.environments.extra.foundry_parsed_v2 import BlockchainCommandParserV2


@pytest.mark.parametrize("parser", [BlockchainCommandParser(), BlockchainCommandParserV2()])
def test_parser_ignores_non_anvil_commands_containing_anvil_text(parser):
    result = parser.parse(
        "pgrep -fa '(^|/)anvil([[:space:]]|$).*--port' || echo 'not_running'",
        {"output": "not_running\n", "returncode": 0},
    )
    assert result is None

    result = parser.parse(
        "cat /tmp/anvil.log 2>/dev/null || echo 'no_log'",
        {"output": "error: unexpected argument '--fork-retries' found\n", "returncode": 0},
    )
    assert result is None


@pytest.mark.parametrize("parser", [BlockchainCommandParser(), BlockchainCommandParserV2()])
def test_parser_detects_real_anvil_command(parser):
    result = parser.parse(
        "anvil --port 8545",
        {"output": "Listening on 127.0.0.1:8545\n", "returncode": 0},
    )
    assert result is not None
    assert result["kind"] == "anvil"
    assert "listening on 127.0.0.1:8545" in result["summary"].lower()


@pytest.mark.parametrize("parser", [BlockchainCommandParser(), BlockchainCommandParserV2()])
def test_parser_detects_nohup_prefixed_anvil_command(parser):
    result = parser.parse(
        "nohup anvil --port 8545 > /tmp/anvil.log 2>&1 &",
        {"output": "Listening on 127.0.0.1:8545\n", "returncode": 0},
    )
    assert result is not None
    assert result["kind"] == "anvil"
