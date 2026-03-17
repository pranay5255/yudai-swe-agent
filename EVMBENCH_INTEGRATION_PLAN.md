# EVMbench Integration Plan

## Current Status
- ✅ 405 DeFiHackLabs exploit cases (mainnet/BSC/base)
- ✅ V3 exploit harness with Docker + Anvil + Foundry
- ✅ Rich UI and parsed feedback (BlockchainCommandParserV2)
- ❌ EVMbench dataset not yet imported
- ❌ DETECT mode not implemented
- ❌ PATCH mode not implemented

## Phase 1: Import EVMbench EXPLOIT Cases (Quick Win)

### 1.1 Download EVMbench Dataset
```bash
cd /home/pranay5255/Documents
git clone https://github.com/openai/frontier-evals
cd frontier-evals

# Navigate to EVMbench data
cd evals/evmbench/
```

### 1.2 Convert to benchmark.csv Format
Create `scripts/import_evmbench.py`:
- Parse EVMbench task files
- Extract: case_name, fork_block, target_address, chain
- Add task_source="code4rena"
- Append to benchmark.csv

Expected: +24 EXPLOIT cases (EVMbench has 24 exploit-ready cases)

### 1.3 Test Integration
```bash
# Run a Code4rena case
uv run python scripts/run_benchmark_exploit_v3.py \
  --case "2024-08-phi_H-06" \
  --model claude-3-5-sonnet-20241022 \
  -v
```

**Time Estimate:** 2-4 hours
**Value:** 6% increase in exploit benchmark size (405 → 429 cases)

---

## Phase 2: Add DETECT Mode (High Value)

### 2.1 Extend BenchmarkCase Model
File: `exploit_generation/models.py`

Add fields:
- `ground_truth_vulnerabilities: list[dict] | None`
- `hints: dict | None`
- `modes: list[str]` (detect, patch, exploit)

### 2.2 Create DETECT Config
File: `src/minisweagent/config/benchmark_detect.yaml`

Template directs agent to:
- Audit smart contracts
- Identify vulnerabilities
- Write findings to `submission/audit.md`

### 2.3 Implement Model-Based Judge
File: `exploit_generation/detect_judge.py`

Uses LLM (GPT-5 or Claude Opus) to compare:
- Ground truth vulnerability
- Agent audit report
Returns: binary (detected or not)

### 2.4 Add DETECT Mode to Runner
File: `scripts/run_benchmark_exploit_v3.py`

Add `--mode detect` flag:
- Loads benchmark_detect.yaml
- Runs agent in audit mode
- Grades with model-based judge
- Calculates recall metric

**Time Estimate:** 1 week
**Value:** Measure vulnerability discovery capabilities (not just exploitation)

---

## Phase 3: Add PATCH Mode (Medium Value)

### 3.1 Create PATCH Config
File: `src/minisweagent/config/benchmark_patch.yaml`

Template directs agent to:
- Read vulnerable contract
- Run existing test suite
- Fix vulnerability without breaking tests

### 3.2 Implement Test-Driven Grading
- Run `forge test`
- Check: functional tests pass + exploit tests fail
- Binary: patched successfully or not

### 3.3 Add PATCH Mode to Runner
Add `--mode patch` flag

**Time Estimate:** 1 week
**Value:** Measure remediation capabilities

---

## Phase 4: Hints System (Ablation Studies)

### 4.1 Add Hints to Dataset
Extend benchmark.csv or use JSON sidecar:
```json
{
  "hints": {
    "low": "Focus on contract X at address Y",
    "medium": "Look for reentrancy in withdraw function",
    "high": "The _handleTrade function lacks reentrancy guard..."
  }
}
```

### 4.2 Add --hint-level Flag
- Inject hints into instance_template based on level
- Track hint level in results
- Compare success rates: no-hint vs low vs medium vs high

**Time Estimate:** 3-4 days
**Value:** Separate discovery skill from exploitation skill

---

## Phase 5: Ploit/Veto Architecture (Optional)

Replace Python grading with Rust-based ploit:
- Faster execution
- More reliable
- Prevents anvil_* cheatcodes via veto proxy

**Time Estimate:** 2 weeks
**Value:** Production-grade grading infrastructure

---

## Quick Start Commands

### Current System (405 DeFiHackLabs cases)
```bash
# Single case
uv run python scripts/run_benchmark_exploit_v3.py --case bancor -v

# Batch run (5 mainnet cases)
uv run python scripts/run_benchmark_exploit_v3.py --chain mainnet --limit 5 -v
```

### After EVMbench Integration (Phase 1)
```bash
# Run Code4rena case
uv run python scripts/run_benchmark_exploit_v3.py --case "2024-08-phi_H-06" -v

# Filter by source
uv run python scripts/run_benchmark_exploit_v3.py --task-source code4rena --limit 10 -v
```

### After DETECT Mode (Phase 2)
```bash
# Audit mode with medium hints
uv run python scripts/run_benchmark_exploit_v3.py \
  --mode detect \
  --case "2024-08-phi_H-06" \
  --hint-level medium \
  --model claude-opus-4.6 \
  -v
```

### After PATCH Mode (Phase 3)
```bash
# Fix vulnerability
uv run python scripts/run_benchmark_exploit_v3.py \
  --mode patch \
  --case "2024-07-basin_H-01" \
  --model claude-3-5-sonnet-20241022 \
  -v
```

---

## Recommended Priority

**P0 (Do First):**
1. ✅ Fix OpenRouter API key issue
2. Import EVMbench EXPLOIT cases (Phase 1) - Quick win, 6% more data
3. Add DETECT mode (Phase 2) - High research value

**P1 (Do Next):**
4. Add hints system (Phase 4) - Enables ablation studies
5. Add PATCH mode (Phase 3) - Complete the lifecycle

**P2 (Nice to Have):**
6. Ploit/Veto architecture (Phase 5) - Production hardening

---

## References
- Study Guide: `/home/pranay5255/Documents/yudai-swe-agent/evmbench_study_guide.html`
- EVMbench Paper: `/home/pranay5255/Documents/yudai-swe-agent/evmbench.pdf`
- Benchmark CSV: `/home/pranay5255/Documents/yudai-swe-agent/benchmark.csv`
- Runner Script: `/home/pranay5255/Documents/yudai-swe-agent/scripts/run_benchmark_exploit_v3.py`
