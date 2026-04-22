# Meta-Agent Abstraction Study

This report studies the current Yudai fork against upstream `mini-swe-agent` and defines the abstractions needed to:

1. create new Docker images with a mini-SWE-agent style agent
2. change prompts from execution traces with another mini-SWE-agent style agent
3. expose those agents through bash CLI commands in the same spirit as `mini` and `mini-extra`

The main conclusion is that the useful unit is not "a custom script". The useful unit is an object graph:

```text
Agent = AgentClass(Model, Environment, AgentConfig)
Run = Runner(Agent, TaskSource, ArtifactContract, SavePolicy)
Profile = PromptConfig + EnvironmentConfig + ModelConfig + RunnerConfig
```

New agents should be declared as profiles and wired through small runners. Docker images and prompt updates are just two different task domains that reuse the same loop.

## Evidence Used

Local git evidence:

- Current fork head: `6e319c8` (`Update EVMBench submodule`)
- Official upstream main fetched as `upstream/main`: `bc85a45`
- Merge base with upstream: `5824d54` (`Doc: single mode doesn't produce a preds.json file (#677)`, 2026-01-02)
- Local branch is 394 commits ahead of that merge base.
- Upstream main is 239 commits ahead of that merge base.

GitHub API evidence gathered with `gh api`:

- `SWE-agent/mini-swe-agent` default branch is `main`, pushed at `2026-04-20T21:22:09Z`.
- Latest official release is `v2.2.8`, published at `2026-03-24T16:52:22Z`.
- `pranay5255/yudai-swe-agent` default branch is `main`, pushed at `2026-04-14T21:34:11Z`.

External API and design references:

- [mini-SWE-agent API reference](https://mini-swe-agent.com/latest/reference/)
- [mini CLI docs](https://mini-swe-agent.com/latest/usage/mini/)
- [Python bindings](https://mini-swe-agent.com/latest/usage/python_bindings/)
- [YAML configuration guide](https://mini-swe-agent.com/latest/advanced/yaml_configuration/)
- [Environment guide](https://mini-swe-agent.com/latest/advanced/environments/)
- [Cookbook: subclassing and mix-and-match components](https://mini-swe-agent.com/latest/advanced/cookbook/)
- [Official GitHub repository](https://github.com/SWE-agent/mini-swe-agent)

## Current Fork Summary

The fork has moved in three major directions:

1. It generalizes the old single-action text loop into a model-driven action interface:
   - `DefaultAgent.query()` now passes `tools=self.env.get_tools()`.
   - `DefaultAgent.get_observations()` executes `message["actions"]`.
   - Models own action parsing and observation formatting.

2. It adds security and exploit environments:
   - `FoundryEnvironmentV3`
   - `ExploitFoundryEnvironmentV3`
   - Foundry, Anvil, Forge script trace parsing, balance/profit measurement

3. It adds EVMBench integration:
   - host runner: `src/minisweagent/run/extra/evmbench.py`
   - container agent entrypoint: `src/minisweagent/run/extra/evmbench_agent.py`
   - benchmark prompt: `src/minisweagent/config/extra/evmbench.yaml`
   - embedded EVMBench adapter path: `evmBench-frontier-evals/project/evmbench/evmbench/agents/yudai/`

These are the right directions, but the current fork mixes clean abstractions with partially staged integration code.

## Important Current Breakages

These need to be fixed before building more meta-agent machinery on top.

### 1. Console scripts were removed

The fork removed `[project.scripts]` from `pyproject.toml`. As a result:

```bash
uv run mini-extra --help
```

fails with:

```text
Failed to spawn: `mini-extra`
Caused by: No such file or directory
```

The module form still works:

```bash
uv run python -m minisweagent.run.mini_extra --help
```

Recommendation: restore console scripts immediately:

```toml
[project.scripts]
mini = "minisweagent.run.mini:app"
mini-swe-agent = "minisweagent.run.mini:app"
mini-extra = "minisweagent.run.mini_extra:main"
mini-e = "minisweagent.run.mini_extra:main"
```

Once new runners exist, extend `src/minisweagent/run/mini_extra.py`, not `pyproject.toml`, for subcommands.

### 2. EVMBench Yudai mode IDs are inconsistent

`src/minisweagent/run/extra/evmbench.py` maps:

```python
detect -> yudai-detect
patch -> yudai-patch
exploit -> yudai-exploit
```

But the embedded EVMBench config currently defines only:

```yaml
yudai-default
yudai-opus
yudai-haiku
```

Verification:

```bash
uv run --extra dev pytest tests/run/test_evmbench.py tests/models/test_test_models.py -q
```

result:

```text
1 failed, 8 passed
FAILED tests/run/test_evmbench.py::test_yudai_agent_ids_exist_in_embedded_evmbench_config
```

Recommendation: choose one naming model.

Preferred:

```yaml
yudai-detect:
  start: yudai/start.sh
  instruction_file_name: AGENTS.md
  env_vars:
    YUDAI_EVMBENCH_MODE: detect

yudai-patch:
  start: yudai/start.sh
  instruction_file_name: AGENTS.md
  env_vars:
    YUDAI_EVMBENCH_MODE: patch

yudai-exploit:
  start: yudai/start.sh
  instruction_file_name: AGENTS.md
  env_vars:
    YUDAI_EVMBENCH_MODE: exploit
```

### 3. EVMBench build references a missing Dockerfile

`src/minisweagent/run/extra/evmbench.py` tries to build:

```text
evmbench/Dockerfile.yudai
```

That file is not present under:

```text
evmBench-frontier-evals/project/evmbench/evmbench/
```

Recommendation: do not overload `evmbench/base:latest` with Yudai. Add an explicit Yudai image family:

```text
evmbench/base:latest              generic benchmark base
evmbench/base-yudai:latest        benchmark base plus Yudai runtime
evmbench/audit:<audit_id>         generic audit image
evmbench-yudai/audit:<audit_id>   Yudai-flavored audit image
```

Then make audit Dockerfiles take:

```dockerfile
ARG EVMBENCH_BASE_IMAGE=evmbench/base:latest
FROM ${EVMBENCH_BASE_IMAGE}
```

### 4. The embedded EVMBench start script is stale

`evmbench/agents/yudai/start.sh` still writes an inline Anthropic-only Python agent to `/tmp/yudai_evmbench_agent.py`.

That bypasses the newer reusable entrypoint:

```bash
python -m minisweagent.run.extra.evmbench_agent
```

Recommendation: replace the inline script with a thin launcher that:

- ensures `evmbench/vendor/yudai_runtime/src` is on `PYTHONPATH`
- forwards model env vars
- calls `python -m minisweagent.run.extra.evmbench_agent`
- writes the trajectory to `/home/logs/yudai-minisweagent.traj.json`

## Upstream API Shape To Preserve

Upstream v2 documentation has converged on four interchangeable parts:

1. Agent class
2. Environment class
3. Model class
4. Run script/config binding

The official cookbook describes this explicitly: pick an agent class, pick an environment class, pick a model class, then bind them in a run script or config. That is the correct abstraction to copy.

The fork should not create new monolithic scripts for every domain. It should create domain-specific profiles that assemble the same components.

## Current Object Model In The Fork

### Agent

`DefaultAgent` is the loop:

```text
run(task)
  add system + instance messages
  while true:
    response = model.query(messages, tools=env.get_tools())
    actions = response.extra.actions
    outputs = [env.execute(action) for action in actions]
    observations = model.format_observation_messages(outputs)
    append observations
```

Useful changes in the fork:

- `RunResult` is dict-like but supports tuple unpacking.
- control-flow exceptions moved to `minisweagent.exceptions`.
- `DefaultAgent.save()` now writes model, environment, and agent type metadata.
- `planner_mode` allows multiple bash blocks per model response.

Design implication: do not subclass the agent for every domain. Subclass only when the loop changes. Most new behavior belongs in:

- environment execution
- prompt config
- trace/result analysis around the agent

### Model

There are two action styles:

- tool-call models, such as `LitellmModel`, using a `bash` tool schema
- text-parsed models, such as `OpenRouterModel`, using markdown bash code block parsing

`OpenRouterModel` now accepts:

```python
planner_mode
planner_action_regex
```

and delegates to `parse_text_actions()`.

Design implication: `PromptSpec` must include the action protocol. A prompt is invalid unless it matches the model parser.

### Environment

The environment interface is small:

```python
execute(action) -> dict
get_template_vars() -> dict
get_tools() -> list[dict]
serialize() -> dict
```

Current domain environments include:

- `LocalEnvironment`
- `DockerEnvironment`
- `FoundryEnvironmentV3`
- `ExploitFoundryEnvironmentV3`

Design implication: Docker image creation should be an environment/task capability, not a separate agent framework.

### Runner

Current runners are mixed:

- `mini`: local interactive runner
- `mini_extra`: subcommand dispatcher
- `evmbench`: host-side EVMBench runner
- `evmbench_agent`: in-container EVMBench agent entrypoint
- benchmark exploit scripts: local benchmark harness runners

Design implication: create a reusable runner pattern:

```text
load profile -> build model -> build environment -> build agent -> run task -> save trajectory -> verify artifacts
```

## Proposed Core Abstractions

Add these concepts as lightweight classes or Pydantic models. They should not replace mini-SWE-agent. They should compose it.

```python
class AgentProfile(BaseModel):
    name: str
    description: str = ""
    agent: dict
    model: dict
    environment: dict
    runner: dict = {}
    artifacts: dict = {}
    trace_policy: dict = {}
```

```python
class ArtifactContract(BaseModel):
    required_paths: list[str]
    optional_paths: list[str] = []
    success_checks: list[str] = []
    forbidden_paths: list[str] = []
```

```python
class AgentFactory:
    def build(self, profile: AgentProfile):
        model = get_model(config=profile.model)
        env = get_environment(profile.environment)
        agent_cls = get_agent_class(profile.agent.get("agent_class", "default"))
        return agent_cls(model, env, **profile.agent)
```

```python
class RunHarness:
    def run(self, profile: AgentProfile, task: str) -> dict:
        agent = AgentFactory().build(profile)
        result = agent.run(task)
        trajectory = agent.save(exit_info=result)
        return self.verify(profile.artifacts, trajectory)
```

Important: the profile is the user-facing abstraction. The class graph is the implementation detail.

## Agent 1: Docker Image Factory Agent

Goal: create, build, validate, and optionally publish Docker images using the same agent loop.

### What the agent controls

The agent should be allowed to edit:

```text
docker/
docker/templates/
evmBench-frontier-evals/project/evmbench/evmbench/Dockerfile.yudai-base
evmBench-frontier-evals/project/evmbench/audits/*/Dockerfile
```

The agent should execute:

```bash
docker build ...
docker image inspect ...
docker run --rm ...
uv run --extra dev pytest ...
```

### What the agent must not own

It should not own benchmark scoring logic. It should not rewrite EVMBench task, grader, or solver semantics just to build an image.

### Image object model

```python
class DockerImageSpec(BaseModel):
    name: str
    tag: str
    dockerfile: Path
    context: Path
    build_args: dict[str, str] = {}
    platform: str = "linux/amd64"
    smoke_tests: list[str] = []
```

```python
class DockerImageFamily(BaseModel):
    base: DockerImageSpec
    children: list[DockerImageSpec] = []
```

### Recommended families

Local exploit generation:

```text
yudai-base:fast
yudai-base:latest
```

EVMBench:

```text
evmbench/base:latest
evmbench/base-yudai:latest
evmbench/audit:<audit_id>
evmbench-yudai/audit:<audit_id>
```

### Current commands

Local Yudai images:

```bash
docker build -t yudai-base:fast -f docker/Dockerfile.base-fast .
docker build -t yudai-base:latest -f docker/Dockerfile.base .
```

Current intended EVMBench path:

```bash
uv run python -m minisweagent.run.extra.evmbench --sync-runtime-only
uv run python -m minisweagent.run.extra.evmbench --mode detect --audit 2024-08-phi --build-images --build-only -m <model>
```

But this path is blocked until the missing `Dockerfile.yudai` and mode IDs are fixed.

### Proposed CLI

After restoring package scripts:

```bash
mini-extra image build -c src/minisweagent/config/images/yudai_foundry.yaml --tag yudai-base:fast
mini-extra image build-evmbench --agent yudai --audit 2024-08-phi --family yudai
mini-extra image smoke --tag yudai-base:fast --check forge --check slither --check echidna-test
```

Implementation location:

```text
src/minisweagent/run/extra/image_factory.py
src/minisweagent/images/specs.py
src/minisweagent/images/builder.py
src/minisweagent/config/images/yudai_foundry.yaml
tests/run/test_image_factory.py
```

The image factory itself can be run by mini-SWE-agent:

```bash
uv run python -m minisweagent.run.mini \
  -c src/minisweagent/config/image_factory_agent.yaml \
  -t "Create a fast Foundry image with slither and echidna, build it, and update the smoke tests."
```

## Agent 2: Trace-Driven Prompt Tuning Agent

Goal: read execution traces and result artifacts, infer failure modes, and update prompt/config files.

The current fork already captures useful data:

- trajectory files via `save_traj()`
- model messages, actions, observations, costs
- `ExploitFoundryEnvironmentV3.execution_traces`
- parsed Forge script summaries from `exploit_generation/trace_parser.py`
- result JSON from `run_benchmark_exploit_episode()`

### Prompt tuning object model

```python
class TraceBundle(BaseModel):
    trajectory_path: Path
    result_path: Path | None = None
    raw_logs: list[Path] = []
```

```python
class FailureTaxonomy(BaseModel):
    setup_failure: bool = False
    format_failure: bool = False
    tool_failure: bool = False
    recon_failure: bool = False
    exploit_logic_failure: bool = False
    validation_failure: bool = False
    early_abort_reason: str | None = None
```

```python
class PromptPatch(BaseModel):
    target_config: Path
    rationale: str
    patch_text: str
    expected_metric_change: str
    regression_tests: list[str]
```

### Prompt update loop

```text
1. Run baseline tasks.
2. Collect trajectories and result JSON.
3. Parse actions, observations, trace summaries, exits, cost, and success.
4. Classify failure modes.
5. Ask a PromptTuningAgent to edit only prompt/config files.
6. Run a canary subset.
7. Accept only if success or diagnostic quality improves without breaking action format.
```

### What the prompt tuner should edit

Good targets:

```text
src/minisweagent/config/extra/evmbench.yaml
src/minisweagent/config/benchmark_exploit_v3.yaml
src/minisweagent/run/extra/evmbench_agent.py
```

The tuner should usually not edit:

```text
exploit_generation/trace_parser.py
src/minisweagent/agents/default.py
src/minisweagent/models/*
EVMBench graders
```

Those are runtime semantics, not prompt policy.

### Proposed CLI

```bash
mini-extra prompt-tune \
  --config src/minisweagent/config/extra/evmbench.yaml \
  --traces evmBench-frontier-evals/project/evmbench/runs \
  --mode detect \
  --out docs/prompt_tuning_reports/evmbench_detect.md
```

```bash
mini-extra prompt-tune apply \
  --proposal docs/prompt_tuning_reports/evmbench_detect.patch.md \
  --canary "uv run --extra dev pytest tests/run/test_evmbench.py -q"
```

Implementation location:

```text
src/minisweagent/run/extra/prompt_tune.py
src/minisweagent/tuning/traces.py
src/minisweagent/tuning/failure_taxonomy.py
src/minisweagent/tuning/prompt_mutator.py
src/minisweagent/config/prompt_tuner.yaml
tests/tuning/test_trace_taxonomy.py
```

### Prompt-tuning agent prompt contract

The prompt tuner should be constrained like this:

```text
You are a prompt tuning agent.
You may read trajectory JSON, result JSON, logs, and YAML configs.
You may edit only prompt/config files listed in the task.
You must preserve action_regex/format_error_template compatibility.
You must produce a short rationale and a minimal patch.
You must run the requested canary tests before finishing.
```

This is still exactly mini-SWE-agent: same loop, different environment, different prompt, different artifact contract.

## Best Abstraction Boundary

Use this rule:

```text
If the behavior changes how actions are selected, parsed, executed, or observed, it belongs in Agent/Model/Environment.
If the behavior changes what the agent is trying to do, it belongs in PromptConfig.
If the behavior changes how runs are launched, repeated, scored, or archived, it belongs in Runner/Harness.
```

Applying that rule:

- Docker image creation belongs in `Runner + Environment + PromptConfig`.
- Trace-driven prompt changes belong in `Runner + TraceAnalyzer + PromptConfig`.
- EVMBench grading belongs in EVMBench, not in Yudai.
- Foundry/Anvil execution belongs in Environment.
- Model-specific bash parsing belongs in Model.

## Immediate Implementation Plan

### Phase 1: Restore runnable CLI baseline

1. Restore `[project.scripts]` in `pyproject.toml`.
2. Add a CLI test that `uv run mini-extra --help` works.
3. Keep module invocation as a fallback:

```bash
uv run python -m minisweagent.run.mini_extra --help
```

### Phase 2: Fix EVMBench adapter consistency

1. Add `yudai-detect`, `yudai-patch`, and `yudai-exploit` to embedded EVMBench config.
2. Replace stale `start.sh` inline Anthropic agent with the reusable `evmbench_agent` module.
3. Add or rename the missing Yudai Dockerfile.
4. Add tests that all referenced Dockerfiles exist.
5. Re-run:

```bash
uv run --extra dev pytest tests/run/test_evmbench.py -q
```

### Phase 3: Introduce agent profiles

Add a minimal profile loader without refactoring the whole codebase:

```text
src/minisweagent/profiles.py
src/minisweagent/config/profiles/image_factory.yaml
src/minisweagent/config/profiles/prompt_tuner.yaml
```

Expose:

```bash
mini-extra profile run -c profiles/image_factory.yaml -t "Build yudai-base:fast and smoke test forge/slither."
mini-extra profile run -c profiles/prompt_tuner.yaml -t "Analyze these traces and update evmbench.yaml."
```

### Phase 4: Add dedicated CLIs only after profiles work

Add ergonomic wrappers:

```bash
mini-extra image ...
mini-extra prompt-tune ...
```

These should call the same profile runner internally.

## Design Decision

The best abstraction is:

```text
AgentProfile
  owns: agent/model/environment config

Runner
  owns: input collection, task construction, artifact verification, trajectory saving

Environment
  owns: command execution and domain tool behavior

TraceAnalyzer
  owns: reading trajectories/results and producing a compact diagnosis

PromptMutator
  owns: safe prompt/config patches
```

This gives you a clean way to create more agents:

```text
ImageFactoryAgent = AgentProfile + Local/Docker environment + Docker artifact contract
PromptTuningAgent = AgentProfile + Local environment + trace artifact contract
EVMBenchAgent = AgentProfile + Local-in-container environment + EVMBench artifact contract
ExploitAgent = AgentProfile + ExploitFoundryEnvironmentV3 + profit artifact contract
```

The agent loop stays small. The domain behavior is explicit and testable.

## Practical Commands After Fixes

Expected commands after restoring console scripts and EVMBench consistency:

```bash
mini -c src/minisweagent/config/mini.yaml -t "Inspect this repo"
```

```bash
mini-extra evmbench \
  --mode detect \
  --audit 2024-08-phi \
  --model minimax/minimax-m2.7 \
  --model-class openrouter \
  --build-images
```

```bash
mini-extra image build \
  --spec src/minisweagent/config/images/yudai_foundry.yaml \
  --tag yudai-base:fast
```

```bash
mini-extra prompt-tune \
  --config src/minisweagent/config/extra/evmbench.yaml \
  --traces evmBench-frontier-evals/project/evmbench/runs \
  --mode detect
```

Until console scripts are restored, use:

```bash
uv run python -m minisweagent.run.mini_extra evmbench --help
```

## Verification Status

Commands run during this study:

```bash
uv run mini-extra --help
```

Result: failed because package console scripts are missing.

```bash
uv run python -m minisweagent.run.mini_extra --help
```

Result: passed and showed the `evmbench` and `exploit-gen` subcommands.

```bash
uv run python -m minisweagent.run.extra.evmbench --help
```

Result: passed and showed EVMBench runner options.

```bash
uv run --extra dev pytest tests/run/test_evmbench.py tests/models/test_test_models.py -q
```

Result: failed because `yudai-detect`, `yudai-patch`, and `yudai-exploit` are missing from embedded EVMBench config.

```bash
uv run --extra dev pytest tests/exploit_generation/test_benchmark_episode.py tests/exploit_generation/test_docker_utils.py -q
```

Result: passed, `12 passed`.

## Final Recommendation

Do not create one-off "meta scripts" for Docker creation and prompt tuning. Create a profile runner and then implement:

1. `ImageFactoryAgent` as a profile plus image artifact contract
2. `PromptTuningAgent` as a profile plus trace artifact contract
3. EVMBench Yudai as a native EVMBench adapter family

This keeps the original mini-SWE-agent idea intact: small loop, composable model, composable environment, explicit prompt, and simple CLI.
