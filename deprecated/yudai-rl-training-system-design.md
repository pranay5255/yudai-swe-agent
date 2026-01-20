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

## 3. MuSe Python Wrapper (IMPLEMENTED)

The MuSe Python wrapper is implemented at `vulnerability_injection/muse_wrapper.py`:

```python
# vulnerability_injection/muse_wrapper.py

"""Python wrapper for MuSe vulnerability injection tool."""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from vulnerability_injection.models import (
    MuseMutation,
    VULNERABILITY_OPERATORS,
)

MUSE_DIR = Path(__file__).parent.parent / "MuSe"


class MuseInjector:
    """
    Python wrapper for MuSe vulnerability injection.

    MuSe is a Node.js-based mutation tool that injects vulnerabilities
    into Solidity smart contracts. This wrapper provides a Python API
    to invoke MuSe and parse its output.

    Example:
        >>> injector = MuseInjector()
        >>> mutations = injector.inject(Path("contract.sol"), Path("output/"))
        >>> for m in mutations:
        ...     print(f"{m.operator}: {m.original} -> {m.replacement}")
    """

    def __init__(
        self,
        operators: list[str] | None = None,
        muse_dir: Path | None = None,
        vulnerability_only: bool = True,
    ):
        """
        Initialize the MuSe injector.

        Args:
            operators: List of operator IDs to enable. If None, uses all
                      vulnerability operators (RE, TX, UC, etc.)
            muse_dir: Path to MuSe installation. Defaults to ./MuSe/
            vulnerability_only: If True and operators is None, only enable
                              vulnerability-specific operators
        """
        self.muse_dir = muse_dir or MUSE_DIR
        self._verify_muse_installed()

        if operators is None:
            self.operators = VULNERABILITY_OPERATORS if vulnerability_only else None
        else:
            self.operators = operators

    def inject(
        self,
        contract_path: Path,
        output_dir: Path,
        operators: list[str] | None = None,
    ) -> list[MuseMutation]:
        """
        Inject vulnerabilities into a contract.

        Creates a temporary workspace, runs MuSe mutation, and copies
        results to the output directory.

        Args:
            contract_path: Path to the Solidity contract
            output_dir: Directory to save mutated contracts
            operators: Override operators for this injection only

        Returns:
            List of generated mutations with metadata
        """
        # ... (full implementation in source)

    def _setup_workspace(self, contract_path: Path) -> Path:
        """Create a temporary workspace with the contract and symlinked node_modules."""
        # Creates minimal project structure
        # Symlinks node_modules to avoid reinstalling
        # Copies sumo-config.js from MuSe dir
        # ...
```

### Data Models (`vulnerability_injection/models.py`)

```python
@dataclass
class BugLocation:
    """Precise location of an injected bug in source code."""
    file: str
    start_line: int
    end_line: int
    start_char: int
    end_char: int

@dataclass
class MuseMutation:
    """A single mutation generated by MuSe."""
    id: str
    operator: str
    file: str
    start_line: int
    end_line: int
    start_char: int
    end_char: int
    original: str
    replacement: str
    status: Optional[str] = None
    testing_time: Optional[float] = None
    mutant_path: Optional[str] = None

    @classmethod
    def from_muse_json(cls, data: dict) -> "MuseMutation":
        """Create a MuseMutation from MuSe JSON output."""
        # ...

# Map MuSe operator IDs to human-readable names and metadata
OPERATOR_INFO = {
    "RE": {"name": "Reentrancy", "severity": "critical", ...},
    "TX": {"name": "tx.origin Authentication", "severity": "high", ...},
    # ... 11 operators total
}

VULNERABILITY_OPERATORS = list(OPERATOR_INFO.keys())
```

---

## 4. Security Tools & Reward Verification (IMPLEMENTED)

The security analysis and reward computation is implemented in `vulnerability_injection/security_tools.py`:

### 4.1 Security Finding Data Structures

```python
# vulnerability_injection/security_tools.py

@dataclass
class Finding:
    """A security finding from a static analysis tool."""
    tool: str              # "slither" or "aderyn"
    detector: str          # e.g., "reentrancy-eth", "tx-origin"
    severity: str          # "High", "Medium", "Low", "Informational"
    confidence: str        # "High", "Medium", "Low"
    description: str
    locations: list[BugLocation]

    def matches_vulnerability(self, operator: str) -> bool:
        """Check if this finding matches a MuSe vulnerability operator."""
        operator_to_detectors = {
            "RE": ["reentrancy-eth", "reentrancy-no-eth", "reentrancy-benign", "reentrancy"],
            "TX": ["tx-origin", "tx-origin-auth"],
            "TD": ["timestamp", "block-timestamp", "weak-randomness"],
            "UC": ["unchecked-lowlevel", "low-level-calls"],
            "US": ["unchecked-send"],
            "UTR": ["unchecked-transfer"],
            "IUO": ["integer-overflow", "integer-underflow", "divide-before-multiply"],
            "USD": ["suicidal", "unprotected-selfdestruct", "unprotected-suicide"],
            "DTU": ["controlled-delegatecall", "delegatecall-loop"],
            "UR1": ["unused-return"],
            "UR2": ["unused-return"],
        }
        matching_detectors = operator_to_detectors.get(operator, [])
        return any(d in self.detector.lower() for d in matching_detectors)


@dataclass
class RewardSignal:
    """Reward signal computed from security analysis comparison."""
    vulnerability_fixed: bool
    new_vulns_introduced: int
    compilation_passed: bool
    total_reward: float
    details: dict
```

### 4.2 Slither Integration

```python
def parse_slither_json(json_output: str) -> list[Finding]:
    """Parse Slither JSON output into Finding objects."""
    data = json.loads(json_output)
    findings = []
    detectors = data.get("results", {}).get("detectors", [])

    for detector in detectors:
        locations = []
        for element in detector.get("elements", []):
            source = element.get("source_mapping", {})
            lines = source.get("lines", [])
            if lines:
                locations.append(BugLocation(
                    file=source.get("filename_relative", ""),
                    start_line=min(lines),
                    end_line=max(lines),
                    start_char=source.get("start", 0),
                    end_char=source.get("start", 0) + source.get("length", 0),
                ))
        findings.append(Finding(
            tool="slither",
            detector=detector.get("check", "unknown"),
            severity=detector.get("impact", "Unknown"),
            confidence=detector.get("confidence", "Unknown"),
            description=detector.get("description", ""),
            locations=locations,
        ))
    return findings


def run_slither(contract_path: str, env, extra_args: str = "") -> tuple[list[Finding], str]:
    """Run Slither on a contract using the FoundryEnvironment."""
    cmd = f". /opt/venv-main/bin/activate && slither {contract_path} --json - {extra_args} 2>/dev/null"
    result = env.execute(cmd)
    output = result.get("output", "")
    # Extract and parse JSON from output
    # ...
    return parse_slither_json(json_str), output
```

### 4.3 Aderyn Integration

```python
def parse_aderyn_json(json_output: str) -> list[Finding]:
    """Parse Aderyn JSON output into Finding objects."""
    data = json.loads(json_output)
    findings = []

    severity_map = {
        "high_issues": "High",
        "medium_issues": "Medium",
        "low_issues": "Low",
        "nc_issues": "Informational",
    }

    for issue_key, severity in severity_map.items():
        issues = data.get(issue_key, {}).get("issues", [])
        for issue in issues:
            # Parse locations and create Finding objects
            # ...
    return findings


def run_aderyn(contract_path: str, env, output_file: str = "/tmp/aderyn_report.json") -> tuple[list[Finding], str]:
    """Run Aderyn on a contract using the FoundryEnvironment."""
    cmd = f"cd {contract_path} && aderyn . --output {output_file} 2>&1; cat {output_file}"
    result = env.execute(cmd)
    # ...
```

### 4.4 Reward Computation

```python
def compare_findings(
    baseline: list[Finding],
    final: list[Finding],
    target_operator: str,
) -> RewardSignal:
    """Compare baseline and final findings to compute reward.

    Args:
        baseline: Findings from the mutated (vulnerable) contract
        final: Findings from the agent's fixed contract
        target_operator: The MuSe operator that was used to inject vulnerability

    Returns:
        RewardSignal with computed reward
    """
    # Check if the target vulnerability was fixed
    baseline_matches = [f for f in baseline if f.matches_vulnerability(target_operator)]
    final_matches = [f for f in final if f.matches_vulnerability(target_operator)]

    vulnerability_fixed = len(baseline_matches) > 0 and len(final_matches) == 0

    # Count new vulnerabilities (excluding the target type)
    baseline_other = {(f.detector, f.severity) for f in baseline if not f.matches_vulnerability(target_operator)}
    final_other = {(f.detector, f.severity) for f in final if not f.matches_vulnerability(target_operator)}
    new_vulns = final_other - baseline_other

    # Compute reward
    reward = 0.0
    if vulnerability_fixed:
        reward += 1.0
    reward -= 0.5 * len(new_vulns)  # Penalty for new vulnerabilities

    return RewardSignal(
        vulnerability_fixed=vulnerability_fixed,
        new_vulns_introduced=len(new_vulns),
        compilation_passed=True,  # Updated by caller
        total_reward=reward,
        details={
            "baseline_target_findings": len(baseline_matches),
            "final_target_findings": len(final_matches),
            "new_vulnerabilities": list(new_vulns),
        },
    )
```

### 4.5 Reward Structure

| Condition | Reward |
|-----------|--------|
| Target vulnerability fixed | +1.0 |
| Each new vulnerability introduced | -0.5 |
| Compilation failure | -1.0 (overrides all) |

---

## 5. Episode Runner (IMPLEMENTED)

The RL episode runner is implemented in `vulnerability_injection/episode.py`:

### 5.1 Episode Structure

```python
# vulnerability_injection/episode.py

@dataclass
class EpisodeResult:
    """Result of a single RL episode."""
    mutation: MuseMutation
    baseline_findings: list[Finding]
    final_findings: list[Finding]
    reward: RewardSignal
    agent_trajectory: dict
    compilation_passed: bool
    episode_id: str

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict for logging."""
        # ...
```

### 5.2 Episode Runner Function

```python
def run_episode(
    clean_contract: Path,
    output_dir: Path,
    model_name: str,
    operators: list[str] | None = None,
    yolo: bool = True,
    cost_limit: float = 3.0,
    docker_image: str = "yudai-complete:latest",
) -> EpisodeResult:
    """Run a single RL episode.

    Full pipeline:
    1. Set up Foundry project structure
    2. Inject vulnerability using MuSe
    3. Initialize Docker environment
    4. Run baseline security analysis (Slither + Aderyn)
    5. Run mini-swe-agent to fix vulnerability
    6. Run final security analysis
    7. Compute reward by comparing findings
    """
    episode_id = f"ep_{random.randint(10000, 99999)}"
    workspace = Path(tempfile.mkdtemp(prefix="rl_episode_"))

    try:
        # Step 1: Set up Foundry project
        project = setup_foundry_project(clean_contract, workspace)

        # Step 2: Inject vulnerability using MuSe
        injector = MuseInjector(operators=operators)
        mutations = injector.inject(clean_contract, workspace / "mutants")
        mutation = random.choice(mutations)

        # Copy mutated contract to project
        shutil.copy(mutation.mutant_path, project / "src" / clean_contract.name)

        # Step 3: Initialize FoundryEnvironment
        env = FoundryEnvironment(project_path=str(project), image=docker_image)

        # Step 4: Run baseline security analysis
        baseline_findings = run_security_analysis("/workspace", env)

        # Step 5: Run agent
        config = yaml.safe_load((builtin_config_dir / "foundry.yaml").read_text())
        if yolo:
            config.setdefault("agent", {})["mode"] = "yolo"
        config.setdefault("agent", {})["cost_limit"] = cost_limit

        model = get_model(model_name, config.get("model", {}))
        agent = DefaultAgent(model, env, **config.get("agent", {}))

        task = generate_task_prompt(mutation)
        exit_status, result = agent.run(task)

        # Save trajectory
        save_traj(agent, output_dir / f"{episode_id}.traj.json", ...)

        # Step 6: Run final security analysis
        final_findings = run_security_analysis("/workspace", env)

        # Step 7: Compute reward
        reward = compare_findings(baseline_findings, final_findings, mutation.operator)

        # Check compilation
        compile_result = env.execute("forge build")
        compilation_passed = compile_result.get("returncode", 1) == 0
        if not compilation_passed:
            reward.total_reward = -1.0

        return EpisodeResult(...)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
```

### 5.3 Task Prompt Generation

```python
def generate_task_prompt(mutation: MuseMutation) -> str:
    """Generate the task prompt for the agent."""
    info = OPERATOR_INFO.get(mutation.operator, {})
    vuln_name = info.get("name", mutation.operator)
    severity = info.get("severity", "unknown")
    description = info.get("description", "")

    return f"""The Solidity contract in src/ has a **{vuln_name}** vulnerability.
Your goal is to identify and fix the vulnerability while maintaining the contract's functionality.

## Vulnerability Details
- **Type**: {vuln_name}
- **Severity**: {severity}
- **Description**: {description}
- **Hint**: The vulnerability is around lines {mutation.start_line}-{mutation.end_line}

## Steps
1. Examine the contract: `cat src/*.sol`
2. Run security analysis: `. /opt/venv-main/bin/activate && slither src/ --print human-summary`
3. Fix the vulnerability by editing the contract
4. Verify it compiles: `forge build`
5. Re-run security analysis to confirm the fix
6. Submit when done: `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`

Focus on fixing ONLY the {vuln_name} vulnerability. Do not refactor unrelated code.
"""
```

### 5.4 CLI Entry Point (`mini-security-fix`)

```python
# src/minisweagent/run/security_fix.py

@app.command()
def main(
    contract: Path,           # Path to the Solidity contract to test
    output: Path = "./rl_results",
    model: str = None,        # e.g., "claude-sonnet-4-20250514"
    operators: str = None,    # Comma-separated MuSe operators (e.g., "RE,TX,UC")
    yolo: bool = True,
    cost_limit: float = 3.0,
    docker_image: str = "yudai-complete:latest",
):
    """Run a vulnerability fix episode.

    Example:
        mini-security-fix ./contracts/SimpleBank.sol -m claude-sonnet-4-20250514

    This will:
    1. Inject a random vulnerability into the contract
    2. Run mini-swe-agent to fix it
    3. Evaluate and report results
    """
    result = run_episode(
        clean_contract=contract,
        output_dir=output,
        model_name=model,
        operators=ops,
        yolo=yolo,
        cost_limit=cost_limit,
        docker_image=docker_image,
    )

    # Display rich tables with results...
```

**Usage:**
```bash
# Install
pip install -e '.[full]'

# Run single episode
mini-security-fix ./contracts/SimpleBank.sol -m claude-sonnet-4-20250514

# Run with specific vulnerability types
mini-security-fix ./contracts/SimpleBank.sol --operators RE,TX,UC
```

### 5.5 FoundryEnvironment

The `FoundryEnvironment` class provides Docker-based execution with Foundry + security tools:

```python
# src/minisweagent/environments/foundry.py

class FoundryEnvironment(DockerEnvironment):
    """Docker environment specialized for Foundry smart contract development.

    Extends DockerEnvironment with:
    - Volume mounting for host Foundry projects
    - Pre-configured environment variables for web3 development
    - Longer timeouts suitable for contract compilation
    - Foundry-specific template variables
    """

    def __init__(
        self,
        *,
        image: str = "yudai/foundry-full:latest",
        project_path: str = "",       # Host path to mount
        mount_target: str = "/workspace",
        timeout: int = 120,
        **kwargs,
    ):
        # Build Docker run_args with volume mount
        run_args = ["--rm"]
        if project_path:
            project_path = Path(project_path).resolve()
            run_args.extend(["-v", f"{project_path}:{mount_target}"])

        super().__init__(
            image=image,
            cwd=mount_target,
            timeout=timeout,
            run_args=run_args,
            forward_env=["ETH_RPC_URL", "ETHERSCAN_API_KEY", ...],
            **kwargs,
        )

    def execute(self, command: str) -> dict:
        """Execute command in Docker container."""
        # Returns {"output": str, "returncode": int}
```

**Docker Image Requirements:**
The `yudai-complete:latest` image includes:
- **Foundry**: forge, cast, anvil, chisel
- **Slither**: `/opt/venv-main/bin/slither`
- **Aderyn**: `aderyn` binary
- **Solidity**: solc 0.8.24+

---

## 6. Directory Structure (CURRENT)

```
yudai-swe-agent/
├── contracts/
│   └── SimpleBank.sol               # Minimal demo contract
├── src/
│   └── minisweagent/
│       ├── __init__.py               # Protocols: Model, Environment, Agent
│       ├── agents/
│       │   └── default.py            # Core ~100-line agent loop
│       ├── environments/
│       │   ├── docker.py             # Base Docker environment
│       │   └── foundry.py            # FoundryEnvironment for smart contracts
│       ├── models/                   # LM interfaces (litellm, anthropic)
│       ├── config/
│       │   ├── default.yaml
│       │   ├── foundry.yaml          # Foundry agent config with security tools
│       │   ├── security.yaml
│       │   └── security_fix_minimal.yaml # Minimal prompts for single-episode runs
│       └── run/
│           ├── mini.py               # Main CLI entry point
│           └── security_fix.py       # RL episode CLI (mini-security-fix)
│
├── vulnerability_injection/           # IMPLEMENTED
│   ├── __init__.py                   # Package exports
│   ├── models.py                     # MuseMutation, BugLocation, OPERATOR_INFO
│   ├── muse_wrapper.py               # Python wrapper for MuSe
│   ├── security_tools.py             # Slither/Aderyn wrappers, reward computation
│   ├── episode.py                    # RL episode runner
│   ├── config/                        # TODO: operator config mappings
│   └── tests/                         # TODO: unit tests for wrapper/tools
│
├── MuSe/                             # Node.js mutation tool
│   ├── index.js                      # CLI entry point (yargs-based)
│   ├── package.json
│   ├── sumo-config.js
│   ├── node_modules/                 # npm dependencies
│   └── src/
│       ├── mutation.js
│       ├── mutationRunner.js
│       └── operators/MuSe/           # 11 vulnerability operators
│           ├── reentrancy.js
│           ├── tx-origin.js
│           └── ...
│
├── dataset/                           # TO BE IMPLEMENTED
│   ├── scripts/
│   │   ├── fetch_etherscan.py
│   │   └── generate_pairs.py
│   ├── raw/
│   ├── clean/
│   └── pairs/
│
├── docker/
│   └── (build scripts for yudai-complete image)
├── scripts/
│   └── run_minimal_episode.py        # Minimal single-episode runner
│
├── tests/
│   └── ...
│
├── pyproject.toml                    # Includes mini-security-fix entry point
└── yudai-rl-training-system-design.md
```

---

## 7. Pipeline Specification (IMPLEMENTED)

### 7.1 High-Level Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              RL VULNERABILITY FIX PIPELINE                               │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                    STEP 1                          STEP 2                    STEP 3
              ┌───────────────┐              ┌───────────────┐         ┌───────────────┐
              │ CLEAN         │              │ MUTATED       │         │ FINAL         │
              │ CONTRACT      │─────────────▶│ CONTRACT      │────────▶│ CONTRACT      │
              │ (original.sol)│   MuSe       │ (vulnerable)  │  Agent  │ (fixed?)      │
              └───────────────┘  Injection   └───────────────┘   Fix   └───────────────┘
                                     │                │                       │
                                     ▼                ▼                       ▼
                              ┌─────────────┐  ┌─────────────┐         ┌─────────────┐
                              │ MUTATION    │  │ BASELINE    │         │ FINAL       │
                              │ METADATA    │  │ FINDINGS    │         │ FINDINGS    │
                              │ (operator,  │  │ (Slither +  │         │ (Slither +  │
                              │  location)  │  │  Aderyn)    │         │  Aderyn)    │
                              └─────────────┘  └─────────────┘         └─────────────┘
                                                     │                       │
                                                     └───────────┬───────────┘
                                                                 ▼
                                                          ┌─────────────┐
                                                          │   REWARD    │
                                                          │   SIGNAL    │
                                                          │  (compare)  │
                                                          └─────────────┘
```

### 7.2 Step-by-Step Pipeline

#### STEP 1: Security Analysis on Clean Contract (Pre-Mutation)
**Input:** `clean_contract.sol`
**Output:** `baseline_clean_findings.json` (optional, for reference)

```python
# Optional: Run on clean contract to establish baseline
# Currently not stored, but could be used for dataset validation
```

#### STEP 2: Vulnerability Injection
**Input:** `clean_contract.sol`
**Output:**
- `mutated_contract.sol` (vulnerable version)
- `mutation_metadata.json` (operator, location, original/replacement code)

```python
injector = MuseInjector(operators=["RE", "TX", "UC"])
mutations = injector.inject(clean_contract, output_dir)
# Select one mutation for the episode
mutation = random.choice(mutations)
```

#### STEP 3: Baseline Security Analysis (On Mutated Contract)
**Input:** `mutated_contract.sol` in Foundry project
**Output:** `baseline_findings.json`

```python
# Run both Slither and Aderyn
baseline_findings = []
slither_findings, _ = run_slither("/workspace/src/", env)
baseline_findings.extend(slither_findings)
aderyn_findings, _ = run_aderyn("/workspace", env)
baseline_findings.extend(aderyn_findings)
```

**Slither Command:**
```bash
. /opt/venv-main/bin/activate && slither /workspace/src/ --json - 2>/dev/null
```

**Aderyn Command:**
```bash
cd /workspace && aderyn . --output /tmp/aderyn_report.json
```

#### STEP 4: Agent Execution (RL Episode)
**Input:**
- Mutated contract in Foundry project
- Task prompt with vulnerability hint
**Output:**
- `modified_contract.sol` (agent's attempted fix)
- `trajectory.json` (agent's action history)

```python
agent = DefaultAgent(model, env, **config)
task = generate_task_prompt(mutation)
exit_status, result = agent.run(task)
save_traj(agent, output_dir / f"{episode_id}.traj.json")
```

#### STEP 5: Final Security Analysis
**Input:** Agent's modified contract
**Output:** `final_findings.json`

```python
final_findings = run_security_analysis("/workspace", env)
```

#### STEP 6: Reward Computation
**Input:**
- `baseline_findings` (from mutated contract)
- `final_findings` (from agent's output)
- `target_operator` (the vulnerability type injected)
**Output:** `RewardSignal`

```python
reward = compare_findings(baseline_findings, final_findings, mutation.operator)

# Check compilation
compile_result = env.execute("forge build")
if compile_result.get("returncode") != 0:
    reward.total_reward = -1.0
```

### 7.3 Output File Structure

Each episode produces the following outputs in `output_dir/`:

```
rl_results/
├── ep_12345.result.json     # Full episode result
│   {
│     "episode_id": "ep_12345",
│     "mutation": {
│       "id": "m46f345c9",
│       "operator": "RE",
│       "file": "Token.sol",
│       "start_line": 45,
│       "end_line": 48,
│       "original": "balances[msg.sender] -= amount;\nmsg.sender.call{...}",
│       "replacement": "msg.sender.call{...};\nbalances[msg.sender] -= amount"
│     },
│     "baseline_findings": [...],
│     "final_findings": [...],
│     "reward": {
│       "vulnerability_fixed": true,
│       "new_vulns_introduced": 0,
│       "compilation_passed": true,
│       "total_reward": 1.0
│     },
│     "agent_trajectory": {
│       "messages": [...],
│       "cost": 0.45,
│       "n_calls": 12
│     }
│   }
│
└── ep_12345.traj.json       # Agent trajectory for RL training
    {
      "messages": [...],
      "exit_status": "Submitted",
      "result": {...}
    }
```

### 7.4 Logged Data Summary

| Step | Data Logged | File |
|------|-------------|------|
| Injection | Mutation operator, location, code diff | `result.json` → `mutation` |
| Baseline Analysis | Slither + Aderyn findings on vulnerable contract | `result.json` → `baseline_findings` |
| Agent Execution | Full message history, cost, API calls | `traj.json`, `result.json` → `agent_trajectory` |
| Final Analysis | Slither + Aderyn findings on modified contract | `result.json` → `final_findings` |
| Reward | Fixed/not fixed, new vulns, compilation, total | `result.json` → `reward` |

### 7.5 Running the Pipeline

```bash
# Single episode
mini-security-fix ./contracts/SimpleBank.sol -m claude-sonnet-4-20250514

# With specific operators
mini-security-fix ./contracts/SimpleBank.sol -m claude-sonnet-4-20250514 --operators RE,TX,UC

# Custom output directory
mini-security-fix ./contracts/SimpleBank.sol -m claude-sonnet-4-20250514 -o ./my_results

# With cost limit
mini-security-fix ./contracts/SimpleBank.sol -m claude-sonnet-4-20250514 --cost-limit 5.0
```

---

### 7.6 Minimal Demo (Single Contract)

This is the smallest runnable end-to-end episode (single contract, single operator).

```bash
# 1) Build the toolchain image
docker build -t yudai-complete -f docker/Dockerfile.yudai.fixed .

# 2) Ensure MuSe dependencies exist (skip if MuSe/node_modules is already present)
cd MuSe && npm install

# 3) Run a single episode (minimal prompts)
python scripts/run_minimal_episode.py -m claude-sonnet-4-20250514 --operators RE

# Alternate: use CLI directly
mini-security-fix ./contracts/SimpleBank.sol -m claude-sonnet-4-20250514 --operators RE --config security_fix_minimal
```

Notes:
- Provide your model/API configuration (e.g., `MSWEA_MODEL_API_KEY`, or `-m <model>`).
- The demo uses `contracts/SimpleBank.sol` as the clean contract input.

---

## 8. Next Steps

### Phase 1: Vulnerability Injection Pipeline ✅ COMPLETE
1. ✅ Create Python wrapper for MuSe (`vulnerability_injection/muse_wrapper.py`)
2. ✅ Build security tools wrappers (`vulnerability_injection/security_tools.py`)
3. ✅ Create episode runner (`vulnerability_injection/episode.py`)
4. ✅ Add CLI entry point (`mini-security-fix`)

### Phase 2: Dataset Creation (IN PROGRESS)
1. Build dataset fetching scripts (Etherscan API)
2. Create training pair generator
3. Validate dataset quality

### Phase 3: RL Training (FUTURE)
- Collect trajectories from multiple episodes
- Implement RL training loop (PPO/GRPO)
- Fine-tune models on successful trajectories

---

## References

1. MuSe Paper: arXiv:2504.15948 - "Automated Vulnerability Injection in Solidity Smart Contracts"
2. SolidiFI: https://github.com/DependableSystemsLab/SolidiFI
3. SolidiFI Paper: https://blogs.ubc.ca/karthik/files/2020/07/issta20.pdf
4. mini-swe-agent: https://github.com/SWE-agent/mini-swe-agent
