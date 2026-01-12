# Single Episode Run - Setup & Changes Documentation

This document captures all changes made to enable single-episode vulnerability fix runs, and identifies extension points for future development.

---

## Quick Start

```bash
# 1. Setup environment
cp .env.example .env
# Edit .env with your OpenRouter API key and model

# 2. Run an episode
python scripts/run_minimal_episode.py

# 3. Check results
cat rl_results/ep_*.result.json
```

---

## Changes Made

### 1. Environment Configuration

#### `.env.example` (NEW)
```bash
# OpenRouter API Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL_NAME=anthropic/claude-3.5-sonnet
# MSWEA_COST_TRACKING=ignore_errors  # For free/local models
```

**Purpose**: Template for environment variables needed to run episodes.

---

### 2. Episode Runner Script

#### `scripts/run_minimal_episode.py` (UPDATED)

**Changes**:
- Added `python-dotenv` to load `.env` file automatically
- Reads `OPENROUTER_API_KEY` and `OPENROUTER_MODEL_NAME` from environment
- Validates API key presence before running
- Changed default config to `security_fix_openrouter`
- Added `--env-file` argument for custom env file path
- Improved output formatting with episode summary

**Key code sections**:
```python
# Lines 91-112: Environment loading and validation
env_file = args.env_file or (project_root / ".env")
if env_file.exists():
    load_dotenv(env_file)

api_key = os.getenv("OPENROUTER_API_KEY")
model_name = args.model or os.getenv("OPENROUTER_MODEL_NAME")
```

**Extension point**: Add more environment variables or model providers here.

---

### 3. Agent Configuration

#### `src/minisweagent/config/security_fix_openrouter.yaml` (NEW)

**Purpose**: OpenRouter-specific config for security fix episodes.

**Key settings**:
```yaml
agent:
  system_template: |
    You are a smart contract security expert...
  step_limit: 50
  cost_limit: 5.0

model:
  model_class: openrouter
  model_kwargs:
    temperature: 0.0
  cost_tracking: ignore_errors
```

**Extension point**: Modify prompts, step limits, or add new template variables.

---

### 4. MuSe Wrapper Fixes

#### `vulnerability_injection/muse_wrapper.py` (UPDATED)

**Changes**:

1. **Simplified injection workflow** (Lines 92-162):
   - Runs MuSe directly from MuSe directory instead of temp workspace
   - Copies contract to `MuSe/contracts/`, runs mutation, copies results out
   - Cleans up contract after completion

2. **Proper operator filtering** (Lines 123-128):
   ```python
   # Disable ALL operators first, then enable only specified ones
   if ops_to_enable:
       self._run_sumo(["disable"])  # No args = disable all
       self._run_sumo(["enable"] + ops_to_enable)
   ```

3. **Malformed mutation handling** (Lines 248-250):
   ```python
   # Skip mutations missing required fields
   if "operator" not in m:
       continue
   ```

4. **Placeholder test file creation** (Lines 163-164):
   ```python
   (test_dir / "placeholder.js").write_text("// Placeholder test for MuSe\n")
   ```

**Extension points**:
- `inject()` method: Add pre/post-processing hooks
- `_parse_mutations()`: Add mutation filtering logic
- Add new MuSe operators to `VULNERABILITY_OPERATORS` in `models.py`

---

### 5. Docker Environment Fix

#### `src/minisweagent/environments/docker.py` (UPDATED)

**Change**: Fixed container start command to handle Foundry image's shell entrypoint.

**Before** (broken):
```python
cmd = [..., self.config.image, "sleep", self.config.container_timeout]
# Results in: docker run ... image sleep 4h
# But Foundry image has ENTRYPOINT ["/bin/sh", "-c"], so it runs: /bin/sh -c sleep 4h
# Which parses as: /bin/sh -c "sleep" with "4h" as $0
```

**After** (fixed, Lines 56-71):
```python
cmd = [
    self.config.executable, "run", "-d",
    "--name", container_name,
    "-w", self.config.cwd,
    "--entrypoint", "/bin/bash",  # Override entrypoint
    *self.config.run_args,
    self.config.image,
    "-c", f"sleep {self.config.container_timeout}",  # Single string
]
```

**Extension point**: Add custom entrypoints for different base images.

---

### 6. MuSe Directory Setup

#### `MuSe/test/.gitkeep` (NEW)
#### `MuSe/contracts/` (CREATED)
#### `MuSe/build/` (CREATED)

**Purpose**: MuSe requires these directories to exist for mutation to work.

---

### 7. Demo Contract

#### `contracts/SimpleBank.sol` (RESTORED)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract SimpleBank {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        require(msg.value > 0, "amount=0");
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(amount > 0, "amount=0");
        require(balances[msg.sender] >= amount, "insufficient");
        balances[msg.sender] -= amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
    }
}
```

**Extension point**: Add more demo contracts in `contracts/` directory.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     SINGLE EPISODE PIPELINE                              │
└─────────────────────────────────────────────────────────────────────────┘

scripts/run_minimal_episode.py
         │
         ▼
┌─────────────────────┐
│ Load .env config    │ ◄── OPENROUTER_API_KEY, OPENROUTER_MODEL_NAME
└─────────────────────┘
         │
         ▼
vulnerability_injection/episode.py::run_episode()
         │
         ├──► 1. Setup Foundry project (temp workspace)
         │
         ├──► 2. MuSe injection (muse_wrapper.py)
         │         │
         │         ├── Disable all operators
         │         ├── Enable specified operators (e.g., RE)
         │         ├── Run `npx sumo mutate`
         │         └── Parse mutations.json
         │
         ├──► 3. Start Docker container (FoundryEnvironment)
         │         │
         │         └── yudai-complete:latest with /workspace mount
         │
         ├──► 4. Baseline security analysis (Slither + Aderyn)
         │
         ├──► 5. Run agent (DefaultAgent)
         │         │
         │         ├── Load config (security_fix_openrouter.yaml)
         │         ├── Initialize OpenRouterModel
         │         └── Agent loop: query → parse → execute → observe
         │
         ├──► 6. Final security analysis
         │
         └──► 7. Compute reward (security_tools.py::compare_findings)
                   │
                   └── Output: EpisodeResult → rl_results/ep_*.result.json
```

---

## Key Files for Extension

| Purpose | File | Key Functions/Classes |
|---------|------|----------------------|
| Episode orchestration | `vulnerability_injection/episode.py` | `run_episode()`, `generate_task_prompt()` |
| MuSe integration | `vulnerability_injection/muse_wrapper.py` | `MuseInjector.inject()` |
| Security analysis | `vulnerability_injection/security_tools.py` | `run_slither()`, `run_aderyn()`, `compare_findings()` |
| Reward computation | `vulnerability_injection/security_tools.py` | `RewardSignal`, `compare_findings()` |
| Data models | `vulnerability_injection/models.py` | `MuseMutation`, `OPERATOR_INFO` |
| Docker environment | `src/minisweagent/environments/docker.py` | `DockerEnvironment` |
| Foundry environment | `src/minisweagent/environments/foundry.py` | `FoundryEnvironment` |
| OpenRouter model | `src/minisweagent/models/openrouter_model.py` | `OpenRouterModel` |
| Agent loop | `src/minisweagent/agents/default.py` | `DefaultAgent` |
| Agent config | `src/minisweagent/config/security_fix_openrouter.yaml` | Templates, limits |

---

## Extension Ideas

### 1. Add New Vulnerability Operators

Edit `vulnerability_injection/models.py`:
```python
OPERATOR_INFO = {
    # Existing...
    "NEW_OP": {
        "name": "New Vulnerability",
        "severity": "high",
        "description": "Description of the vulnerability",
        "detection_tools": ["slither", "aderyn"],
    },
}
```

### 2. Add Custom Reward Logic

Edit `vulnerability_injection/security_tools.py::compare_findings()`:
```python
def compare_findings(...) -> RewardSignal:
    # Add custom reward bonuses/penalties
    if some_condition:
        reward += 0.5  # Bonus for gas optimization
```

### 3. Add New Security Tools

Edit `vulnerability_injection/security_tools.py`:
```python
def run_mythril(contract_path: str, env) -> tuple[list[Finding], str]:
    cmd = ". /opt/venv-mythril/bin/activate && myth analyze ..."
    # Parse output into Finding objects
```

### 4. Batch Episode Running

Create `scripts/run_batch_episodes.py`:
```python
for contract in contracts_dir.glob("*.sol"):
    for operator in ["RE", "TX", "UC"]:
        result = run_episode(contract, operators=[operator], ...)
        results.append(result)
```

### 5. Custom Agent Prompts

Edit `src/minisweagent/config/security_fix_openrouter.yaml`:
```yaml
agent:
  system_template: |
    You are an expert in {{vulnerability_type}}...

  instance_template: |
    {{task}}

    Additional context: {{custom_context}}
```

---

## Troubleshooting

### MuSe "No valid test directory" error
```bash
mkdir -p MuSe/test MuSe/contracts MuSe/build
echo "// placeholder" > MuSe/test/.gitkeep
```

### Docker container exits immediately
Check if the image has a custom entrypoint. The fix in `docker.py` handles Foundry images.

### "No mutations generated" error
- Ensure MuSe operators are properly enabled/disabled
- Check that the contract has code patterns matching the operator (e.g., RE needs external calls)

### OpenRouter API errors
- Verify `OPENROUTER_API_KEY` is set correctly
- Check model name format: `provider/model-name` (e.g., `anthropic/claude-3.5-sonnet`)

---

## Sample Output

```json
{
  "episode_id": "ep_35037",
  "mutation": {
    "operator": "RE",
    "original": "balances[msg.sender] -= amount;\n\n(bool ok, ) = msg.sender.call{value: amount}(\"\");",
    "replacement": "(bool ok, ) = msg.sender.call{value: amount}(\"\");\nbalances[msg.sender] -= amount;"
  },
  "reward": {
    "vulnerability_fixed": false,
    "new_vulns_introduced": 5,
    "compilation_passed": true,
    "total_reward": -2.50
  }
}
```

---

## References

- MuSe Paper: arXiv:2504.15948
- OpenRouter API: https://openrouter.ai/docs
- mini-swe-agent: https://github.com/SWE-agent/mini-swe-agent
- Slither: https://github.com/crytic/slither
- Aderyn: https://github.com/Cyfrin/aderyn
