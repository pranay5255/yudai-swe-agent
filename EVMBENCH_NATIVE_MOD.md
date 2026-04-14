# EVMBench Native Integration Notes

## Step 1: Benchmark-Side Invariants

The EVMBench-native design has to start from the benchmark's own contract, not from mini-swe-agent.
`evmbench` is intentionally narrow: it wants a backend that can run an agent plus grader workflow inside containers.

The non-negotiable conventions are:

- EVMBench must be able to start one task container per audit, and optionally a sidecar container for exploit mode.
- EVMBench must be able to execute shell commands in the main container.
- EVMBench must be able to upload and download small files and directories.
- In exploit mode, EVMBench may need to discover the sidecar hostname and run/upload/download inside that sidecar.
- Audit images are the unit of execution. Locally they default to `evmbench/audit:<audit_id>`.
- For remote fleets, image lookup comes from `EVMBENCH_AUDIT_IMAGE_REPO`, producing `<repo>:<audit_id>`.
- Agent integration is file-based. EVMBench resolves an agent from `evmbench/agents/*/config.yaml` and expects:
  - a `start.sh`
  - an instruction filename
  - optional env vars
  - optional `gateway_sni_hosts`

Relevant sources:

- `evmBench-frontier-evals/project/evmbench/docs/scale.md`
- `evmBench-frontier-evals/project/evmbench/evmbench/audit.py`
- `evmBench-frontier-evals/project/evmbench/evmbench/agents/agent.py`
- `evmBench-frontier-evals/project/evmbench/evmbench/nano/runtime.py`

## Correct EVMBench-Side Abstraction

From the benchmark's point of view:

- `Computer backend` = how containers, shell commands, and file transfer happen
- `Audit image` = the runtime filesystem and installed tools
- `Agent adapter` = `config.yaml` plus `start.sh`
- `Solver/task` = orchestration only

This means EVMBench should not care that Yudai is implemented using mini-swe-agent.
From inside EVMBench, Yudai should look like any other agent adapter.

## What This Implies For Yudai

The benchmark-side rule is:

- EVMBench owns container lifecycle, audit images, grading, RPC sidecar wiring, and prompt injection.
- Yudai owns only its launcher and internal runtime.
- Tool availability belongs in the audit image lineage, not in `LocalEnvironment`, not in the solver, and not in any `benchmark.csv` workspace flow.

If the task container has `forge`, `cast`, `slither`, `aderyn`, and related tools installed, Yudai can use them.
If the task container does not have them, the image must be fixed. The environment class is not the correct place to solve that.

## Benchmark-First Target Design

The clean native architecture should be:

1. `evmbench/base` is the benchmark runtime base image.
2. `evmbench/audit:<audit_id>` inherits from `evmbench/base`.
3. `evmbench/base` may itself inherit from a reusable Yudai toolchain image, but that is an implementation detail.
4. The Yudai adapter inside `evmbench/agents/yudai/` should stay small:
   - `config.yaml`
   - `start.sh`
   - optionally one benchmark-specific Python entrypoint
5. The solver should pass dynamic env directly to the launched agent process instead of rewriting scripts when possible.
6. EVMBench should never recreate the older `benchmark.csv` workspace model for audit tasks. The audit image is already the workspace.

## What Must Stay Stable

Any redesign inside `evmBench-frontier-evals/project/evmbench/evmbench` must preserve:

- agent discovery via `evmbench/agents/<agent>/config.yaml`
- agent launch via `start.sh`
- audit image lookup via `Audit.docker_image`
- runtime dependence only on the `Computer API` from `scale.md`
- exploit sidecar routing remaining a solver/task concern
- the agent operating on the prepared audit filesystem rather than constructing a second synthetic workspace

## Step 2: Current Yudai Integration vs Benchmark Invariants

### What already matches EVMBench

- The audit image is still the unit of execution, which matches `scale.md`.
- The agent is still integrated through the expected EVMBench adapter shape:
  - `evmbench/agents/yudai/config.yaml`
  - `evmbench/agents/yudai/start.sh`
- Exploit-side RPC routing is still benchmark-owned.
  - Solver/task computes sidecar host and port.
  - The agent only consumes the resulting environment and instructions.

### Where the current integration leaks abstractions

- `yudai-detect`, `yudai-patch`, and `yudai-exploit` are modeled as separate agents.
  - This is not benchmark-native. Mode is benchmark state, not agent identity.
- The real Yudai runtime and prompt logic live outside `evmbench/`.
  - EVMBench currently depends on out-of-tree staging and vendoring instead of a self-contained benchmark-side adapter.
- `start.sh` mutates vendored Python files at container startup.
  - This is not clean, scale-friendly, or easy to extend.
- Toolchain ownership is split awkwardly across:
  - `yudai-base`
  - `evmbench/Dockerfile.yudai`
  - repo-root build helpers
- Prompt/config ownership is split between:
  - benchmark-side outer config in `evmbench/agents/yudai/`
  - repo-root inner config in `src/minisweagent/config/extra/evmbench.yaml`
- The build flow is orchestrated from the main repo side rather than from the EVMBench repo side.

### Step 2 conclusion

The runtime contract is mostly correct, but the Yudai adapter is not benchmark-native yet.
It still behaves like an external runtime being injected into EVMBench instead of an EVMBench-owned agent adapter with a clean internal boundary.

## Step 3: Benchmark-Side Redesign Proposal

### Design goals

- Keep EVMBench benchmark-owned and agent-agnostic.
- Make Yudai a first-class EVMBench agent adapter.
- Keep audit workspaces benchmark-native.
- Move agent-specific orchestration into `evmbench/`.
- Make toolchain composition explicit and extensible.
- Preserve the `scale.md` backend contract unchanged.

### Key redesign decision

Do not make `evmbench/base:latest` implicitly Yudai-specific.

Instead, EVMBench should support agent-flavored base images and audit-image variants.
This keeps the benchmark generic while still letting Yudai runs inherit the full Yudai toolchain.

### Proposed image model

- `evmbench/base:latest`
  - generic benchmark base
  - minimal benchmark-owned runtime
- `evmbench/base-yudai:latest`
  - Yudai-specific benchmark base
  - inherits from a reusable Yudai toolchain image
  - adds EVMBench-specific pieces such as `ploit`, `veto`, workspace dirs, and the Yudai runtime
- `evmbench/audit:<audit_id>`
  - generic audit images
- `evmbench-yudai/audit:<audit_id>`
  - Yudai-flavored audit images built from `evmbench/base-yudai:latest`

This keeps Yudai toolchain evolution separate from the benchmark's default base image.

### Proposed Docker convention

Audit Dockerfiles should be normalized to:

- `ARG EVMBENCH_BASE_IMAGE=evmbench/base:latest`
- `FROM ${EVMBENCH_BASE_IMAGE}`

This lets EVMBench build multiple audit-image families cleanly without rewriting solver logic.

### Proposed Yudai adapter layout inside EVMBench

- `evmbench/agents/yudai/config.yaml`
  - one logical agent family
  - profiles by provider/model if needed
  - not split by detect/patch/exploit
- `evmbench/agents/yudai/start.sh`
  - minimal launcher only
  - no hotpatching of vendored files
- `evmbench/agents/yudai/entrypoint.py`
  - benchmark-native Python entrypoint
  - consumes EVMBench instructions + environment
  - launches the Yudai runtime
- `evmbench/agents/yudai/runtime.yaml`
  - inner Yudai behavior config for EVMBench tasks
- `evmbench/vendor/yudai_runtime/`
  - optional vendored local runtime snapshot for development builds

### Proposed ownership split

- EVMBench owns:
  - audit images
  - base-image variants
  - sidecar/RPC wiring
  - agent adapter discovery
  - benchmark instructions
- Yudai adapter inside EVMBench owns:
  - benchmark-native launcher
  - mode-aware supplements
  - inner runtime config
- Reusable Yudai toolchain image owns:
  - `forge`
  - `cast`
  - `anvil`
  - `slither`
  - `aderyn`
  - `myth`
  - `echidna`
  - any CLI dependencies Yudai expects

### Mode handling

Mode should come from EVMBench state, not from agent identity.

That means:

- remove `yudai-detect`, `yudai-patch`, `yudai-exploit` as separate agent ids
- keep a single `yudai-*` family
- pass mode via:
  - EVMBench instruction text
  - explicit env if useful
  - optional CLI arg into the Yudai entrypoint

### RPC handling

Exploit RPC should remain entirely benchmark-owned.

The clean contract is:

- solver/task computes RPC host and port
- solver launches the agent with `RPC_URL` and related env vars
- Yudai consumes those env vars directly
- no generated wrapper script should be needed

### Development workflow from the EVMBench side

If Yudai is being iterated locally, EVMBench should own the sync/build hook.

Recommended approach:

- add a benchmark-side script such as `scripts/sync_yudai_runtime.py`
- that script stages a local Yudai runtime into `evmbench/vendor/yudai_runtime`
- `docker_build.py` or a small companion builder can then build:
  - `evmbench/base-yudai:latest`
  - `evmbench-yudai/audit:<audit_id>`

This keeps the development flow rooted in EVMBench instead of the repo root.

### Native verification strategy

The benchmark-side verification path should also live in EVMBench.

Recommended checks:

- build Yudai-flavored audit images from inside EVMBench
- run a one-audit detect / patch / exploit eval via `evmbench.nano.entrypoint`
- extend `scripts/smoke_test_agent_clis.py` to include Yudai
  - this validates that the agent launcher works under EVMBench networking conventions
  - this keeps verification benchmark-native instead of depending on repo-root harnesses

### Step 3 conclusion

The benchmark-side redesign should make Yudai a native EVMBench agent family with:

- one logical agent identity
- benchmark-owned mode and RPC handling
- benchmark-side build and verification hooks
- explicit agent-flavored audit-image families
- no dependence on `benchmark.csv` workspace construction

## Step 4: Concrete Implementation Plan Inside `evmbench/`

This step is still design and planning only.
The goal is to define the exact benchmark-side change set before touching the EVMBench runtime again.

### Phase A: Normalize the image model

Problem:

- Audit Dockerfiles currently hardcode a mix of:
  - `FROM evmbench/base`
  - `FROM evmbench/base:latest`
- This prevents clean agent-flavored audit-image families.

Required change:

- Update every audit Dockerfile in `audits/*/Dockerfile` to use:
  - `ARG EVMBENCH_BASE_IMAGE=evmbench/base:latest`
  - `FROM ${EVMBENCH_BASE_IMAGE}`

Files:

- `evmBench-frontier-evals/project/evmbench/audits/*/Dockerfile`
- `evmBench-frontier-evals/project/evmbench/audits/template/Dockerfile`

Outcome:

- Any audit can be rebuilt against:
  - generic benchmark base
  - Yudai-flavored benchmark base
  - future agent-flavored bases

### Phase B: Create explicit benchmark base variants

Problem:

- `evmbench/base` is currently being overloaded with Yudai-specific runtime concerns.

Required change:

- Keep `evmbench/Dockerfile` as the generic benchmark base.
- Add a new `evmbench/Dockerfile.yudai-base`.
- `Dockerfile.yudai-base` should:
  - inherit from a reusable Yudai toolchain image or install the same toolchain directly
  - install benchmark-specific binaries:
    - `ploit`
    - `veto`
  - create benchmark workspace dirs:
    - `/home/agent`
    - `/home/agent/audit`
    - `/home/agent/submission`
    - `/home/logs`
  - install only the dependencies needed for the Yudai EVMBench adapter
  - avoid runtime hotpatching in `start.sh`

Files:

- `evmBench-frontier-evals/project/evmbench/evmbench/Dockerfile`
- `evmBench-frontier-evals/project/evmbench/evmbench/Dockerfile.yudai-base` (new)

Outcome:

- `evmbench/base:latest` stays benchmark-generic.
- `evmbench/base-yudai:latest` becomes the explicit Yudai benchmark base.

### Phase C: Extend the EVMBench builder for image families

Problem:

- `docker_build.py` currently only knows one base image and one audit tag family.

Required change:

- Extend `docker_build.py` with explicit base-image controls:
  - `--base-tag evmbench/base:latest`
  - `--base-dockerfile evmbench/Dockerfile`
  - `--audit-tag-prefix evmbench/audit`
  - `--build-family generic|yudai`
- For the Yudai family, the builder should produce:
  - `evmbench/base-yudai:latest`
  - `evmbench-yudai/audit:<audit_id>`
- During audit builds, pass a build arg:
  - `--build-arg EVMBENCH_BASE_IMAGE=<selected_base_tag>`

Files:

- `evmBench-frontier-evals/project/evmbench/docker_build.py`

Outcome:

- EVMBench can build and publish multiple audit-image families without changing solver logic.

### Phase D: Make Yudai a native EVMBench agent adapter

Problem:

- The current Yudai adapter depends on out-of-tree runtime staging and splits mode into separate agent ids.

Required change:

- Keep one logical Yudai family in `evmbench/agents/yudai/config.yaml`.
- Remove mode-specific agent ids as the main path.
- Keep model/provider variants if useful, but not detect/patch/exploit variants.
- Add a benchmark-native entrypoint under `evmbench/agents/yudai/`, for example:
  - `entrypoint.py`
  - `runtime.yaml`
- `start.sh` should become a thin launcher:
  - validate env
  - log tool availability and RPC env
  - exec the Yudai benchmark-native entrypoint
- The benchmark-native entrypoint should:
  - read `AGENTS.md`
  - infer or accept EVMBench mode
  - append benchmark-specific mode supplements
  - launch the Yudai runtime

Files:

- `evmBench-frontier-evals/project/evmbench/evmbench/agents/yudai/config.yaml`
- `evmBench-frontier-evals/project/evmbench/evmbench/agents/yudai/start.sh`
- `evmBench-frontier-evals/project/evmbench/evmbench/agents/yudai/entrypoint.py` (new)
- `evmBench-frontier-evals/project/evmbench/evmbench/agents/yudai/runtime.yaml` (new)

Outcome:

- From EVMBench’s point of view, Yudai is now a self-contained agent adapter.

### Phase E: Keep solver/task benchmark-owned and generic

Problem:

- Mode and RPC should stay benchmark-owned.
- The solver should not need Yudai-specific branching beyond the normal agent adapter contract.

Required change:

- Keep mode in EVMBench state:
  - `evmbench.mode`
- Keep exploit RPC override in solver/task.
- Keep sidecar discovery and veto wiring in `nano/task.py` and `nano/solver.py`.
- Solver may pass launch env directly to the process, but should not rewrite Yudai-specific script structure.

Files:

- `evmBench-frontier-evals/project/evmbench/evmbench/nano/solver.py`
- `evmBench-frontier-evals/project/evmbench/evmbench/nano/task.py`
- `evmBench-frontier-evals/project/evmbench/evmbench/agents/run.py`

Outcome:

- The benchmark remains agent-agnostic.
- Yudai remains a normal EVMBench agent from the solver’s perspective.

### Phase F: Add a benchmark-owned Yudai runtime sync hook

Problem:

- Local Yudai iteration should be possible, but the control point should live in EVMBench if we are redesigning from the benchmark side.

Required change:

- Add a benchmark-side script such as:
  - `scripts/sync_yudai_runtime.py`
- It should stage local Yudai runtime code into:
  - `evmbench/vendor/yudai_runtime`
- This script should be optional and clearly marked as a local-development path.
- Production or scale builds should be able to work from:
  - vendored runtime snapshot
  - packaged runtime artifact
  - prebuilt image

Files:

- `evmBench-frontier-evals/project/evmbench/scripts/sync_yudai_runtime.py` (new)
- `evmBench-frontier-evals/project/evmbench/evmbench/vendor/yudai_runtime/`

Outcome:

- Local iteration is still possible without making the benchmark depend on repo-root orchestration.

### Phase G: Add benchmark-native verification

Problem:

- Verification currently happens partly outside EVMBench.

Required change:

- Extend `scripts/smoke_test_agent_clis.py` to include Yudai.
- Add support for selecting the Yudai audit-image family for smoke tests.
- Add one documented end-to-end command per mode:
  - detect
  - patch
  - exploit
- Verification should prove:
  - the Yudai launcher works
  - the audit image contains the required tools
  - exploit mode sees the benchmark-provided RPC env

Files:

- `evmBench-frontier-evals/project/evmbench/scripts/smoke_test_agent_clis.py`
- `evmBench-frontier-evals/project/evmbench/README.md`

Outcome:

- All core verification happens from the benchmark side.

### Recommended implementation order

1. Normalize audit Dockerfiles to use `ARG EVMBENCH_BASE_IMAGE`.
2. Add `Dockerfile.yudai-base`.
3. Extend `docker_build.py` for image families and build args.
4. Refactor the Yudai adapter into one logical agent family.
5. Add benchmark-side runtime sync hook.
6. Extend smoke tests and README verification commands.
7. Only then simplify or remove any repo-root helper paths that become obsolete.

### Acceptance criteria for the redesign

- EVMBench can build both generic and Yudai-flavored audit-image families.
- Yudai runs from a self-contained adapter inside `evmbench/agents/yudai/`.
- Yudai can use `forge`, `cast`, `slither`, `aderyn`, and related tools directly inside audit tasks.
- Yudai exploit runs can consume benchmark-provided RPC env from the sidecar path.
- No `benchmark.csv` workspace construction is involved in EVMBench-native runs.
- Benchmark-side smoke tests can validate the Yudai adapter without repo-root orchestration.
