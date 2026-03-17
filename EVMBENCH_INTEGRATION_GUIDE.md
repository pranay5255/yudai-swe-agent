# EVMBench Integration Guide

## Why use EVMBench natively

EVMBench already defines:

- the task datasets and splits
- the per-audit Docker images
- the grading contract for `detect`, `patch`, and `exploit`
- the anti-cheating exploit pipeline (`ploit` + `veto`)

So the clean architecture is:

1. keep EVMBench as the benchmark of record
2. plug Yudai/mini-swe-agent into EVMBench as an agent
3. iterate on Yudai prompts/configs, not on EVMBench grading logic

## What was added

- `mini-extra evmbench`
  - stages the local mini-swe-agent runtime into the embedded EVMBench checkout
  - builds a Yudai EVMBench base image
  - builds the required audit images
  - runs the native EVMBench entrypoint with the Yudai agent adapter
- `minisweagent.run.extra.evmbench_agent`
  - runs mini-swe-agent inside the EVMBench container
  - uses `LocalEnvironment`, so it operates directly on `/home/agent/audit`
  - keeps EVMBench-native outputs:
    - detect: `submission/audit.md`
    - patch: harness extracts `submission/agent.diff` automatically
    - exploit: harness extracts `submission/txs.json` automatically
- EVMBench agent adapter files under:
  - `evmBench-frontier-evals/project/evmbench/evmbench/agents/yudai/`
- Yudai EVMBench base Dockerfile:
  - `evmBench-frontier-evals/project/evmbench/evmbench/Dockerfile.yudai`

## Recommended workflow

### 1. Stage the local runtime into EVMBench

```bash
uv run python -m minisweagent.run.extra.evmbench --sync-runtime-only
```

### 2. Build the Yudai EVMBench images

```bash
OPENROUTER_API_KEY=... \
uv run python -m minisweagent.run.extra.evmbench \
  --mode exploit \
  --audit 2024-08-phi \
  --build-images \
  --build-only
```

### 3. Run one EVMBench exploit audit with Yudai

```bash
OPENROUTER_API_KEY=... \
uv run python -m minisweagent.run.extra.evmbench \
  --mode exploit \
  --audit 2024-08-phi \
  --model z-ai/glm-5-turbo \
  --model-class openrouter \
  --hint-level none \
  --concurrency 1
```

### 4. Run a full split

```bash
OPENROUTER_API_KEY=... \
uv run python -m minisweagent.run.extra.evmbench \
  --mode exploit \
  --split exploit-tasks \
  --model z-ai/glm-5-turbo \
  --model-class openrouter \
  --concurrency 1
```

## Notes

- The current `scripts/run_benchmark_exploit_v3.py` harness is still useful for the older DeFiHackLabs-style benchmark.
- EVMBench should not be forced into `benchmark.csv`; it already has a richer task model and grader.
- If the full local image `yudai-base:latest` is missing, the exploit runner now falls back to `yudai-base:fast` when available.
