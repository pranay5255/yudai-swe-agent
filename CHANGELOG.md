# Changelog

## [Unreleased] - 2026-02-16

### Added

- **V3 Exploit Harness**: Complete v3 exploit generation pipeline
  - `FoundryEnvironmentV3` with enhanced Anvil fork management (`foundry_v3.py`)
  - `ExploitFoundryEnvironmentV3` with v3 command parser (`exploit_environment_v3.py`)
  - `benchmark_exploit_v3.yaml` configuration for v3 benchmark runs
  - `run_benchmark_exploit_v3.py` runner script with early failure detection support
  - Registered `foundry_v3` and `exploit_foundry_v3` in environment mapping

- **Early Failure Detection**: Trajectory-based abort mechanism
  - `FailureDetector` class detects unrecoverable patterns (e.g. "contract not verified")
  - `_build_failure_aware_agent_class` wraps any agent with early abort on detected failure
  - `EarlyFailureDetected` exception for clean abort signaling

- **Real DEX Integration**: Upgraded `DexUtils.sol` from mock event emissions to real on-chain swaps via Uniswap V2 (Ethereum, Base) and PancakeSwap V2 (BSC) routers

- **V3 Benchmark Results**: Initial v3 run results for bancor, opyn, and bzx test cases

- **Submodule**: Added `yudai-grep` repository reference

### Fixed

- **Agent Timestamp Handling**: Prevent duplicate `timestamp` kwargs in `DefaultAgent.add_message()`, exception handling, and query response formatting using `setdefault()`
- **Action Dict Support**: `ExploitFoundryEnvironmentV2.execute()` now accepts action dicts via `get_action_command()`
- **Action Regex Escaping**: Fixed double-escaped backslashes (`\\s` -> `\s`) across all model configs (litellm, openrouter, portkey, requesty, test_models) and added `bash`/`sh` fence support
- **OpenRouter Error Handling**: Moved error/choices validation before content extraction, added defensive `.get()` access, and removed leftover merge conflict markers

### Security

- **API Key Masking**: Added `_mask_api_key()` to `foundry_v2.py` to prevent accidental leakage of Alchemy/Infura keys in RPC URLs into logs and agent prompts

### Tests

- V3 environment tests: parser matching, action dict acceptance
- `exploit_foundry_v3` shorthand resolution test
- Failure detector and failure-aware agent unit tests
- V3 task prompt content verification (batching, BSC legacy note)
- `_build_error_message` handler tests
- V3 benchmark runner integration test with v3-specific env defaults
