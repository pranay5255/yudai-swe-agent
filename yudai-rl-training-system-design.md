# Yudai RL Training System Design
## Self-Play Reinforcement Learning for Smart Contract Vulnerability Detection & Fixing

---

## Executive Summary

This document outlines a system for post-training language models on smart contract security using reinforcement learning with verifiable rewards. The core innovation is using **mutation-based vulnerability injection** to create training data from known-good contracts, enabling a self-play RL loop where the LM learns to both detect and fix vulnerabilities.

**Key Components:**
1. **Vulnerability Injection Pipeline** - MuSe (primary) + SolidiFI (secondary) for automated bug injection
2. **Dataset Creation** - Clean contracts from Etherscan/DeFi protocols mutated into vulnerable versions
3. **Reward Verification** - Docker-based verification using existing yudai-complete tooling
4. **RL Training Loop** - Integration with mini-swe-agent for trajectory collection

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        YUDAI RL TRAINING PIPELINE                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────────────┐    ┌───────────────────────┐
│  SOURCE DATA    │    │   VULNERABILITY         │    │   RL ENVIRONMENT      │
│                 │    │   INJECTION ENGINE      │    │                       │
│  - Etherscan    │───▶│                         │───▶│  State: Vuln Contract │
│    Verified     │    │  ┌─────────┐            │    │  Action: LM Fix       │
│  - DeFi Llama  │    │  │  MuSe   │ Primary    │    │  Reward: Verifiable   │
│  - Immunefi    │    │  └─────────┘            │    │                       │
│    Bug Bounty  │    │  ┌─────────┐            │    │  Docker: yudai-complete│
│                 │    │  │SolidiFI│ Secondary  │    │                       │
└─────────────────┘    │  └─────────┘            │    └───────────────────────┘
                       └─────────────────────────┘              │
                                                                 ▼
                              ┌─────────────────────────────────────────┐
                              │           REWARD VERIFICATION            │
                              │                                         │
                              │  1. Compilation Check (forge build)     │
                              │  2. Static Analysis (slither/aderyn)    │
                              │  3. Test Suite Verification             │
                              │  4. Exploit PoC Execution               │
                              └─────────────────────────────────────────┘
```

---

## 1. Vulnerability Injection Systems

### 1.1 MuSe (Primary System) - Already Integrated

MuSe is a mutation-based vulnerability injection tool built on the SuMo framework. It is already available at `/MuSe/` in this repository.

#### MuSe Architecture
```
MuSe/
├── index.js                    # CLI entry point (yargs-based)
├── src/
│   ├── mutation.js            # Core Mutation class
│   ├── mutationRunner.js       # Main orchestration
│   ├── reporter.js            # JSON/CSV reporting
│   └── operators/
│       ├── mutationGenerator.js
│       └── MuSe/               # 11 vulnerability operators
│           ├── reentrancy.js
│           ├── tx-origin.js
│           ├── unchecked-call.js
│           └── ... (8 more)
└── sumo-config.js             # Configuration
```

#### MuSe Vulnerability Operators (11 Total)

| ID | Vulnerability | Description | Mutation Strategy |
|----|---------------|-------------|-------------------|
| **RE** | Reentrancy | Swaps state update and external call order | `balances[sender] -= amt; call()` → `call(); balances[sender] -= amt` |
| **TX** | tx.origin Auth | Replaces msg.sender with tx.origin | `msg.sender == owner` → `tx.origin == owner` |
| **TD** | Timestamp Dependence | Replaces block properties with block.timestamp | `block.number` → `block.timestamp` |
| **UC** | Unchecked Call | Removes require() from low-level calls | `require(addr.call())` → `addr.call()` |
| **US** | Unchecked Send | Removes return check from .send() | `require(addr.send())` → `addr.send()` |
| **UTR** | Unchecked Transfer | Removes check from token transfers | `require(token.transfer())` → `token.transfer()` |
| **IUO** | Integer Over/Underflow | Removes SafeMath or adds unchecked blocks | `a.add(b)` → `unchecked { a + b }` |
| **USD** | Unprotected Selfdestruct | Changes visibility to public | `function destroy() private` → `function destroy() public` |
| **DTU** | Delegatecall to Untrusted | Replaces delegatecall target with controllable address | Injects `address public delegateAddressDTU` |
| **UR1** | Unused Return (Assignment) | Ignores return value by default init | `x = func()` → `x = 0; func()` |
| **UR2** | Unused Return (Declaration) | Ignores return in variable declaration | Similar to UR1 for declarations |

#### MuSe Usage

```bash
# Enable specific operators
cd MuSe && npx sumo enable RE TX UC IUO TD

# Generate mutants without testing
npx sumo mutate

# Mutants saved to: sumo/results/mutants/
# Report saved to: sumo/results/mutations.json
```

#### MuSe Output Format

```json
{
  "id": "m46f345c9",
  "operator": "RE",
  "file": "contracts/Token.sol",
  "startLine": 45,
  "endLine": 48,
  "original": "balances[msg.sender] -= amount;\nmsg.sender.call{value: amount}(\"\");",
  "replace": "msg.sender.call{value: amount}(\"\");\nbalances[msg.sender] -= amount;"
}
```

### 1.2 SolidiFI (Secondary System) - To Be Integrated

SolidiFI provides complementary injection capabilities using AST-based code snippet injection.

#### SolidiFI Bug Types (7 Categories)

| Bug Type | Injection Method | Example |
|----------|------------------|---------|
| Re-entrancy | Function snippet injection | Adds vulnerable withdraw function |
| Timestamp Dependency | Statement injection | Adds `block.timestamp >= value` checks |
| Unchecked Send | Weakening existing checks | Removes `if(!send()) revert()` |
| Unhandled Exception | Removing error handling | Removes catch blocks |
| TOD (Front-running) | Multi-function snippet | Adds order-dependent logic |
| Integer Overflow | Type transformation | `uint256` → `uint8` |
| tx.origin | Pattern replacement | `msg.sender` → `tx.origin` |

**Note**: SolidiFI targets Solidity 0.5.x and requires updates for 0.8.x+ contracts.

### 1.3 Comparison: MuSe vs SolidiFI

| Aspect | MuSe | SolidiFI |
|--------|------|----------|
| **Approach** | Mutation-based (modify existing code) | Injection-based (add new code) |
| **Solidity Version** | 0.8.x compatible | 0.5.x (needs updating) |
| **Integration** | npm package, CLI | Python, requires AST parser |
| **Output** | JSON + mutant files | Buggy contracts + bug log |
| **Best For** | Realistic bugs in existing logic | Adding new vulnerable functions |
| **Status** | Ready (in /MuSe/) | Needs integration |

### 1.4 Combined Strategy

Use **MuSe as primary** for realistic mutations, **SolidiFI as secondary** for snippet injection:

```python
def inject_vulnerability(contract: Contract, bug_type: str) -> tuple[Contract, BugLog]:
    # Try MuSe first (better for realistic bugs)
    if bug_type in MUSE_OPERATORS:
        return muse_inject(contract, bug_type)

    # Fall back to SolidiFI for snippet injection
    elif bug_type in SOLIDIFI_BUG_TYPES:
        return solidifi_inject(contract, bug_type)

    raise ValueError(f"Unknown bug type: {bug_type}")
```

---

## 2. Dataset Creation Pipeline

### 2.1 Source Contracts

```yaml
# config/dataset_sources.yaml
sources:
  etherscan:
    api_key: "${ETHERSCAN_API_KEY}"
    chains: [ethereum, polygon, arbitrum, optimism]
    filters:
      verified: true
      min_transactions: 100
      has_source: true

  defi_protocols:
    - name: uniswap-v3
      repo: https://github.com/Uniswap/v3-core
    - name: aave-v3
      repo: https://github.com/aave/aave-v3-core
    - name: compound-v2
      repo: https://github.com/compound-finance/compound-protocol

  quality_filters:
    min_lines: 50
    max_lines: 1000
    must_compile: true
    solidity_version: ">=0.8.0"
```

### 2.2 Dataset Generation Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      DATASET GENERATION PIPELINE                         │
└─────────────────────────────────────────────────────────────────────────┘

1. FETCH CLEAN CONTRACTS
   │
   ├── Etherscan API → Verified contracts
   ├── GitHub repos  → DeFi protocols
   └── Quality filters → Compile check, size limits

2. INJECT VULNERABILITIES (MuSe + SolidiFI)
   │
   ├── For each contract:
   │   ├── Select random vulnerability type
   │   ├── Run injection (MuSe primary)
   │   ├── Verify mutation compiles
   │   └── Generate bug metadata
   │
   └── Output: vulnerable_contracts/
       ├── Token-m46f345c9.sol      # Mutated contract
       └── Token-m46f345c9.json     # Bug metadata

3. CREATE TRAINING PAIRS
   │
   ├── (original.sol, vulnerable.sol, bug_metadata.json)
   └── Stored in dataset/pairs/
```

### 2.3 Dataset Schema

```python
@dataclass
class TrainingPair:
    """A single training example."""
    id: str                          # Unique identifier
    original_path: str               # Path to clean contract
    vulnerable_path: str             # Path to mutated contract
    bug_metadata: BugMetadata        # Injection details

@dataclass
class BugMetadata:
    """Metadata about the injected vulnerability."""
    bug_type: str                    # e.g., "reentrancy", "tx-origin"
    operator: str                    # e.g., "RE", "TX"
    injector: str                    # "muse" or "solidifi"
    location: BugLocation            # Line/char positions
    original_code: str               # Original snippet
    vulnerable_code: str             # Mutated snippet
    detection_tools: list[str]       # Tools expected to catch this

@dataclass
class BugLocation:
    """Precise location of the injected bug."""
    file: str
    start_line: int
    end_line: int
    start_char: int
    end_char: int
```

---

## 3. MuSe Python Wrapper

Since MuSe is a Node.js tool, we need a Python wrapper for integration with mini-swe-agent:

```python
# src/vulnerability_injection/muse_wrapper.py

import subprocess
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

MUSE_DIR = Path(__file__).parent.parent.parent / "MuSe"

@dataclass
class MuseMutation:
    id: str
    operator: str
    file: str
    start_line: int
    end_line: int
    original: str
    replacement: str

class MuseInjector:
    """Python wrapper for MuSe vulnerability injection."""

    def __init__(self, operators: list[str] = None):
        self.operators = operators or ["RE", "TX", "UC", "IUO", "TD"]
        self._configure_operators()

    def _configure_operators(self):
        """Enable specified operators in MuSe."""
        # Disable all first
        subprocess.run(
            ["npx", "sumo", "disable", "--all"],
            cwd=MUSE_DIR,
            capture_output=True
        )
        # Enable selected
        subprocess.run(
            ["npx", "sumo", "enable"] + self.operators,
            cwd=MUSE_DIR,
            capture_output=True
        )

    def inject(self, contract_path: Path, output_dir: Path) -> list[MuseMutation]:
        """
        Inject vulnerabilities into a contract.

        Args:
            contract_path: Path to the Solidity contract
            output_dir: Directory to save mutated contracts

        Returns:
            List of generated mutations with metadata
        """
        # Setup workspace
        workspace = self._setup_workspace(contract_path)

        # Run MuSe mutate
        result = subprocess.run(
            ["npx", "sumo", "mutate"],
            cwd=workspace,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"MuSe failed: {result.stderr}")

        # Parse results
        mutations_file = workspace / "sumo" / "results" / "mutations.json"
        mutations = self._parse_mutations(mutations_file)

        # Copy mutants to output
        self._copy_mutants(workspace, output_dir)

        return mutations

    def _setup_workspace(self, contract_path: Path) -> Path:
        """Create temporary workspace with contract."""
        import tempfile
        import shutil

        workspace = Path(tempfile.mkdtemp(prefix="muse_"))
        contracts_dir = workspace / "contracts"
        contracts_dir.mkdir()

        # Copy contract
        shutil.copy(contract_path, contracts_dir / contract_path.name)

        # Copy MuSe config
        config = {
            "buildDir": "build",
            "contractsDir": "contracts",
            "testDir": "test",
            "skipContracts": [],
            "testingFramework": "forge",
            "minimal": False
        }
        (workspace / "sumo-config.js").write_text(
            f"module.exports = {json.dumps(config)};"
        )

        return workspace

    def _parse_mutations(self, mutations_file: Path) -> list[MuseMutation]:
        """Parse MuSe mutations.json output."""
        if not mutations_file.exists():
            return []

        data = json.loads(mutations_file.read_text())
        return [
            MuseMutation(
                id=m["id"],
                operator=m["operator"],
                file=m["file"],
                start_line=m["startLine"],
                end_line=m["endLine"],
                original=m["original"],
                replacement=m["replace"]
            )
            for m in data
        ]

    def _copy_mutants(self, workspace: Path, output_dir: Path):
        """Copy generated mutant files to output directory."""
        import shutil
        mutants_dir = workspace / "sumo" / "results" / "mutants"
        if mutants_dir.exists():
            for mutant in mutants_dir.glob("*.sol"):
                shutil.copy(mutant, output_dir / mutant.name)
```

---

## 4. Reward Verification System

### 4.1 Verifiable Reward Pipeline

```python
# src/minisweagent/rewards/verifiable_reward.py

import subprocess
from dataclasses import dataclass
from typing import Optional, List, Dict

@dataclass
class RewardSignal:
    total: float
    compilation_passed: bool
    vulnerability_fixed: bool
    no_new_vulns: bool
    tests_passed: bool
    exploit_prevented: bool
    details: Dict

class VerifiableRewardComputer:
    def __init__(self, docker_image: str = "yudai-complete"):
        self.docker_image = docker_image

    def compute(
        self,
        original_path: str,
        modified_path: str,
        bug_type: str,
        bug_location: dict
    ) -> RewardSignal:
        reward = 0.0
        details = {}

        # 1. Compilation Check
        compile_ok = self._check_compilation(modified_path)
        if not compile_ok:
            return RewardSignal(
                total=-1.0,
                compilation_passed=False,
                vulnerability_fixed=False,
                no_new_vulns=False,
                tests_passed=False,
                exploit_prevented=False,
                details={"error": "compilation_failed"}
            )

        # 2. Static Analysis Comparison
        orig_vulns = self._run_slither(original_path)
        mod_vulns = self._run_slither(modified_path)

        vuln_fixed = self._check_vuln_fixed(
            orig_vulns, mod_vulns, bug_type, bug_location
        )
        if vuln_fixed:
            reward += 1.0

        # 3. Check for new vulnerabilities
        new_vulns = self._find_new_vulns(orig_vulns, mod_vulns)
        no_new = len(new_vulns) == 0
        reward -= 0.5 * len(new_vulns)

        # 4. Test Suite
        tests_ok = self._run_tests(modified_path)
        if tests_ok:
            reward += 0.5

        # 5. Exploit PoC (if available)
        exploit_prevented = self._verify_exploit_fails(
            modified_path, bug_type
        )
        if exploit_prevented:
            reward += 1.0

        return RewardSignal(
            total=reward,
            compilation_passed=True,
            vulnerability_fixed=vuln_fixed,
            no_new_vulns=no_new,
            tests_passed=tests_ok,
            exploit_prevented=exploit_prevented,
            details=details
        )

    def _check_compilation(self, path: str) -> bool:
        result = subprocess.run(
            ["docker", "exec", "yudai-container",
             "bash", "-lc", f"cd /workspace && forge build"],
            capture_output=True
        )
        return result.returncode == 0

    def _run_slither(self, path: str) -> List[Dict]:
        result = subprocess.run(
            ["docker", "exec", "yudai-container",
             "bash", "-lc",
             f". /opt/venv-main/bin/activate && slither {path} --json -"],
            capture_output=True
        )
        return self._parse_slither_output(result.stdout)

    def _run_tests(self, path: str) -> bool:
        result = subprocess.run(
            ["docker", "exec", "yudai-container",
             "bash", "-lc", "cd /workspace && forge test"],
            capture_output=True
        )
        return result.returncode == 0
```

---

## 5. Integration with mini-swe-agent

### 5.1 Training Loop Structure

```python
# scripts/train_rl.py (future implementation)

def training_loop():
    injector = MuseInjector(operators=["RE", "TX", "UC", "IUO"])
    reward_computer = VerifiableRewardComputer()
    dataset = ContractDataset("config/dataset_sources.yaml")

    for episode in range(num_episodes):
        # 1. Sample contract
        contract = dataset.sample()

        # 2. Inject vulnerability
        mutations = injector.inject(contract.path, output_dir)
        mutation = random.choice(mutations)

        # 3. Create task for agent
        task = f"""
        The following smart contract has a {mutation.operator} vulnerability.
        Identify and fix the vulnerability while maintaining functionality.

        Contract: {mutation.file}
        Vulnerability type: {mutation.operator}
        """

        # 4. Run mini-swe-agent
        status, trajectory = agent.run(task)

        # 5. Compute reward
        reward = reward_computer.compute(
            original_path=mutation.file,
            modified_path=agent.modified_contract,
            bug_type=mutation.operator,
            bug_location={"start": mutation.start_line, "end": mutation.end_line}
        )

        # 6. Store for RL training
        buffer.add(trajectory, reward)
```

---

## 6. Directory Structure

```
yudai-swe-agent/
├── src/
│   └── minisweagent/
│       ├── agents/
│       ├── environments/
│       ├── models/
│       └── config/
├── vulnerability_injection/           # NEW
│   ├── __init__.py
│   ├── muse_wrapper.py               # Python wrapper for MuSe
│   ├── solidifi_adapter.py           # SolidiFI integration (later)
│   ├── injector.py                   # Unified injection interface
│   └── config/
│       └── operators.yaml            # Operator configuration
├── dataset/                           # NEW
│   ├── scripts/
│   │   ├── fetch_etherscan.py        # Contract fetcher
│   │   ├── generate_pairs.py         # Training pair generator
│   │   └── validate_dataset.py       # Dataset quality checks
│   ├── raw/                          # Downloaded contracts
│   │   └── etherscan/
│   ├── clean/                        # Verified clean contracts
│   └── pairs/                        # Training pairs
│       └── {contract_id}/
│           ├── original.sol
│           ├── vulnerable.sol
│           └── metadata.json
├── rewards/                           # NEW
│   ├── __init__.py
│   └── verifiable_reward.py
├── MuSe/                             # Already present
│   ├── index.js
│   └── src/operators/MuSe/
├── docker/
│   └── Dockerfile.yudai.fixed
├── scripts/                           # NEW
│   ├── generate_dataset.py
│   └── validate_injection.py
└── tests/
    └── test_injection.py
```

---

## 7. Next Steps (See TASKS.md)

Phase 1: Vulnerability Injection Pipeline
1. Create Python wrapper for MuSe
2. Build dataset fetching scripts
3. Create training pair generator
4. Validate with mini-swe-agent

Phase 2: RL Training (Future)
- Integrate reward computation
- Build trajectory collection
- Implement RL training loop

---

## References

1. MuSe Paper: arXiv:2504.15948 - "Automated Vulnerability Injection in Solidity Smart Contracts"
2. SolidiFI: https://github.com/DependableSystemsLab/SolidiFI
3. SolidiFI Paper: https://blogs.ubc.ca/karthik/files/2020/07/issta20.pdf
4. mini-swe-agent: https://github.com/SWE-agent/mini-swe-agent
