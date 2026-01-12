# Complete Episode Workflow Explained

## Table of Contents
1. [What is an Episode?](#what-is-an-episode)
2. [The Complete Pipeline](#the-complete-pipeline)
3. [Component Deep Dive](#component-deep-dive)
4. [Data Flow & Structures](#data-flow--structures)
5. [Reward System](#reward-system)
6. [Example Walkthrough](#example-walkthrough)
7. [RL Training Context](#rl-training-context)

---

## What is an Episode?

An **episode** is a single complete cycle of:
1. Creating a vulnerable contract
2. Having an AI agent attempt to fix it
3. Evaluating how well it did

Think of it like a training exercise:
- **Input**: A clean smart contract
- **Process**: Inject vulnerability → AI fixes it → Evaluate
- **Output**: Score (reward) indicating success

In Reinforcement Learning (RL) terminology:
- **State**: The vulnerable contract code
- **Action**: The agent's bash commands to fix it
- **Reward**: How well the fix worked (+1.0 for success, penalties for failures)

---

## The Complete Pipeline

### Overview Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                     EPISODE PIPELINE FLOW                           │
└────────────────────────────────────────────────────────────────────┘

INPUT: Clean Contract (SimpleBank.sol)
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Setup Foundry Project                                   │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  /tmp/rl_episode_xyz/                                           │
│  ├── src/SimpleBank.sol         (clean contract)                │
│  └── foundry.toml                (compiler config)              │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Inject Vulnerability (MuSe)                             │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  MuSe Operator: RE (Reentrancy)                                │
│                                                                  │
│  ORIGINAL CODE:                                                 │
│    balances[msg.sender] -= amount;                              │
│    (bool ok, ) = msg.sender.call{value: amount}("");            │
│                                                                  │
│  MUTATED CODE:                                                  │
│    (bool ok, ) = msg.sender.call{value: amount}("");            │
│    balances[msg.sender] -= amount;  ← STATE CHANGE AFTER CALL! │
│                                                                  │
│  Output: MuseMutation object with metadata                      │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼ Copy mutated contract → src/SimpleBank.sol (replaces clean)
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Start Docker Container (FoundryEnvironment)             │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  docker run -d --entrypoint /bin/bash \                         │
│    -v /tmp/rl_episode_xyz:/workspace \                          │
│    yudai-complete:latest \                                      │
│    -c "sleep 4h"                                                │
│                                                                  │
│  Container has:                                                 │
│  • forge, cast, anvil (Foundry tools)                           │
│  • slither (security analyzer)                                  │
│  • aderyn (security analyzer)                                   │
│  • solc 0.8.24                                                  │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Baseline Security Analysis                              │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  Run on VULNERABLE contract (before agent fixes it)             │
│                                                                  │
│  Slither:                                                       │
│    . /opt/venv-main/bin/activate                                │
│    slither /workspace/src/ --json -                             │
│                                                                  │
│  Aderyn:                                                        │
│    aderyn /workspace --output /tmp/aderyn.json                  │
│                                                                  │
│  Result: baseline_findings = [Finding(...), Finding(...)]       │
│          (Typically 0-2 findings on clean contract)             │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: Agent Execution (The AI Fix Attempt)                    │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  Model: OpenRouter (anthropic/claude-3.5-sonnet)                │
│  Agent: DefaultAgent (mini-swe-agent)                           │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ AGENT LOOP (up to 50 steps or $3 cost limit)            │   │
│  │                                                          │   │
│  │  1. System Prompt:                                      │   │
│  │     "You are a smart contract security expert..."       │   │
│  │                                                          │   │
│  │  2. Task Prompt:                                        │   │
│  │     "Fix the Reentrancy vulnerability at lines 20-22"   │   │
│  │                                                          │   │
│  │  3. Agent thinks → generates bash command:              │   │
│  │     ```bash                                             │   │
│  │     cat src/SimpleBank.sol                              │   │
│  │     ```                                                 │   │
│  │                                                          │   │
│  │  4. Execute in Docker → return output                   │   │
│  │                                                          │   │
│  │  5. Agent sees output → generates next command:         │   │
│  │     ```bash                                             │   │
│  │     sed -i 's/old_line/new_line/' src/SimpleBank.sol    │   │
│  │     ```                                                 │   │
│  │                                                          │   │
│  │  6. Repeat until:                                       │   │
│  │     • Agent says: COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT │   │
│  │     • Step limit reached (50)                           │   │
│  │     • Cost limit reached ($3)                           │   │
│  │     • Error occurs                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Output: Modified contract + trajectory (all messages/actions)  │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: Final Security Analysis                                 │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  Run on AGENT'S FIXED contract                                  │
│                                                                  │
│  Same tools (Slither + Aderyn)                                  │
│  Result: final_findings = [Finding(...), ...]                   │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 7: Compilation Check                                       │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  forge build                                                    │
│                                                                  │
│  If fails → total_reward = -1.0 (regardless of other factors)   │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 8: Reward Computation                                      │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │
│  compare_findings(baseline, final, target_operator="RE")        │
│                                                                  │
│  1. Did target vulnerability get fixed?                         │
│     baseline has "reentrancy" → final doesn't → +1.0            │
│                                                                  │
│  2. Were new vulnerabilities introduced?                        │
│     final has 3 new issues → -0.5 × 3 = -1.5                    │
│                                                                  │
│  3. Total reward: 1.0 - 1.5 = -0.5                              │
│                                                                  │
│  4. Special case: Compilation failed?                           │
│     Override → total_reward = -1.0                              │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
OUTPUT: EpisodeResult
  ├── episode_id: "ep_35037"
  ├── mutation: MuseMutation(operator="RE", ...)
  ├── baseline_findings: [...]
  ├── final_findings: [...]
  ├── reward: RewardSignal(total=0.5, fixed=true, ...)
  ├── compilation_passed: true
  └── agent_trajectory: {messages: [...], cost: 0.42, calls: 12}
```

---

## Component Deep Dive

### 1. MuSe (Mutation Seeding)

**What it does**: Injects realistic vulnerabilities into smart contracts.

**How it works**:
```python
# vulnerability_injection/muse_wrapper.py

injector = MuseInjector(operators=["RE"])  # Only reentrancy

# Under the hood:
# 1. Copies contract to MuSe/contracts/SimpleBank.sol
# 2. Runs: npx sumo disable    (disable all operators)
# 3. Runs: npx sumo enable RE  (enable only reentrancy)
# 4. Runs: npx sumo mutate     (generate mutants)
# 5. Reads: MuSe/sumo/results/mutations.json
# 6. Returns: list[MuseMutation]
```

**Output structure**:
```python
MuseMutation(
    id="m7cd291c3",
    operator="RE",
    file="/path/to/SimpleBank.sol",
    start_line=20,
    end_line=22,
    original="balances[msg.sender] -= amount;\n\n(bool ok, ) = ...",
    replacement="(bool ok, ) = ...\nbalances[msg.sender] -= amount;",
    mutant_path="/tmp/rl_episode_xyz/mutants/SimpleBank.sol-m7cd291c3.sol"
)
```

**Why this design**: MuSe uses AST-level mutations, so it produces syntactically valid but vulnerable code. This is better than random fuzzing.

---

### 2. FoundryEnvironment (Docker Container)

**What it does**: Provides isolated environment with all tools needed for smart contract development and security analysis.

**How it works**:
```python
# src/minisweagent/environments/foundry.py

env = FoundryEnvironment(
    project_path="/tmp/rl_episode_xyz",  # Host path
    image="yudai-complete:latest"
)

# This creates:
docker run -d \
  --entrypoint /bin/bash \
  -v /tmp/rl_episode_xyz:/workspace \
  yudai-complete:latest \
  -c "sleep 4h"

# The container stays alive for 4 hours, allowing multiple commands
```

**Execute commands**:
```python
result = env.execute("forge build")
# Returns: {"output": "...", "returncode": 0}

result = env.execute("cat src/SimpleBank.sol")
# Returns: {"output": "contract SimpleBank {...}", "returncode": 0}
```

**Why Docker**: Isolation, reproducibility, pre-installed tools, prevents host contamination.

---

### 3. Security Analysis Tools

**Slither** - Static analysis tool from Trail of Bits
```bash
# Inside container:
. /opt/venv-main/bin/activate
slither /workspace/src/ --json - 2>/dev/null
```

Output (parsed to Finding objects):
```json
{
  "tool": "slither",
  "detector": "reentrancy-eth",
  "severity": "High",
  "description": "Reentrancy in withdraw()...",
  "locations": [{"file": "src/SimpleBank.sol", "start_line": 16, ...}]
}
```

**Aderyn** - Modern Rust-based analyzer from Cyfrin
```bash
aderyn /workspace --output /tmp/aderyn.json
```

**Detection mapping**:
```python
# Each vulnerability operator maps to detector patterns:
OPERATOR_INFO = {
    "RE": {"detection_tools": ["slither", "mythril", "aderyn"]},
    "TX": {"detection_tools": ["slither", "aderyn"]},
    ...
}

# Finding.matches_vulnerability("RE") checks:
# - Slither detectors: "reentrancy-eth", "reentrancy-no-eth", "reentrancy-events"
# - Aderyn detectors: "reentrancy", "reentrancy-benign"
```

---

### 4. DefaultAgent (mini-swe-agent)

**What it does**: Autonomous LLM agent that reads, thinks, and executes bash commands to fix the vulnerability.

**Agent loop** (`src/minisweagent/agents/default.py`):
```python
while not done and step < step_limit:
    # 1. Query LLM with full conversation history
    response = model.query(messages)

    # 2. Parse bash command from response
    actions = parse_action(response, action_regex)
    # Regex: ```(?:bash|sh)\s*\n(.*?)\n```

    # 3. Execute command in Docker
    output = env.execute(actions[0])

    # 4. Add observation to message history
    messages.append({
        "role": "user",
        "content": format_observation(output)
    })

    # 5. Check if done
    if "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" in output:
        done = True
```

**Message flow**:
```
Turn 1:
  User → Agent: "Fix the reentrancy at line 20"
  Agent → Env: `cat src/SimpleBank.sol`
  Env → Agent: [file contents]

Turn 2:
  Agent → Env: `sed -i '20,22s/old/new/' src/SimpleBank.sol`
  Env → Agent: returncode=0

Turn 3:
  Agent → Env: `forge build`
  Env → Agent: "Compiled successfully"

Turn 4:
  Agent → Env: `echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`
  DONE
```

**Why this works**: The LLM has full context from all previous turns, so it can reason about what commands to run next based on previous outputs.

---

## Data Flow & Structures

### Key Data Structures

#### 1. MuseMutation
```python
@dataclass
class MuseMutation:
    id: str               # "m7cd291c3"
    operator: str         # "RE" (reentrancy)
    file: str             # Path to original file
    start_line: int       # 20
    end_line: int         # 22
    original: str         # Original code
    replacement: str      # Mutated code
    mutant_path: str      # Path to .sol-m7cd291c3.sol file
```

#### 2. Finding
```python
@dataclass
class Finding:
    tool: str             # "slither" or "aderyn"
    detector: str         # "reentrancy-eth"
    severity: str         # "High", "Medium", "Low"
    confidence: str       # "High", "Medium", "Low"
    description: str      # Human-readable description
    locations: list[BugLocation]  # Where the issue is

    def matches_vulnerability(self, operator: str) -> bool:
        """Check if this finding matches the target vulnerability type."""
        # E.g., operator="RE" matches detector in ["reentrancy-eth", ...]
```

#### 3. RewardSignal
```python
@dataclass
class RewardSignal:
    vulnerability_fixed: bool      # True if target vuln was fixed
    new_vulns_introduced: int      # Count of new issues
    compilation_passed: bool       # Does it compile?
    total_reward: float            # Final score
    details: dict                  # Extra debug info
```

#### 4. EpisodeResult
```python
@dataclass
class EpisodeResult:
    episode_id: str                    # "ep_35037"
    mutation: MuseMutation             # What vulnerability was injected
    baseline_findings: list[Finding]   # Issues before agent fix
    final_findings: list[Finding]      # Issues after agent fix
    reward: RewardSignal               # How well did agent do
    compilation_passed: bool           # Final compilation status
    agent_trajectory: dict             # Full conversation history
```

### Data Flow Through System

```
Clean Contract (Path)
  ↓
MuseInjector.inject()
  ↓
list[MuseMutation] → Pick one random mutation
  ↓
Copy mutated contract to project
  ↓
FoundryEnvironment.execute("slither ...") → baseline_findings
  ↓
DefaultAgent.run(task_prompt)
  ├─ Loop: query → parse → execute → observe
  └─ Returns: exit_status, result
  ↓
FoundryEnvironment.execute("slither ...") → final_findings
  ↓
compare_findings(baseline, final, operator)
  ↓
RewardSignal
  ↓
EpisodeResult → Saved to rl_results/ep_*.result.json
```

---

## Reward System

### Reward Formula

```python
reward = 0.0

# Primary goal: Fix the target vulnerability
if vulnerability_fixed:
    reward += 1.0

# Penalty: Don't introduce new vulnerabilities
reward -= 0.5 * new_vulns_introduced

# Critical failure: Must compile
if not compilation_passed:
    reward = -1.0  # Override everything
```

### Examples

#### Example 1: Perfect Fix
```
Baseline: [reentrancy-eth]
Final:    []
Compilation: ✓

reward = 1.0 (fixed) + 0 (no new issues) = +1.0 ✓
```

#### Example 2: Fixed but Introduced Issues
```
Baseline: [reentrancy-eth]
Final:    [unchecked-call, missing-zero-check]
Compilation: ✓

reward = 1.0 (fixed) - 0.5×2 (new issues) = 0.0
```

#### Example 3: Broke the Contract
```
Baseline: [reentrancy-eth]
Final:    []
Compilation: ✗ (syntax error)

reward = -1.0 (compilation failure overrides everything)
```

#### Example 4: Didn't Fix It
```
Baseline: [reentrancy-eth]
Final:    [reentrancy-eth]  ← Still there!
Compilation: ✓

reward = 0 (not fixed) - 0 (no new) = 0.0
```

### Why This Reward Design?

1. **Primary objective is clear**: Fix the vulnerability (+1.0)
2. **Encourages safety**: New bugs are bad (-0.5 each)
3. **Hard constraint**: Must compile (-1.0 penalty)
4. **Simple to interpret**: Score maps to success

This is compatible with RL algorithms like PPO (Proximal Policy Optimization) or GRPO (Group Relative Policy Optimization).

---

## Example Walkthrough

Let's trace an actual episode with **SimpleBank.sol** and **RE** (Reentrancy) operator.

### Initial State

**Clean contract** (`contracts/SimpleBank.sol`):
```solidity
function withdraw(uint256 amount) external {
    require(amount > 0, "amount=0");
    require(balances[msg.sender] >= amount, "insufficient");

    balances[msg.sender] -= amount;  // ← State update BEFORE call

    (bool ok, ) = msg.sender.call{value: amount}("");
    require(ok, "transfer failed");
}
```

### Step 1-2: Setup + Inject Vulnerability

```bash
# Temp workspace created: /tmp/rl_episode_xyz/
# MuSe runs: npx sumo mutate with operator=RE
```

**Mutated contract** (lines 20-22 swapped):
```solidity
function withdraw(uint256 amount) external {
    require(amount > 0, "amount=0");
    require(balances[msg.sender] >= amount, "insufficient");

    (bool ok, ) = msg.sender.call{value: amount}("");  // ← Call BEFORE state update!
    balances[msg.sender] -= amount;                    // ← Vulnerable to reentrancy

    require(ok, "transfer failed");
}
```

### Step 3-4: Docker + Baseline Analysis

```bash
# Container started: minisweagent-9e179614

# Slither output:
{
  "detector": "reentrancy-eth",
  "severity": "High",
  "description": "Reentrancy in withdraw()...",
  "elements": [...]
}

# baseline_findings = [Finding(detector="reentrancy-eth", ...)]
# ✓ Slither correctly detected the vulnerability!
```

### Step 5: Agent Execution

**Turn 1**:
```
Agent: Let me examine the contract
```bash
cat src/SimpleBank.sol
```

Output: [shows vulnerable contract]
```

**Turn 2**:
```
Agent: I see the reentrancy issue. The external call happens before state update.
```bash
python3 -c "
import re
code = open('src/SimpleBank.sol').read()
# Swap lines 20-21 back
fixed = code.replace(
    '(bool ok, ) = msg.sender.call{value: amount}(\"\");\n        balances[msg.sender] -= amount;',
    'balances[msg.sender] -= amount;\n\n        (bool ok, ) = msg.sender.call{value: amount}(\"\");'
)
open('src/SimpleBank.sol', 'w').write(fixed)
"
```

Output: returncode=0
```

**Turn 3**:
```
Agent: Let me verify it compiles
```bash
forge build
```

Output: "Compiled 1 Solidity file successfully"
```

**Turn 4**:
```
Agent: Task complete!
```bash
echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT
```

DONE (exit_status="Submitted")
```

### Step 6-8: Final Analysis + Reward

```bash
# Slither on fixed contract:
{
  "detector": "reentrancy-events",  # ← Only minor issue (event after call)
  "severity": "Low",
  ...
}

# final_findings = [Finding(detector="reentrancy-events", severity="Low")]
# Note: "reentrancy-eth" is gone! The high-severity issue was fixed.

# Compilation check:
forge build → returncode=0 ✓

# Reward computation:
vulnerability_fixed = True  (reentrancy-eth not in final)
new_vulns_introduced = 1    (reentrancy-events is new, but low severity)
total_reward = 1.0 - 0.5×1 = +0.5

# Final result:
EpisodeResult(
    episode_id="ep_35037",
    reward=RewardSignal(
        vulnerability_fixed=True,
        total_reward=0.5,
        compilation_passed=True
    )
)
```

**Saved to**: `rl_results/ep_35037.result.json`

---

## RL Training Context

### Current State: Single Episodes

Right now, we run **one episode at a time**:
```bash
python scripts/run_minimal_episode.py
# → 1 episode → 1 result file
```

This is useful for:
- Testing the pipeline
- Debugging agent behavior
- Collecting initial data

### Future: Batch Collection for RL Training

To train an RL model, you need **many episodes** (100s to 1000s):

```python
# Pseudo-code for batch collection
results = []
for contract in dataset:
    for operator in ["RE", "TX", "UC", "TD", ...]:
        for episode in range(5):  # 5 attempts per contract-operator pair
            result = run_episode(contract, operators=[operator])
            results.append(result)

# Now you have ~1000 episodes with trajectories and rewards
```

### Training Loop (Future)

```python
# Pseudo-code for RL training

# 1. Collect trajectories
trajectories = [load_trajectory(f) for f in glob("rl_results/*.traj.json")]

# 2. Label with rewards
for traj, result in zip(trajectories, results):
    traj.reward = result.reward.total_reward

# 3. Train policy (e.g., PPO)
policy = PolicyModel()  # Could be fine-tuned LLM
for epoch in range(10):
    for batch in batches(trajectories):
        loss = compute_ppo_loss(policy, batch)
        optimizer.step(loss)

# 4. New policy is better at fixing vulnerabilities!
```

### Why This Works

The **reward signal** directly measures what we care about:
- Did the agent fix the vulnerability? (+1.0)
- Did it break things? (-0.5 per new issue, -1.0 for compilation failure)

Over many episodes, the RL algorithm learns:
- Which commands are effective (e.g., `sed -i` for simple fixes)
- Which patterns to look for (e.g., external call before state update)
- How to use tools (e.g., `slither` to verify fixes)

### Data Requirements

For effective training:
- **Diversity**: Many different contracts and vulnerability types
- **Volume**: 500-1000+ episodes per vulnerability type
- **Quality**: Accurate reward labels (requires good detection tools)

---

## Summary

**What is an episode?**
One complete cycle: Clean contract → Inject bug → AI fixes → Evaluate → Score

**Key components:**
1. **MuSe**: Injects realistic vulnerabilities
2. **Docker**: Isolated environment with tools
3. **Agent**: LLM that autonomously executes bash commands
4. **Security tools**: Slither + Aderyn detect issues
5. **Reward**: +1.0 for fix, -0.5 per new bug, -1.0 for compilation failure

**Data flow:**
Contract → Mutate → Analyze (baseline) → Agent fixes → Analyze (final) → Compare → Reward

**Current use**: Single-episode testing and data collection

**Future use**: Batch collection → RL training → Better policies for vulnerability fixing

**Why this matters:**
This pipeline generates training data for teaching AI models to autonomously fix smart contract vulnerabilities—a critical need in blockchain security.
