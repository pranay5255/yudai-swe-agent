# TASKS.md - Vulnerability Injection & Dataset Creation

This document tracks implementation tasks for Phase 1 of the Yudai RL Training System.

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

## Task Dependencies

```
T0.1 ─┬─> T0.2 ──> T1.1 ──> T1.2 ──> T1.3 ──> T1.5
      │
T0.3 ─┘                              │
                                     v
                              T2.1 ──> T2.2 ──> T2.3 ──> T2.4 ──> T2.5
                                                                    │
                                                                    v
                              T3.1 ──> T3.2 ──> T3.3
                                                  │
                                                  v
                                           T4.1, T4.2, T4.3
```

---

## Quick Start Sequence

For rapid iteration, complete tasks in this order:

1. **Day 1**: T0.1, T0.2, T0.3 (Environment setup)
2. **Day 2-3**: T1.1, T1.2, T1.3 (Core wrapper)
3. **Day 4**: T1.4, T1.5 (Config and tests)
4. **Day 5-6**: T2.1, T2.2, T2.4 (Dataset pipeline)
5. **Day 7**: T3.1, T3.2 (mini-swe-agent integration)
6. **Day 8**: T3.3 (Integration testing)
7. **Day 9-10**: T4.x (Documentation)

---

## Success Metrics

Phase 1 is complete when:

1. **MuSe Wrapper**: Python API to inject vulnerabilities
   - `injector.inject(contract) -> list[Mutation]` works

2. **Dataset Pipeline**: End-to-end dataset generation
   - `generate_pairs.py` produces valid training pairs

3. **Integration**: mini-swe-agent can process pairs
   - Agent receives vulnerable contract
   - Agent attempts to fix it
   - Trajectory is captured for future training

4. **Validation**: Quality checks pass
   - Mutated contracts compile
   - Vulnerabilities are detectable by static analysis
   - Original and vulnerable contracts differ only at injection point

---

## Notes

- **MuSe vs SolidiFI**: Start with MuSe only. Add SolidiFI in Phase 2 if needed.
- **Testing Framework**: Use pytest throughout.
- **Code Style**: Follow CLAUDE.md guidelines (minimal code, pathlib, etc.)
- **Docker**: All verification runs in Docker to match production environment.
