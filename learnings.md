# Learnings

## Benchmark exploit runs (2026-01-25 to 2026-01-26)

### Prompt and control flow
- `scripts/run_benchmark_exploit.py` selects the case, fetches source, and calls `exploit_generation/benchmark_episode.py` which builds the task prompt and launches the agent via `src/minisweagent/config/benchmark_exploit.yaml`.
- The prompt is layered: `_build_task_prompt` adds workflow text, then `benchmark_exploit.yaml` repeats a workflow section and inlines the full source in `<solidity>`. This duplication is the main driver of huge prompt sizes for large sources (e.g., `pickle`).
- The system template enforces exactly one bash code block. Any deviation triggers a format error, which appears in multiple trajectories.
- Because the config includes `mode`/`whitelist_actions`, the runner always uses `InteractiveAgent` even without `--interactive`. Step-limit handling becomes interactive and can fail if input is blank.
- Action observations are appended to the conversation. Repeated `cat src/Target.sol` and full Strategy rewrites quickly inflate context and cost.

### Model effects
- `google/gemini-3-flash-preview` tends to jump into iterative exploit code + `forge script`, which increases context and cost rapidly (notably for `sdao`).
- A provider-side `MALFORMED_FUNCTION_CALL` surfaced in the bancor trajectory, producing an empty response and a format error.
- `deepseek/deepseek-v3.2` is more reconnaissance-heavy (more `cast`/`cat`, fewer `forge script` runs), but still hits the 15-step cap without reaching success.
- Deepseek completions exceeded `max_tokens: 4096` in multiple steps, implying upstream param dropping or provider-side overrides.

### Run snapshots
- `bancor` (Gemini): mostly `cast` probes; one Strategy write; provider error + format error; interrupted at step limit.
- `pickle` (Gemini): very large source; many Strategy + `forge script` iterations; huge prompt sizes; interrupted.
- `brahtopg` (Gemini): mixed probes and Strategy iterations; interrupted.
- `sdao` (Gemini): aggressive flash-loan approach; highest context size and cost; interrupted.
- `sdao` (Deepseek): more code reading, fewer `forge` runs; format error; interrupted.
- `qixi` (Deepseek): storage/owner probing only; format error; interrupted before any `forge` run.
- `bevo` (Deepseek): fee reconnaissance; hit step limit and failed on empty interactive input.

## Actionable steps
1. Raise `step_limit` and/or `cost_limit` for benchmark runs to avoid hard stops at 15 steps.
2. Run with `--no-interactive` (or change config) to avoid interactive step-limit prompts and blank-input failures.
3. Reduce prompt bloat by removing duplicate workflow text or trimming the inlined source in `benchmark_exploit.yaml`.
4. Instruct the agent to avoid repeated `cat src/Target.sol` and full Strategy rewrites; prefer targeted `sed`/`rg` and minimal edits.
5. Choose model per case: Gemini for faster iteration but higher cost, Deepseek for deeper reconnaissance if you lift the step limit.
