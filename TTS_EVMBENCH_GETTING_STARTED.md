# TTS on EVMBench: Getting Started Plan

## Goal

Get back on track to improve EVMBench performance with test-time scaling (TTS) methods, using this repo's `mini-swe-agent` fork as the harness and EVMBench as the benchmark of record.

The intended architecture is:

1. Keep EVMBench native.
2. Run Yudai/mini-swe-agent as an EVMBench agent.
3. Add TTS orchestration on top of the Yudai agent path rather than rewriting EVMBench grading.

## Current Repo State

### What the last 50 commits say

The recent history breaks into three phases:

1. 2026-02-15: V3 exploit harness build-out for the older benchmark path.
   - Added `FoundryEnvironmentV3`
   - Added `ExploitFoundryEnvironmentV3`
   - Added `scripts/run_benchmark_exploit_v3.py`
   - Added early failure detection
2. 2026-03-12: EVMBench research pivot and cleanup.
   - Added EVMBench study assets
   - Removed most V2 exploit harness focus
   - Added notes around discovery bottlenecks, static analysis, and hints
3. 2026-03-17 to 2026-03-30: native EVMBench integration plus TTS planning.
   - Added native EVMBench runner
   - Added EVMBench container entrypoint for mini-swe-agent
   - Added EVMBench config
   - Added tests for the root-side EVMBench adapter
   - Added `tts-evmbench-guide.html`

### What is already implemented

- Native EVMBench runner in `src/minisweagent/run/extra/evmbench.py`
- Native EVMBench agent entrypoint in `src/minisweagent/run/extra/evmbench_agent.py`
- EVMBench-specific config in `src/minisweagent/config/extra/evmbench.yaml`
- Legacy exploit harness still present for the older DeFiHackLabs-style benchmark
- Early failure detection logic in `exploit_generation/benchmark_episode.py`

### What was validated

On 2026-04-02, the targeted root-side tests passed:

```bash
uv run pytest tests/run/test_evmbench.py tests/run/test_run_benchmark_exploit_scripts.py -q
```

Result:

- `8 passed`

This confirms the root adapter surface is wired up, but it does not prove the full EVMBench runtime path is aligned end-to-end.

## Important Blocker

The root repo and the embedded EVMBench submodule are currently out of sync.

### Root repo expects

The root runner expects these EVMBench agent IDs:

- `yudai-detect`
- `yudai-patch`
- `yudai-exploit`

This is encoded in `src/minisweagent/run/extra/evmbench.py`.

### Current submodule exposes

The checked-out EVMBench submodule currently exposes older agent IDs:

- `yudai-default`
- `yudai-opus`
- `yudai-haiku`

These are in:

- `evmBench-frontier-evals/project/evmbench/evmbench/agents/yudai/config.yaml`
- `evmBench-frontier-evals/project/evmbench/evmbench/agents/yudai/start.sh`

### Submodule mismatch details

As of 2026-04-02:

- parent repo records submodule commit: `20ba71827870452ecbd54df79075631da0b39d8d`
- local submodule checkout is at: `dd8c956ffd3002c65deb39860c5f6d0aa0fcfbcc`

So the first practical task is alignment. Until that is fixed, the "native EVMBench + Yudai adapter" path is conceptually correct but operationally inconsistent.

## Why the Native EVMBench Path Is Correct

Do not force EVMBench into `benchmark.csv`.

The cleaner architecture, already documented in this repo, is:

1. EVMBench owns datasets, splits, task containers, and grading.
2. This repo provides the Yudai/mini-swe-agent runtime and orchestration.
3. TTS work happens in the agent/controller layer.

Use the legacy exploit harness only as a source of reusable ideas, especially:

- early failure detection
- exploit verification logic
- verbose branch instrumentation

## Key Files To Work From

### Native EVMBench path

- `EVMBENCH_INTEGRATION_GUIDE.md`
- `src/minisweagent/run/extra/evmbench.py`
- `src/minisweagent/run/extra/evmbench_agent.py`
- `src/minisweagent/config/extra/evmbench.yaml`

### Embedded EVMBench side

- `evmBench-frontier-evals/project/evmbench/README.md`
- `evmBench-frontier-evals/project/evmbench/evmbench/agents/yudai/config.yaml`
- `evmBench-frontier-evals/project/evmbench/evmbench/agents/yudai/start.sh`
- `evmBench-frontier-evals/project/evmbench/evmbench/Dockerfile.yudai`

### Reusable legacy harness logic

- `exploit_generation/benchmark_episode.py`
- `scripts/run_benchmark_exploit_v3.py`

### TTS planning artifact

- `tts-evmbench-guide.html`

## TTS Strategy Summary

The guide points to this priority order:

1. Start with `detect`
2. Then `exploit`
3. Then `patch`

And this method priority:

1. Snell-style difficulty routing
2. ToT / FoT branching for coverage
3. S*-style execution-guided selection
4. ACTS-style adaptive control later

Important constraint: true ACTS depends on token-level signals or logprobs. The current model layer in this repo does not expose that in a practical way, so ACTS should be treated as a later or approximate phase, not the first implementation target.

## Step-by-Step Getting Started Plan

### Phase 0: Align the EVMBench integration

Goal: make the root repo and EVMBench submodule agree on one agent interface.

Steps:

1. Update the EVMBench submodule agent config to support:
   - `yudai-detect`
   - `yudai-patch`
   - `yudai-exploit`
2. Make those entries call the current mini-swe-agent EVMBench entrypoint.
3. Ensure the submodule startup path uses the root-side `minisweagent.run.extra.evmbench_agent` flow, not the older standalone script loop.
4. Add a test that checks the agent IDs referenced in `src/minisweagent/run/extra/evmbench.py` actually exist in the checked-out submodule config.

Success condition:

- one-audit native EVMBench runs start successfully through the Yudai adapter

### Phase 1: Reproduce a clean baseline

Goal: establish a stable baseline before adding TTS.

Commands to use after alignment:

```bash
uv run python -m minisweagent.run.extra.evmbench --sync-runtime-only
```

```bash
OPENROUTER_API_KEY=... \
uv run python -m minisweagent.run.extra.evmbench \
  --mode detect \
  --audit 2024-08-phi \
  --build-images \
  --build-only
```

```bash
OPENROUTER_API_KEY=... \
uv run python -m minisweagent.run.extra.evmbench \
  --mode detect \
  --audit 2024-08-phi \
  --model <baseline-model> \
  --model-class openrouter \
  --hint-level none \
  --concurrency 1
```

Baseline rules:

- use one fixed model
- use `hint-level none`
- use `concurrency 1`
- keep cost limits fixed
- archive run outputs and trajectories

Success condition:

- one stable no-hint detect baseline run with logs and artifacts

### Phase 2: Start TTS with detect mode

Goal: improve vulnerability coverage where EVMBench has the largest upside.

Implement first:

1. Initial repo scan
   - contracts
   - file graph
   - external calls
   - admin/governance surfaces
   - token transfer surfaces
2. Difficulty scoring
   - contract size
   - number of external calls
   - multi-contract interactions
   - token flow complexity
3. Multi-branch detect exploration
   - 3-5 branches
   - each branch starts from a different code region
4. Merge findings
   - deduplicate
   - normalize finding structure
   - write final `submission/audit.md`

Implementation note:

Do this above the current single `InteractiveAgent.run(...)` flow, not as a prompt-only hack.

Success condition:

- detect mode can run multiple branches and produce one merged report

### Phase 3: Add evaluation and ablations for detect

Goal: measure marginal value instead of jumping straight to a full composite agent.

Compare:

1. baseline single-pass detect
2. difficulty routing only
3. multi-branch detect only
4. routing + multi-branch detect

Keep total compute roughly normalized across conditions.

Metrics to track:

- recall
- number of findings
- duplicate findings
- cost
- runtime

Success condition:

- one small evaluation table showing whether TTS improves recall at similar compute

### Phase 4: Move to exploit mode

Goal: apply execution-guided TTS where exploit mode already has a strong verifier.

Implement first:

1. exploit difficulty routing
   - simple one-step
   - medium multi-step
   - complex multi-contract / flash-loan style
2. parallel exploit candidates
   - several candidate transaction sequences
3. execution-guided pruning
   - keep branches with promising balance or state changes
   - stop dead branches early
4. explicit balance/state verification after each serious attempt

Reuse from legacy harness where helpful:

- failure detection
- branch pruning ideas
- execution trace handling

Success condition:

- exploit mode tries multiple candidates and selects based on actual chain feedback

### Phase 5: Move to patch mode

Goal: combine search with test-driven verification.

Implement:

1. candidate vulnerability hypotheses
2. multiple patch proposals per target
3. run tests after each patch candidate
4. retain patches where:
   - normal behavior still works
   - exploit path is blocked

Success condition:

- patch mode supports candidate generation plus execution-guided selection

### Phase 6: Add later-stage adaptive control

Goal: approximate ACTS once the basic TTS stack is working.

Near-term practical version:

- branch on stall
- branch on repeated uncertainty phrases
- trigger self-critique after failed verification
- reallocate budget away from dead paths

Later research version:

- real spike-based stopping if a model backend exposes useful logprobs

Success condition:

- adaptive control reduces wasted compute on dead branches

## Recommended Immediate Next Actions

Do these in order:

1. Fix the root/submodule EVMBench agent mismatch.
2. Run a single native EVMBench detect audit end-to-end.
3. Freeze the no-hint baseline.
4. Implement a minimal detect orchestrator with 3 branches.
5. Evaluate baseline vs multi-branch detect on a small audit subset.

## What Not To Do First

- Do not start by importing EVMBench into `benchmark.csv`
- Do not start with patch mode
- Do not start with full ACTS/logprob work
- Do not combine all TTS techniques before measuring isolated gains

## Definition of Done for the First Milestone

The first milestone is complete when all of the following are true:

1. Native EVMBench detect runs cleanly through the aligned Yudai adapter.
2. A no-hint baseline run is archived.
3. A minimal multi-branch detect controller exists.
4. You have a small ablation showing whether multi-branch detect helps.

That gets the repo back onto the right track for serious TTS-on-EVMBench work.
