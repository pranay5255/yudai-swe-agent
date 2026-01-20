# TASKS.md - Yudai RL Training System

This document tracks implementation tasks for the Yudai RL Training System.

**Phases**:
- **Phase 1**: Vulnerability injection pipeline and dataset creation (EXISTING)
- **Phase 2**: Exploit generation pipeline using A1 architecture (NEW)

---

# Phase 1: Vulnerability Injection & Dataset Creation

**Scope**: Vulnerability injection pipeline and dataset creation only.
**Out of Scope**: RL training loop, reward computation (Phase 2).

---

## Overview

```
Phase 1 Milestone: End-to-end pipeline that:
1. Takes a clean Solidity contract
2. Injects a vulnerability using MuSe
3. Produces a training pair (original, vulnerable, metadata)
4. Validates the pair works with mini-swe-agent
```

---

## Checkpoint 0: Environment Setup

### T0.1: Verify MuSe Installation
- [ ] Install MuSe dependencies: `cd MuSe && npm install`
- [ ] Verify MuSe CLI works: `npx sumo list`
- [ ] Test basic mutation: create test contract, run `npx sumo mutate`
- [ ] Document any issues with current MuSe setup

**Acceptance Criteria**: Running `npx sumo list` shows all 11 MuSe operators.

### T0.2: Test MuSe with Sample Contract
- [ ] Create `test_contracts/SimpleToken.sol` - basic ERC20-like contract
- [ ] Configure `sumo-config.js` pointing to test_contracts/
- [ ] Enable RE, TX, UC operators
- [ ] Run mutation and verify output in `sumo/results/`
- [ ] Inspect generated mutants for correctness

**Acceptance Criteria**: At least 3 different mutants generated with valid metadata.

### T0.3: Verify Docker Environment
- [ ] Ensure `yudai-complete` Docker image is available
- [ ] Test forge build inside container
- [ ] Test slither inside container
- [ ] Test aderyn inside container
- [ ] Document container startup command

**Acceptance Criteria**: All tools (forge, slither, aderyn) run successfully in Docker.

---

## Checkpoint 1: MuSe Python Wrapper

### T1.1: Create vulnerability_injection Package Structure
```
vulnerability_injection/
├── __init__.py
├── muse_wrapper.py
├── models.py           # Dataclasses for mutations
├── config/
│   └── operators.yaml  # Operator configuration
└── tests/
    └── test_muse_wrapper.py
```

- [ ] Create directory structure
- [ ] Create `__init__.py` with exports
- [ ] Create `models.py` with dataclasses:
  - `MuseMutation`
  - `BugLocation`
  - `BugMetadata`

**Acceptance Criteria**: `from vulnerability_injection import MuseInjector` works.

### T1.2: Implement MuseInjector Core
File: `vulnerability_injection/muse_wrapper.py`

- [ ] Implement `__init__(operators: list[str])`
- [ ] Implement `_configure_operators()` - enable/disable operators via CLI
- [ ] Implement `_setup_workspace(contract_path)` - create temp dir with contract
- [ ] Implement `_parse_mutations(mutations_file)` - parse JSON output
- [ ] Implement `_copy_mutants(workspace, output_dir)` - copy sol files

**Acceptance Criteria**: Unit tests pass for each method.

### T1.3: Implement inject() Method
- [ ] Implement full `inject(contract_path, output_dir) -> list[MuseMutation]`
- [ ] Handle subprocess errors gracefully
- [ ] Clean up temporary workspace after completion
- [ ] Return list of mutations with full metadata

**Acceptance Criteria**:
```python
injector = MuseInjector(["RE", "TX"])
mutations = injector.inject(Path("test.sol"), Path("output/"))
assert len(mutations) > 0
assert all(m.operator in ["RE", "TX"] for m in mutations)
```

### T1.4: Add Operator Configuration
File: `vulnerability_injection/config/operators.yaml`

```yaml
operators:
  RE:
    name: "Reentrancy"
    severity: "critical"
    detection_tools: ["slither", "mythril"]
  TX:
    name: "tx.origin Authentication"
    severity: "high"
    detection_tools: ["slither", "aderyn"]
  # ... etc
```

- [ ] Create YAML configuration for all 11 MuSe operators
- [ ] Add loader function to read config
- [ ] Use config for metadata enrichment

**Acceptance Criteria**: Config loads and provides metadata for all operators.

### T1.5: Write Unit Tests
File: `vulnerability_injection/tests/test_muse_wrapper.py`

- [ ] Test operator configuration
- [ ] Test workspace setup
- [ ] Test mutation parsing
- [ ] Test full injection flow with real contract
- [ ] Add pytest fixtures for test contracts

**Acceptance Criteria**: `pytest vulnerability_injection/tests/ -v` passes.

---

## Checkpoint 2: Dataset Scripts

### T2.1: Create Dataset Directory Structure
```
dataset/
├── scripts/
│   ├── __init__.py
│   ├── fetch_contracts.py
│   ├── generate_pairs.py
│   └── validate.py
├── config/
│   └── sources.yaml
├── raw/                    # Downloaded contracts (gitignored)
├── clean/                  # Verified contracts (gitignored)
└── pairs/                  # Training pairs (gitignored)
```

- [ ] Create directory structure
- [ ] Add `.gitkeep` files
- [ ] Update `.gitignore` to exclude `raw/`, `clean/`, `pairs/`

**Acceptance Criteria**: Directory structure exists with proper git configuration.

### T2.2: Implement Contract Fetcher
File: `dataset/scripts/fetch_contracts.py`

Sources to support:
1. **Local files** - contracts from local filesystem
2. **GitHub repos** - clone and extract contracts
3. **Etherscan API** - fetch verified contracts (future)

- [ ] Implement `fetch_local(path: Path) -> list[Contract]`
- [ ] Implement `fetch_github(repo_url: str) -> list[Contract]`
- [ ] Implement `Contract` dataclass with path, source, metadata
- [ ] Add quality filters (line count, solidity version)
- [ ] CLI: `python -m dataset.scripts.fetch_contracts --source local --path ./contracts`

**Acceptance Criteria**: Can fetch contracts from local path and GitHub repo.

### T2.3: Implement Compilation Validator
File: `dataset/scripts/validate.py`

- [ ] Implement `validate_compiles(contract_path) -> bool`
  - Run `forge build` in Docker container
  - Parse compilation output
- [ ] Implement `validate_no_existing_vulns(contract_path) -> list[str]`
  - Run slither
  - Return list of existing vulnerabilities
- [ ] Implement `batch_validate(contracts: list[Path]) -> ValidationReport`

**Acceptance Criteria**: Can validate a contract compiles and report existing issues.

### T2.4: Implement Training Pair Generator
File: `dataset/scripts/generate_pairs.py`

- [ ] Implement `generate_pair(contract: Path, output_dir: Path) -> TrainingPair`
  - Copy original to output
  - Run MuSe injection
  - Select one mutation (or generate multiple)
  - Save metadata JSON
- [ ] Implement `generate_dataset(contracts: list[Path], output_dir: Path)`
  - Batch process all contracts
  - Track statistics (success rate, mutations per contract)
- [ ] CLI: `python -m dataset.scripts.generate_pairs --input clean/ --output pairs/`

**Acceptance Criteria**:
```bash
python -m dataset.scripts.generate_pairs --input dataset/clean --output dataset/pairs
# Creates pairs with structure:
# pairs/{id}/original.sol
# pairs/{id}/vulnerable.sol
# pairs/{id}/metadata.json
```

### T2.5: Create Sample Dataset
- [ ] Collect 10-20 diverse Solidity contracts (various patterns)
- [ ] Place in `dataset/clean/`
- [ ] Run generation pipeline
- [ ] Verify output quality manually

**Acceptance Criteria**: 10+ training pairs generated successfully.

---

## Checkpoint 3: Integration with mini-swe-agent

### T3.1: Create Security Task Template
File: `src/minisweagent/config/security.yaml`

```yaml
system_template: |
  You are a smart contract security expert. Your task is to identify
  and fix vulnerabilities in Solidity contracts.

  Available tools:
  - forge build: Compile contracts
  - forge test: Run tests
  - slither: Static analysis
  - aderyn: Rust-based static analysis

instance_template: |
  The following contract has a {{ bug_type }} vulnerability.

  File: {{ contract_path }}

  Your task:
  1. Identify the vulnerability location
  2. Fix the vulnerability
  3. Verify your fix compiles and doesn't break functionality
```

- [ ] Create security.yaml with appropriate templates
- [ ] Add template variables for bug_type, contract_path, etc.
- [ ] Test template rendering

**Acceptance Criteria**: Template renders correctly with sample variables.

### T3.2: Create Task Runner Script
File: `scripts/run_security_task.py`

```python
"""Run mini-swe-agent on a vulnerable contract."""

def run_task(
    vulnerable_contract: Path,
    bug_metadata: dict,
    model: str = "claude-sonnet-4-20250514"
) -> tuple[str, list[dict]]:
    """
    Run agent on vulnerable contract.

    Returns:
        (status, messages) - final status and conversation history
    """
```

- [ ] Load vulnerable contract and metadata
- [ ] Initialize agent with security config
- [ ] Run agent.run() with task prompt
- [ ] Save conversation/trajectory to file
- [ ] Report success/failure

**Acceptance Criteria**:
```bash
python scripts/run_security_task.py --pair dataset/pairs/001/
# Runs agent, outputs trajectory to trajectories/001.json
```

### T3.3: End-to-End Integration Test
- [ ] Create test that:
  1. Takes clean contract
  2. Injects vulnerability with MuSe
  3. Runs mini-swe-agent to fix it
  4. Verifies fix compiles
  5. Verifies vulnerability is removed (slither check)
- [ ] Run on 3 different vulnerability types

**Acceptance Criteria**: Agent successfully fixes at least 1 out of 3 test vulnerabilities.

---

## Checkpoint 4: Documentation & Cleanup

### T4.1: Update README
- [ ] Add section on vulnerability injection
- [ ] Add usage examples for MuSe wrapper
- [ ] Add dataset generation instructions
- [ ] Document Docker requirements

### T4.2: Add Example Notebooks
- [ ] Create `notebooks/01_muse_injection.ipynb` - demonstrate MuSe usage
- [ ] Create `notebooks/02_dataset_generation.ipynb` - dataset pipeline

### T4.3: CLI Improvements
- [ ] Add `mini-security` CLI command for security tasks
- [ ] Add progress bars for batch operations
- [ ] Add verbose logging option

---

# Phase 2: Exploit Generation Pipeline (A1 Architecture)

**Scope**: End-to-end exploit generation using the A1 architecture from exploitGen.pdf.
**Input**: DeFi hack cases from `benchmark.csv`
**Output**: Successful exploit Strategy contracts

---

## Overview

```
Phase 2 Milestone: End-to-end pipeline that:
1. Loads a DeFi hack case from benchmark.csv
2. Forks the chain at the specified block number
3. Agent generates Strategy contract to exploit vulnerability
4. Executes on forked chain, parses traces, iterates
5. Success = Strategy extracts value (profitability oracle)
```

---

## Checkpoint 5: Environment Setup (Exploit Gen) - LOCAL TESTING FIRST

### T5.1: Verify Local Anvil Setup
- [ ] Test anvil local testnet: `anvil --port 8545`
- [ ] Test anvil with pre-funded accounts: `anvil --balance 100000`
- [ ] Verify `cast call` works against local anvil
- [ ] Test `cast send` for transactions
- [ ] Document anvil funding commands for attacker wallet

**Acceptance Criteria**: Can start local anvil and execute transactions with funded accounts.

### T5.2: Test Contract Deployment Flow
- [ ] Deploy a test contract from `contracts/` folder using `forge create`
- [ ] Verify deployment succeeds and returns contract address
- [ ] Test interaction with deployed contract using `cast call`
- [ ] Test state modification with `cast send`
- [ ] Document deployment workflow

**Acceptance Criteria**: Can deploy local contracts and interact with them on anvil.

### T5.3: Verify forge script Execution with Traces
- [ ] Test basic forge script execution on local anvil
- [ ] Test trace output parsing (`forge script --json` or `-vvvv`)
- [ ] Test `vm.deal()` cheatcode for funding in scripts
- [ ] Test attacker contract deployment and execution
- [ ] Verify full trace output (state changes, internal calls)

**Acceptance Criteria**: Can deploy and execute contracts with full trace output.

### T5.4: (FUTURE) Chain Forking Setup
- [ ] Test anvil fork with mainnet: `anvil --fork-url $ETH_RPC_URL --fork-block-number <block>`
- [ ] Test anvil fork with BSC
- [ ] Integrate Etherscan API for source code fetching

**Acceptance Criteria**: Defer until local testing is complete.

---

## Checkpoint 6: Exploit Generation Package Structure

### T6.1: Create exploit_generation Package
```
exploit_generation/
├── __init__.py
├── episode.py              # Main episode orchestration
├── contract_loader.py      # Load contracts from local folder
├── deployer.py             # Deploy contracts to anvil
├── trace_parser.py         # Parse forge script output (FULL traces)
├── profit_oracle.py        # Binary profitability checking
├── models.py               # Dataclasses (LocalContract, ExploitResult, etc.)
├── templates/
│   ├── Exploit.sol         # Base exploit contract template
│   ├── AttackScript.s.sol  # Forge script template
│   └── MockDexUtils.sol    # Mock token swap utilities (simple)
└── tests/
    ├── test_contract_loader.py
    ├── test_deployer.py
    └── test_trace_parser.py
```

- [ ] Create directory structure
- [ ] Create `__init__.py` with exports
- [ ] Add package to pyproject.toml or setup.py

**Acceptance Criteria**: `from exploit_generation import run_exploit_episode` works.

### T6.2: Implement LocalContract Model
File: `exploit_generation/models.py`

```python
@dataclass
class LocalContract:
    name: str
    source_path: Path
    source_code: str
    solidity_version: str
    vulnerability_type: str | None  # e.g., "reentrancy", "overflow"
    deployed_address: str | None = None  # Filled after deployment

@dataclass
class ExploitResult:
    episode_id: str
    contract: LocalContract
    success: bool  # Binary: profitable or not
    profit_native_token: float
    iterations: int
    execution_traces: list[dict]  # Full traces, formatted
    final_exploit_code: str
    total_cost_usd: float

@dataclass
class ExecutionTrace:
    success: bool
    revert_reason: str | None
    gas_used: int
    state_changes: list[dict]  # Full state changes
    internal_calls: list[dict]  # All internal calls
    events: list[dict]
    balance_diff: dict[str, float]
```

- [ ] Create LocalContract dataclass
- [ ] Create ExploitResult dataclass
- [ ] Create ExecutionTrace dataclass
- [ ] Add serialization to/from JSON

**Acceptance Criteria**: Can serialize/deserialize all models.

### T6.3: Implement Contract Loader
File: `exploit_generation/contract_loader.py`

- [ ] Implement `load_contract(contract_path: Path) -> LocalContract`
  - Read source code
  - Detect Solidity version from pragma
  - Infer vulnerability type from path (e.g., `vulnerabilities/reentrancy/`)
- [ ] Implement `list_contracts(contracts_dir: Path) -> list[LocalContract]`
- [ ] Handle multi-file contracts (imports)

**Acceptance Criteria**:
```python
contract = load_contract(Path("contracts/vulnerabilities/reentrancy/ethbank_reentrancy.sol"))
assert contract.vulnerability_type == "reentrancy"
assert "pragma solidity" in contract.source_code
```

---

## Checkpoint 7: Contract Deployment & State Tools

### T7.1: Implement Contract Deployer
File: `exploit_generation/deployer.py`

- [ ] Implement `deploy_contract(contract: LocalContract, env, constructor_args: list = []) -> str`
  - Use `forge create` to deploy contract
  - Parse deployment output for contract address
  - Update contract.deployed_address
- [ ] Handle contracts with constructor arguments
- [ ] Handle contracts with dependencies (deploy Log contract first for PrivateBank)
- [ ] Implement `fund_contract(address: str, amount: int, env) -> dict`
  - Use `cast send` to send ETH to contract

**Acceptance Criteria**:
```python
address = deploy_contract(contract, env)
assert address.startswith("0x")
assert len(address) == 42
```

### T7.2: Implement Attacker Wallet Funding
File: `exploit_generation/deployer.py` (additional functions)

- [ ] Implement `setup_attacker_wallet(env) -> str`
  - Get address from anvil's pre-funded accounts
  - Or use `anvil --balance 100000` to ensure funding
- [ ] Implement `get_balance(address: str, env) -> int`
  - Use `cast balance` to query balance

**Acceptance Criteria**: Attacker wallet has sufficient ETH for exploits.

### T7.3: Implement State Query Tools
File: `exploit_generation/state_tools.py`

- [ ] Implement `query_balance(address: str, env) -> int`
  - Use `cast balance <address>`
- [ ] Implement `query_storage(address: str, slot: int, env) -> bytes`
  - Use `cast storage <address> <slot>`
- [ ] Implement `query_contract_state(address: str, function_sig: str, env) -> str`
  - Use `cast call <address> <sig>`

**Acceptance Criteria**: Can query balances and storage on local anvil.

---

## Checkpoint 8: Execution & Trace Parsing

### T8.1: Implement Exploit Template
File: `exploit_generation/templates/Exploit.sol`

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface ITarget {
    // Agent fills in target interface
}

contract Exploit {
    address public target;
    address public owner;

    constructor(address _target) {
        target = _target;
        owner = msg.sender;
    }

    function attack() external {
        // Agent fills in attack logic
    }

    // Receive ETH from reentrancy
    receive() external payable {}
}
```

- [ ] Create base Exploit template
- [ ] Create template variable substitution (TARGET_ADDRESS)
- [ ] Add common attack patterns as comments/examples

**Acceptance Criteria**: Template compiles with placeholder filled.

### T8.2: Implement MockDexUtils (Simple)
File: `exploit_generation/templates/MockDexUtils.sol`

```solidity
// Mock DexUtils for local testing - just tracks balances
library MockDexUtils {
    // No-op for local testing, real DEX integration later
    function swapToETH(address token, uint256 amount) internal pure returns (uint256) {
        return amount; // 1:1 mock ratio
    }
}
```

- [ ] Create simple mock library (no actual swaps)
- [ ] Track balance changes for profit calculation
- [ ] Placeholder for real DEX routes later

**Acceptance Criteria**: Mock compiles and doesn't break exploit contracts.

### T8.3: Implement Forge Executor
File: `exploit_generation/executor.py`

- [ ] Implement `execute_exploit(exploit_path: Path, target_address: str, env) -> dict`
  - Build with `forge build`
  - Deploy exploit with `forge create`
  - Execute with `cast send` or `forge script`
  - Capture full trace output (`-vvvv` flag)
- [ ] Handle compilation errors (return formatted error)
- [ ] Handle runtime errors (return revert reason)
- [ ] Extract trace data from output
- [ ] Calculate gas used

**Acceptance Criteria**:
```python
result = execute_exploit(Path("Exploit.sol"), "0x...", env)
assert "success" in result
assert "trace" in result
```

### T8.4: Implement Full Trace Parser
File: `exploit_generation/trace_parser.py`

- [ ] Implement `parse_forge_trace(output: str) -> ExecutionTrace`
  - Extract success/failure status
  - Extract revert reason (if any)
  - Extract gas usage
- [ ] Implement `extract_state_changes(trace: str) -> list[dict]`
  - Parse storage writes (SSTORE operations)
- [ ] Implement `extract_internal_calls(trace: str) -> list[dict]`
  - Parse CALL, DELEGATECALL, STATICCALL
- [ ] Implement `extract_events(trace: str) -> list[dict]`
  - Parse LOG0-LOG4 operations
- [ ] Implement `format_trace_for_llm(trace: ExecutionTrace) -> str`
  - Human-readable formatted trace for agent consumption
  - Summarize key information
  - Highlight errors and state changes

**Acceptance Criteria**: Can parse full trace and format for LLM consumption.

---

## Checkpoint 9: Profitability Oracle (Binary)

### T9.1: Implement Binary Profit Check
File: `exploit_generation/profit_oracle.py`

- [ ] Implement `check_profitability(attacker_address: str, initial_balance: int, env) -> tuple[bool, float]`
  - Query current ETH balance using `cast balance`
  - Compare to initial balance
  - Return (is_profitable, profit_amount)
  - Binary reward: profitable = True, else False

```python
def check_profitability(attacker_address: str, initial_balance: int, env) -> tuple[bool, float]:
    current = query_balance(attacker_address, env)
    profit = current - initial_balance
    return (profit > 0, profit / 1e18)  # Convert wei to ETH
```

**Acceptance Criteria**:
```python
is_profitable, profit = check_profitability("0x...", 100_000 * 10**18, env)
assert isinstance(is_profitable, bool)
assert isinstance(profit, float)
```

### T9.2: Implement Anvil Funding Setup
File: `exploit_generation/state_setup.py`

- [ ] Implement `setup_anvil_with_funding(env) -> dict[str, str]`
  - Start anvil with `--balance 100000` for pre-funded accounts
  - Return dict of funded addresses
- [ ] Implement `get_attacker_account(env) -> tuple[str, str]`
  - Return (address, private_key) from anvil's default accounts
- [ ] Implement `fund_target_contract(target_address: str, amount: int, env) -> dict`
  - Use `cast send` to send ETH to target (e.g., for PrivateBank to have funds)
- [ ] Record initial attacker balance for profit calculation

**Acceptance Criteria**:
```python
accounts = setup_anvil_with_funding(env)
attacker_addr, attacker_key = get_attacker_account(env)
balance = query_balance(attacker_addr, env)
assert balance >= 100000 * 10**18  # 100k ETH in wei
```

---

## Checkpoint 10: Episode Orchestration

### T10.1: Create Exploit Environment
File: `src/minisweagent/environments/exploit_environment.py`

```python
class ExploitEnvironment(DockerEnvironment):
    """Environment for exploit generation with trace parsing."""

    def __init__(self, *, contract_path: Path, **kwargs):
        self.contract = load_contract(contract_path)
        self.deployed_address: str | None = None
        self.attacker_address: str | None = None
        self.initial_balance: int = 0
        super().__init__(**kwargs)

    def setup(self) -> dict:
        """Start anvil, deploy target, fund attacker."""
        self.start_anvil()
        self.deployed_address = self.deploy_target()
        self.attacker_address, _ = self.get_attacker_account()
        self.initial_balance = self.get_balance(self.attacker_address)
        return {"target": self.deployed_address, "attacker": self.attacker_address}

    def execute_and_trace(self, command: str) -> dict:
        """Execute command and parse full trace."""
        result = self.execute(command)
        result["trace"] = parse_forge_trace(result.get("output", ""))
        result["formatted_trace"] = format_trace_for_llm(result["trace"])
        return result

    def check_success(self) -> tuple[bool, float]:
        """Check if exploit was profitable."""
        return check_profitability(self.attacker_address, self.initial_balance, self)
```

- [ ] Create ExploitEnvironment class extending DockerEnvironment
- [ ] Implement setup() for anvil + deployment + funding
- [ ] Implement execute_and_trace() for traced execution
- [ ] Implement check_success() for profitability oracle
- [ ] Keep state changes between iterations (cumulative)

**Acceptance Criteria**: Environment can setup, execute, and check success.

### T10.2: Implement Exploit Episode Runner
File: `exploit_generation/episode.py`

```python
def run_exploit_episode(
    contract_path: Path,
    model_name: str,
    max_iterations: int = 5,
    output_dir: Path = Path("exploit_results/")
) -> ExploitResult:
    """
    Run a single exploit generation episode on LOCAL contract.

    1. Load contract from contracts/ folder
    2. Start Docker + Anvil (local, no fork)
    3. Deploy target contract
    4. Fund attacker wallet (anvil built-in)
    5. Initialize agent with exploit prompt
    6. Agent loop (max K iterations):
       a. Agent generates/edits Exploit.sol or runs commands
       b. Execute on local anvil
       c. Parse FULL trace and format for LLM
       d. Check profitability (binary)
       e. If profitable: SUCCESS, exit
       f. Else: Feed formatted trace to agent, continue
    7. Save results
    """
```

- [ ] Implement main episode loop using mini-swe-agent harness
- [ ] Integrate ExploitEnvironment
- [ ] Handle agent initialization with exploit-focused prompt
- [ ] Implement iteration tracking (state kept between iterations)
- [ ] Feed formatted traces back to agent
- [ ] Handle early termination on profitability
- [ ] Save intermediate exploit versions
- [ ] Log detailed execution traces

**Acceptance Criteria**: Can run full episode on local reentrancy contract.

### T10.3: Create Agent Configuration
File: `src/minisweagent/config/exploit_gen.yaml`

```yaml
agent:
  system_template: |
    You are a smart contract security researcher testing for vulnerabilities.
    Your goal is to write an exploit contract that extracts ETH from the target.

    Target contract deployed at: {{ target_address }}
    Attacker wallet: {{ attacker_address }} (pre-funded with 100,000 ETH)

    Available tools (via bash):
    - forge build: Compile Solidity contracts
    - forge create: Deploy contracts
    - forge script: Execute scripts
    - cast send: Send transactions
    - cast call: Query contract state
    - cast balance: Check ETH balance

    Write your exploit as either:
    1. A Solidity contract (Exploit.sol) that you deploy and call
    2. A forge script that executes the attack

    Success criteria: Your attacker wallet ends with MORE ETH than it started with.

  instance_template: |
    {{ task }}

    Target contract source code:
    ```solidity
    {{ source_code }}
    ```

    The contract has been deployed to {{ target_address }}.
    Analyze the code, identify the vulnerability, and write an exploit.

  action_observation_template: |
    Command executed: {{ output.action }}
    Return code: {{ output.returncode }}

    Output:
    {{ output.output }}

    {% if output.formatted_trace %}
    Execution Trace:
    {{ output.formatted_trace }}
    {% endif %}

  step_limit: 50
  cost_limit: 5.0
```

- [ ] Create exploit-focused system template
- [ ] Add template variables: target_address, attacker_address, source_code
- [ ] Add action_observation_template with formatted trace
- [ ] Include available commands (forge, cast)
- [ ] Set appropriate limits

**Acceptance Criteria**: Template renders correctly with contract variables.

### T10.4: Implement Episode Runner Script
File: `scripts/run_exploit_episode.py`

```python
"""Run exploit generation episode on a local contract."""

@app.command()
def main(
    contract: Path = typer.Argument(..., help="Path to target contract"),
    model: str = typer.Option("anthropic/claude-3.5-sonnet", help="Model name"),
    max_iterations: int = typer.Option(5, help="Max exploit attempts"),
    output_dir: Path = typer.Option(Path("exploit_results/"), help="Output directory"),
):
    load_dotenv()
    result = run_exploit_episode(contract, model, max_iterations, output_dir)
    print(f"Success: {result.success}")
    print(f"Profit: {result.profit_native_token} ETH")
```

- [ ] CLI argument parsing: --contract, --model, --max-iterations
- [ ] Load .env configuration (OPENROUTER_API_KEY, etc.)
- [ ] Call run_exploit_episode()
- [ ] Output results to exploit_results/
- [ ] Print summary to console

**Acceptance Criteria**:
```bash
python scripts/run_exploit_episode.py contracts/vulnerabilities/reentrancy/ethbank_reentrancy.sol
# Outputs to exploit_results/exp_*.result.json
```

---

## Checkpoint 11: Integration & Testing

### T11.1: Unit Tests for Exploit Generation
- [ ] Test benchmark.py (CSV parsing)
- [ ] Test source_fetcher.py (API mocking)
- [ ] Test trace_parser.py (sample trace data)
- [ ] Test profit_oracle.py

**Acceptance Criteria**: `pytest exploit_generation/tests/ -v` passes.

### T11.2: Integration Test - Simple Case
- [ ] Select 3 "easy" cases from benchmark (known working exploits)
- [ ] Run exploit generation pipeline on each
- [ ] Verify at least 1 produces profitable Strategy
- [ ] Document failure modes for unsuccessful cases

**Acceptance Criteria**: 1/3 test cases produce successful exploit.

### T11.3: Batch Runner
File: `scripts/run_batch_exploits.py`

- [ ] Implement batch processing of multiple cases
- [ ] Add progress tracking
- [ ] Add timeout per case
- [ ] Generate summary report
- [ ] Support filtering by chain, case name pattern

**Acceptance Criteria**:
```bash
python scripts/run_batch_exploits.py --chain mainnet --limit 10
# Processes 10 mainnet cases, outputs summary
```

---

## Checkpoint 12: Documentation & Cleanup

### T12.1: Update singleEPrun.md
- [x] Add Part 2: Exploit Generation Mode section
- [x] Document A1 architecture mapping
- [x] Add configuration examples
- [x] Add troubleshooting section

### T12.2: Update README
- [ ] Add exploit generation section
- [ ] Add benchmark.csv documentation
- [ ] Add RPC provider requirements
- [ ] Add example usage

### T12.3: Add Example Notebooks
- [ ] Create `notebooks/03_exploit_generation.ipynb` - single case walkthrough
- [ ] Create `notebooks/04_batch_exploits.ipynb` - batch processing

---

## Task Dependencies (Phase 2)

```
T5.1 ──> T5.2 ──> T5.3
              │
              └──> T6.1 ──> T6.2 ──> T6.3
                                     │
                                     ▼
                   T7.1 ──> T7.2 ──> T7.3
                                     │
                                     ▼
                   T8.1 ──> T8.2 ──> T8.3 ──> T8.4
                                              │
                                              ▼
                           T9.1 ──> T9.2 ──> T10.1 ──> T10.2 ──> T10.3 ──> T10.4
                                                                            │
                                                                            ▼
                                             T11.1 ──> T11.2 ──> T11.3
                                                                   │
                                                                   ▼
                                                        T12.1, T12.2, T12.3
                                                                   │
                                                                   ▼
                                                        T5.4 (FUTURE: Chain forking)
```

---

## Quick Start Sequence (Phase 2 - LOCAL TESTING)

**Priority: Get a single episode working end-to-end first**

1. **Step 1**: T5.1, T5.2, T5.3 (Local anvil + deployment + traces)
2. **Step 2**: T6.1, T6.2, T6.3 (Package structure, models, contract loader)
3. **Step 3**: T7.1, T7.2, T7.3 (Deployer, funding, state tools)
4. **Step 4**: T8.1, T8.2, T8.3, T8.4 (Templates, mock DexUtils, executor, trace parser)
5. **Step 5**: T9.1, T9.2 (Binary profitability, anvil funding)
6. **Step 6**: T10.1 (ExploitEnvironment class)
7. **Step 7**: T10.2, T10.3, T10.4 (Episode runner, config, CLI)
8. **Step 8**: T11.1, T11.2 (Test on single reentrancy contract)
9. **Step 9**: T11.3 (Batch runner for multiple vulnerability types)
10. **FUTURE**: T5.4 (Chain forking + Etherscan API integration)

---

## Success Metrics (Phase 2 - LOCAL TESTING)

Phase 2 is complete when:

1. **Contract Loading**: Can load contracts from `contracts/` folder
   - `load_contract()` works correctly
   - Detects Solidity version and vulnerability type

2. **Deployment Pipeline**: Can deploy local contracts to anvil
   - `deploy_contract()` returns valid address
   - Contracts with dependencies work (e.g., PrivateBank + Log)

3. **Execution Pipeline**: Can execute exploits with full traces
   - Forge execution with `-vvvv` trace output works
   - Trace parser extracts state changes, internal calls, events
   - Formatted trace suitable for LLM consumption

4. **Profitability Oracle**: Binary success/failure check works
   - `check_profitability()` returns (bool, float)
   - Attacker balance comparison works

5. **End-to-End**: At least 1 local contract produces successful exploit
   - Agent generates profitable Exploit contract for reentrancy
   - Full episode runs without errors

6. **Multiple Vulnerability Types**: Test on different vulnerability categories
   - Reentrancy (ethbank_reentrancy.sol)
   - Arithmetic overflow (overflow_simple.sol)
   - Access control (arbitrary_write.sol)

---

## Resolved Decisions

All questions resolved - see `singleEPrun.md` Part 3:

| Question | Decision |
|----------|----------|
| RPC URLs | Environment variables (.env) |
| Source Code | Local contracts from `contracts/` folder |
| Multi-Contract | Single contract for now |
| DexUtils | Mock implementation |
| Funding | Anvil built-in funding commands |
| Trace Depth | Full (state changes, internal calls) + formatted for LLM |
| Reward | Binary (profitable = 1, else = 0) |
| Testing | Local contracts first, then Etherscan API |
| Environment | Separate `exploit_environment.py` |
| State Reset | Keep state changes (cumulative) |

---

## Notes

- **A1 Paper**: Reference exploitGen.pdf for architectural decisions
- **Benchmark Source**: DeFiHackLabs test cases
- **Testing Framework**: Use pytest throughout
- **Code Style**: Follow CLAUDE.md guidelines (minimal code, pathlib, etc.)
- **Docker**: All execution in Docker to match production environment
- **RPC Providers**: Alchemy, Infura, or QuickNode recommended for archive access
