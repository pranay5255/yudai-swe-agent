# RCA: Qwen vLLM Modal Forest 2-Tree Canto Run

Date: 2026-05-05 UTC

Run root:

`runs/phase6/qwen-vllm-2tree-canto-2026-05-05`

Preserved RCA bundle:

`runs/rca/qwen-vllm-2tree-canto-2026-05-05`

## What Was Saved

Local Phase 6 command logs:

- `runs/rca/qwen-vllm-2tree-canto-2026-05-05/_phase6_command_logs/modal-forest-qwen-vllm-2trees-debug/2024-01-canto.stdout.log`
- `runs/rca/qwen-vllm-2tree-canto-2026-05-05/_phase6_command_logs/modal-forest-qwen-vllm-2trees-debug/2024-01-canto.stderr.log`

Fetched Modal app logs:

- `runs/rca/qwen-vllm-2tree-canto-2026-05-05/modal-app-swe-rex-2026-05-05T1520-1620.log`
- `runs/rca/qwen-vllm-2tree-canto-2026-05-05/modal-app-vllm-2026-05-05T1520-1620.log`

Final copied Modal forest artifacts:

- `runs/rca/qwen-vllm-2tree-canto-2026-05-05/modal-forest-qwen-vllm-2trees-debug/2026-05-05T15-29-29-GMT_run-group_mini-swe-agent-modal-forest-qwen-vllm-2trees-debug_detect/2024-01-canto_a7bef0fc-6fd0-40ee-84b1-55cdf289422f/modal/logs/modal-forest-result.json`
- `runs/rca/qwen-vllm-2tree-canto-2026-05-05/modal-forest-qwen-vllm-2trees-debug/2026-05-05T15-29-29-GMT_run-group_mini-swe-agent-modal-forest-qwen-vllm-2trees-debug_detect/2024-01-canto_a7bef0fc-6fd0-40ee-84b1-55cdf289422f/modal/logs/forest/trajectory-manifest.json`
- `runs/rca/qwen-vllm-2tree-canto-2026-05-05/modal-forest-qwen-vllm-2trees-debug/2026-05-05T15-29-29-GMT_run-group_mini-swe-agent-modal-forest-qwen-vllm-2trees-debug_detect/2024-01-canto_a7bef0fc-6fd0-40ee-84b1-55cdf289422f/modal/logs/forest/*.traj.json`

Saved sizes:

- RCA bundle: about 2.7M
- Local stdout/stderr command logs: 5,395 lines, 808,514 bytes
- Modal `swe-rex` app log: 1,468 lines, 158,867 bytes
- Modal vLLM app log: 1,545 lines, 291,283 bytes

## High-Level Finding

The 38 Modal sandboxes were expected from the current control flow after failures. They were not from "2 trees" alone.

One full 2-role forest attempt creates 6 worker sandboxes:

- 1 scout
- 2 branch workers: `token-flow` and `accounting`
- 2 tree judges: one per role
- 1 global judge

The logs show 6 completed failed attempts, then a partial seventh attempt interrupted during branch startup:

- 6 full attempts * 6 sandboxes = 36 sandboxes
- partial seventh attempt got through scout and started a branch = 2 more sandboxes
- total observed unique sandboxes = 38

The same multiplication happened to runtime HTTP calls. The fetched `swe-rex` app log contains 38 unique Modal task/container ids and hundreds of runtime `GET /is_alive`, `POST /execute`, and `POST /close` calls.

## Why It Retried So Many Times

`common/nanoeval/nanoeval/eval.py` sets `RunnerArgs.max_retries` to 16 by default.

`common/nanoeval/nanoeval/evaluation.py` requeues a task when the clean result is a `RolloutSystemError` and `task.retry_idx < spec.runner.max_retries`.

`evmbench/nano/solver.py` wraps Modal runner failures as `RolloutSystemError`.

`evmbench/agents/mini-swe-agent/evaluate_phase6.py` builds the Phase 6 command with only:

`runner.concurrency=1`

It does not pass:

`runner.max_retries=0`

So every Modal forest infrastructure failure caused nanoeval to run the entire forest again. With the default retry value, an uninterrupted run could have tried up to 17 total attempts for one audit.

`--stop-on-failure` in Phase 6 only stops the matrix after the underlying nanoeval command exits. It does not stop nanoeval's internal retry loop.

`PHASE6_ITEM_TIMEOUT_SECONDS=7200` only caps the matrix item wall time. It does not make the run a single attempt.

## Why Failed Attempts Kept Spending All 6 Sandboxes

`evmbench/agents/mini-swe-agent/config.yaml` configures `mini-swe-agent-modal-forest-qwen-vllm-2trees-debug` with:

`FOREST_CONTINUE_ON_WORKER_ERROR: "1"`

`evmbench/agents/modal_runner.py` turns that into:

`--continue-on-worker-error`

`evmbench/agents/mini-swe-agent/modal_forest.py` then continues to branches, tree judges, and global judge even if scout or branches failed. That is useful if the purpose is trace collection under partial failure, but it is expensive and noisy during infrastructure debugging.

For this run, that meant the forest continued after the scout failed to write `scout.md`, and continued after branch context overflow errors.

## Why Qwen Produced Bad Or Missing Artifacts

There are two separate model/runtime failure modes in the saved artifacts.

### 1. Scout hit its step limit

The final saved `scout.traj.json` has:

- `exit_status`: `LimitsExceeded`
- `api_calls`: 12
- missing artifact: `/home/agent/forest/scout/scout.md`

The scout spent budget inspecting the broad audit workspace and audit-generated reports, including gas/non-critical report content, then exhausted its step limit without writing the required scout files.

That is why Modal forest logged:

`verify scout output exists failed with return code 1`

### 2. Branches filled the 32k context window

The final saved `token-flow/branch-01.traj.json` has:

- `exit_status`: `ContextWindowExceededError`
- `api_calls`: 18
- final successful model usage near the limit: `prompt_tokens=29688`, `completion_tokens=3080`, `total_tokens=32768`
- next query failed because the prompt exceeded the server limit

The repeated error was:

`This model's maximum context length is 32768 tokens. However, you requested 0 output tokens and your prompt contains at least 32769 input tokens`

This was not a Modal H100 health issue. The branch simply accumulated enough prompt and tool-output history to exceed the vLLM server's configured `max_model_len=32768`.

## Why Context Was So Large

`audits/2024-01-canto/config.yaml` has no `patch_path_mapping` entries.

`evmbench/agents/mini-swe-agent/modal_forest.py` derives audit scope files from `vulnerability.patch_path_mapping`.

For detect mode, if no scope files exist, the forest explicitly uses full workspace scope. There is a test for this exact behavior in `tests/test_mini_swe_agent_forest.py`:

`test_detect_audit_without_patch_mapping_uses_full_workspace_scope`

So for `2024-01-canto`, every worker was told the full `/home/agent/audit` workspace was in scope. That pushed Qwen into broad file/report reading, large observations, and eventually a context overflow.

## Artifact Preservation Problem

The retry attempts reused the same task `run_dir` and Modal forest `output_dir`:

`.../2024-01-canto_a7bef0fc-.../modal`

As a result, `modal-forest-result.json` and copied artifacts represent only the last completed attempt before interruption. Earlier attempt metadata was overwritten. The complete chronology survives mainly in the Phase 6 stdout/stderr logs and the fetched Modal app logs.

This is a separate bug for dataset building: retries should write attempt-specific output dirs, or Phase 6 should copy each attempt's Modal artifacts before retry overwrite.

## Root Causes

1. Nanoeval retry multiplication: Modal runner failures become `RolloutSystemError`, and nanoeval defaults to 16 retries.
2. Phase 6 does not override `runner.max_retries`, so one failed audit can become many full Modal forest attempts.
3. The Qwen 2-tree debug runner enables `FOREST_CONTINUE_ON_WORKER_ERROR=1`, so each failed attempt continues to later stages and spends all expected worker sandboxes.
4. `2024-01-canto` has no scope metadata, so detect-mode forest workers use the full audit workspace.
5. The one-H100 vLLM deployment is configured at 32k context, and branch trajectories exceeded that context after normal tool use.
6. Retry attempts overwrite the same Modal forest output directory, which damages RCA and dataset trace preservation.
7. Each forest worker creates a fresh Modal/SWE-ReX sandbox, and the logs show each sandbox bootstrapping `swe-rex` at runtime. There is no sandbox reuse in the current forest architecture.

## Fix Plan

### Immediate safety fixes

1. Add `runner.max_retries=0` to Phase 6 Modal debug commands, or expose it through a Phase 6 CLI/env option.
2. Add a Qwen debug runner that does not set `FOREST_CONTINUE_ON_WORKER_ERROR=1`.
3. Do not use Phase 6 for the next Qwen Modal debug run. Use direct `entrypoint.py forest` so there is no nanoeval retry loop.
4. Start with one role, one branch, low step limits, and no `--continue-on-worker-error`.

### Dataset-quality fixes

1. Add scope metadata for Canto, or add a Modal forest CLI override for scope files.
2. Reduce prompt/history growth before scaling forest width:
   - limit or summarize large file/report observations
   - avoid feeding full audit-generated reports into scout/branch prompts
   - lower branch step limits until scope is fixed
3. Preserve per-attempt artifacts:
   - include `retry_idx` in Modal output dirs, or
   - copy Modal logs/artifacts into an attempt-specific archive before nanoeval requeues.
4. Consider prebuilding `swe-rex` into the audit image or using a Modal image layer so each sandbox does not install/bootstrap it at runtime.
5. Only after one-role direct forest produces valid scout, branch, judge, and submission artifacts should Phase 6 be used for matrix-style data collection.

## Next Run Recommendation

For data gathering and final dataset building, do not run Phase 6 yet. Run direct Modal forest first.

Reason: Phase 6 currently hides the per-attempt failure by retrying and overwriting artifacts. Direct Modal forest gives one interpretable run and stops as soon as the first hard failure happens.

Use this no-healthcheck direct forest command:

```bash
set -a
. ./.env
set +a

export UV_CACHE_DIR=/tmp/uv-cache
export MODEL="${VLLM_LITELLM_MODEL:-openai/${VLLM_SERVED_MODEL_NAME}}"
export MODEL_KWARGS_JSON="${MODEL_KWARGS_JSON:-{\"drop_params\":true}}"
export MSWEA_COST_TRACKING="${MSWEA_COST_TRACKING:-ignore_errors}"
export OUTPUT_DIR="runs/modal-forest-debug/qwen-1role-canto-$(date -u +%Y%m%dT%H%M%SZ)"

uv run python evmbench/agents/mini-swe-agent/entrypoint.py forest \
  --audit-id 2024-01-canto \
  --mode detect \
  --hint-level none \
  --image "${MODAL_AUDIT_IMAGE_REPO:-ghcr.io/pranay5255/evmbench-audit}:2024-01-canto" \
  --model "$MODEL" \
  --model-kwargs-json "$MODEL_KWARGS_JSON" \
  --cost-tracking "$MSWEA_COST_TRACKING" \
  --scout-step-limit 4 \
  --branch-step-limit 6 \
  --judge-step-limit 4 \
  --global-step-limit 4 \
  --scout-cost-limit 0.5 \
  --branch-cost-limit 0.5 \
  --judge-cost-limit 0.5 \
  --global-cost-limit 0.5 \
  --branches-per-tree 1 \
  --max-tree-roles 1 \
  --tree-roles token-flow \
  --worker-concurrency 1 \
  --output-dir "$OUTPUT_DIR"
```

Expected sandbox count for this direct run:

- If scout fails: 1 sandbox
- If scout succeeds and branch fails: 2 sandboxes
- If the whole one-role forest runs: 4 sandboxes

Do not add `--continue-on-worker-error` for debugging.

## Modal Log Fetch Commands

For this specific run, app IDs were:

- `ap-acsjht4VvB6wK6tD7c2k8B`: `swe-rex`
- `ap-okdjNyULebZU18oaHEdD9x`: `evmbench-vllm-qwen`

Use app IDs rather than names for stopped apps:

```bash
mkdir -p runs/rca/qwen-vllm-2tree-canto-2026-05-05

env UV_CACHE_DIR=/tmp/uv-cache uv run modal app logs ap-acsjht4VvB6wK6tD7c2k8B \
  --timestamps \
  --show-function-id \
  --show-function-call-id \
  --show-container-id \
  --since 2026-05-05T15:20:00 \
  --until 2026-05-05T16:20:00 \
  --tail 10000 \
  > runs/rca/qwen-vllm-2tree-canto-2026-05-05/modal-app-swe-rex-2026-05-05T1520-1620.log

env UV_CACHE_DIR=/tmp/uv-cache uv run modal app logs ap-okdjNyULebZU18oaHEdD9x \
  --timestamps \
  --show-function-id \
  --show-function-call-id \
  --show-container-id \
  --since 2026-05-05T15:20:00 \
  --until 2026-05-05T16:20:00 \
  --tail 10000 \
  > runs/rca/qwen-vllm-2tree-canto-2026-05-05/modal-app-vllm-2026-05-05T1520-1620.log
```

## Phase 6 After Fixes

Only use Phase 6 after adding a no-retry option. The intended command shape should include `runner.max_retries=0` in the generated nanoeval command.

Until `evaluate_phase6.py` supports that knob, this direct nanoeval command is safer than the wrapper, but it still uses the agent config that enables `FOREST_CONTINUE_ON_WORKER_ERROR=1`:

```bash
set -a
. ./.env
set +a

export UV_CACHE_DIR=/tmp/uv-cache
export PHASE6_RUNS_DIR="runs/phase6/manual-qwen-no-retry-$(date -u +%Y%m%dT%H%M%SZ)"

uv run python -m evmbench.nano.entrypoint \
  evmbench.audit=2024-01-canto \
  evmbench.mode=detect \
  evmbench.audit_split=detect-tasks \
  evmbench.hint_level=none \
  evmbench.log_to_run_dir=True \
  evmbench.runs_dir="$PHASE6_RUNS_DIR" \
  evmbench.solver=evmbench.nano.solver.EVMbenchSolver \
  evmbench.solver.agent_id=mini-swe-agent-modal-forest-qwen-vllm-2trees-debug \
  runner.concurrency=1 \
  runner.max_retries=0
```

Prefer the direct `entrypoint.py forest` command above until there is a no-retry/no-continue Qwen runner.
