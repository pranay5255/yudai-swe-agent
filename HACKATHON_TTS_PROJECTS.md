# Hackathon Project Ideas for Codex + EVMBench Test-Time Scaling

This note turns the current repo context into five concrete hackathon project ideas. The common architecture across all of them is:

- `mini-swe-agent` is the orchestrator and budget controller.
- Native EVMBench Codex workers do the actual task execution.
- EVMBench grading stays unchanged, so the project still emits the same benchmark artifacts.

## Ground Truth From This Repo

- The current EVMBench bridge already exists in [evmbench.py](/home/pranay5255/Documents/yudai-swe-agent/src/minisweagent/run/extra/evmbench.py:19). It maps benchmark modes to agent IDs and launches the native EVMBench entrypoint.
- The current mini-swe-agent loop is simple and linear in [default.py](/home/pranay5255/Documents/yudai-swe-agent/src/minisweagent/agents/default.py:54). That means the right place for test-time scaling is above `DefaultAgent.run(...)`, not inside the low-level loop.
- The EVMBench container entrypoint already builds a mode-specific task and appends mode supplements in [evmbench_agent.py](/home/pranay5255/Documents/yudai-swe-agent/src/minisweagent/run/extra/evmbench_agent.py:28).
- Native Codex EVMBench workers already exist in [config.yaml](/home/pranay5255/Documents/yudai-swe-agent/evmBench-frontier-evals/project/evmbench/evmbench/agents/codex/config.yaml:6) and are launched by [start.sh](/home/pranay5255/Documents/yudai-swe-agent/evmBench-frontier-evals/project/evmbench/evmbench/agents/codex/start.sh:13).
- Instruction assembly and hint injection already happen in [agent.py](/home/pranay5255/Documents/yudai-swe-agent/evmBench-frontier-evals/project/evmbench/evmbench/agents/agent.py:93). Your orchestrator should vary prompts by adding branch-specific supplements before the run, not by rewriting the grader.
- Exploit mode already has strong verifier signals in [exploit_environment_v3.py](/home/pranay5255/Documents/yudai-swe-agent/src/minisweagent/environments/exploit_environment_v3.py:45): `execution_traces` and `get_balance_ether(...)`.
- The older exploit harness already has early failure detection in [benchmark_episode.py](/home/pranay5255/Documents/yudai-swe-agent/exploit_generation/benchmark_episode.py:47).
- EVMBench already has `best@k`, `oracle best@k`, and `pass@k` utilities in [stats.py](/home/pranay5255/Documents/yudai-swe-agent/evmBench-frontier-evals/project/evmbench/scripts/stats.py:793). That is perfect for a TTS evaluation story.

## Paper Map

The `relevant_papers` directory contains HTML redirect stubs rather than the full PDFs, but the targets are recoverable:

- [Tree of Thoughts: Deliberate Problem Solving with Large Language Models](https://arxiv.org/abs/2305.10601)
- [Forest-of-Thought: Scaling Test-Time Compute for Enhancing LLM Reasoning](https://arxiv.org/abs/2412.09078)
- [S*: Test Time Scaling for Code Generation](https://arxiv.org/abs/2502.14382)
- [ACTS: Adaptive Control for Test-time Scaling](https://openreview.net/forum?id=GXbTHRBSA4)
- [Scaling Laws for Neural Language Models](https://arxiv.org/abs/2001.08361)

### 1. Tree of Thoughts

Core idea:

- Expand multiple candidate reasoning paths.
- Evaluate intermediate states.
- Backtrack when a path looks weak.

How it maps to EVMBench:

- A "thought" becomes a vulnerability hypothesis or audit subproblem, not a token span.
- For detect, each branch can start from a different audit surface:
  - entry contracts
  - external calls and cross-contract edges
  - token transfer and approval flows
  - accounting and reward math
  - ownership and privileged paths
- The orchestrator can run 3 to 5 Codex workers, score their partial findings, then continue only the strongest branches.

Best orchestrator shape:

- Host-level controller in a new file such as `src/minisweagent/run/extra/tts_detect.py`.
- Each branch invokes the same EVMBench Codex worker, but with a different branch supplement prepended to the instructions loaded by [agent.py](/home/pranay5255/Documents/yudai-swe-agent/evmBench-frontier-evals/project/evmbench/evmbench/agents/agent.py:93).
- Judge branch quality with simple signals:
  - mentions concrete function names
  - cites files or line references
  - includes exploitability or loss-of-funds reasoning
  - produces non-duplicate findings

Compute allocation:

- Start with 3 branches.
- After 8 to 12 steps, prune the bottom branch by specificity and novelty.
- Reinvest its remaining budget into the top 2.

### 2. Forest-of-Thought

Core idea:

- Run multiple trees, not just one tree.
- Use sparse activation so only relevant trees wake up.
- Use consensus and self-correction to converge.

How it maps to EVMBench:

- Instead of one set of generic branches, run specialist trees:
  - token-flow tree
  - accounting and share-price tree
  - access-control tree
  - cross-contract / integration tree
  - exploitability / concrete-loss tree
- Activate only the trees that fit the audit. For example, if the repo has no ERC20 transfers, skip the token-flow tree.

Best orchestrator shape:

- A `forest_controller` does a cheap scout pass:
  - count contracts
  - count external calls
  - detect ERC20/ERC4626/ERC721 usage
  - detect upgradeability / proxy patterns
- Based on that scout, activate 2 to 4 specialist trees.
- Each tree runs 2 small Codex branches, then a tree-local judge summarizes.
- A global merge judge produces the final `submission/audit.md`.

Compute allocation:

- Sparse activation is the key. Do not always spawn every tree.
- Spend 20% of the total budget on the scout and routing decision.
- Spend 60% on active tree workers.
- Spend 20% on consensus, merge, and self-correction.

Why this is strong for EVMBench:

- Your EDA already showed EVMBench is dominated by token/accounting/access-control style bugs more than just classic reentrancy. A specialist forest is better aligned with the actual benchmark mix than a generic single-agent run.

### 3. S*

Core idea:

- Mix parallel generation with sequential improvement.
- Use execution-grounded or test-grounded selection, not only a language-model judge.
- Compare candidates using distinguishing feedback.

How it maps to EVMBench:

- This is the best paper for `exploit` and `patch`.
- For exploit:
  - generate multiple `Strategy.sol` or transaction-plan candidates in parallel
  - replay them
  - keep the candidates that actually change balances or get deeper into the exploit trace
- For patch:
  - generate multiple diffs
  - run tests
  - keep only candidates that preserve behavior and block the vulnerability

Best orchestrator shape:

- `mini-swe-agent` spawns `k` Codex exploit or patch workers.
- After the first round, the controller scores them with execution signals:
  - `execution_traces[-1]` in [exploit_environment_v3.py](/home/pranay5255/Documents/yudai-swe-agent/src/minisweagent/environments/exploit_environment_v3.py:60)
  - balance delta from `get_balance_ether(...)`
  - compile success
  - vulnerability-specific test pass/fail
- Then the controller runs a second sequential round only for the top candidates, feeding back the concrete failure signal.

Compute allocation:

- Parallel round: 4 cheap branches.
- Sequential round: keep top 2.
- Final round: keep top 1 for full budget.

Why this is strong for your repo:

- The repo already has failure-aware exploit logic in [benchmark_episode.py](/home/pranay5255/Documents/yudai-swe-agent/exploit_generation/benchmark_episode.py:79). S* is basically the cleanest theory-backed way to productize that idea.

### 4. ACTS

Core idea:

- Use a stopping policy to decide when to keep thinking and when to stop.
- Use a learned or signal-driven controller to avoid wasting compute.

Important constraint in this repo:

- The local TTS plan already notes that true ACTS needs token-level signals or logprobs, which the current model layer does not expose practically yet.
- So the right hackathon interpretation is approximate ACTS, not full ACTS.

How it maps to EVMBench:

- Replace token-level termination signals with branch-level progress signals:
  - repeated shell commands
  - repeated uncertainty language
  - no new findings for N steps
  - no balance improvement after exploit attempts
  - compile/test failure loops
  - repeated interaction with the same file without new evidence

Best orchestrator shape:

- Start with 3 branches.
- Every few steps, run a controller policy:
  - continue the branch
  - inject a critique message and let it retry
  - kill the branch and reallocate budget
  - fork a corrective branch from a stronger sibling

Compute allocation:

- Give every branch a small initial budget.
- Promote only branches with measurable progress.
- Reallocate dead-branch budget to surviving branches.

Hackathon value:

- This is a very good stretch feature layered on top of a simpler detect or exploit swarm.
- It is not the right first implementation, but it is a strong "we built an adaptive compute controller for Codex agents" demo line.

### 5. Scaling Laws

Core idea:

- Performance improves predictably with compute, but returns diminish.
- With a fixed budget, allocation matters as much as raw spending.

How it maps to EVMBench:

- This is not a direct branching method. It is the paper that justifies a scheduler.
- You should not spend the same budget on every audit or every branch.
- Use audit complexity to choose:
  - branch count
  - per-branch step limit
  - whether to escalate from detect to exploit or patch

Best orchestrator shape:

- A budget router computes an audit complexity score from:
  - number of Solidity files
  - total SLOC
  - number of external calls
  - number of protocols touched
  - whether a test suite exists
  - whether exploit artifacts exist
- Then it assigns a non-linear budget curve.

A practical schedule:

- small audit: 1 branch, short horizon
- medium audit: 2 to 3 branches, medium horizon
- large audit: 4 to 5 branches, long horizon, but only after the scout says there are multiple high-value surfaces

Good heuristic:

- `budget ~ base * complexity^alpha`, with `alpha` below 1 to reflect diminishing returns.
- In practice, a piecewise schedule is enough for the hackathon.

## Five Concrete Hackathon Projects

## Project 1: Codex Tree Detective

Best paper:

- Tree of Thoughts

What it is:

- A detect-only multi-branch auditor that explores multiple vulnerability hypotheses in parallel, prunes weak branches, and merges the best findings into one `audit.md`.

What you build:

- `tts_detect.py`
- 3 branch seeds
- branch scoring and pruning
- merged report writer
- best@k evaluation on a small audit subset

Why it fits the hackathon:

- Fastest path to a working demo.
- Very clear "was not possible without Codex" story: one orchestrator drives multiple Codex auditors in parallel.

Recommended compute policy:

- Start with 3 branches for every audit.
- If scout complexity is low, collapse to 1.
- If branch novelty stalls, prune and reinvest.

Best demo:

- One audit baseline vs one audit 3-branch run.
- Show higher finding coverage or a better EVMBench detect score.

## Project 2: Forest of Auditors

Best paper:

- Forest-of-Thought

What it is:

- A role-specialized swarm of Codex auditors, with sparse activation and consensus.

What you build:

- scout router
- 3 to 5 specialist trees
- local judge for each tree
- global merge judge

Why it fits the hackathon:

- Best story value.
- Strong multi-agent angle.
- Directly aligned with your long-term goal of detect-orchestrated TTS.

Recommended compute policy:

- Activate only relevant trees.
- Keep each tree shallow, but use more breadth where the scout sees multiple risky surfaces.

Best demo:

- Show tree activation changing between two audits.
- Show that the token/accounting tree catches issues a generic branch missed.

## Project 3: S* Exploit Tournament

Best paper:

- S*

What it is:

- A tournament for exploit or patch candidates where Codex workers generate candidates, the environment verifies them, and only the best candidates get more budget.

What you build:

- exploit branch fan-out
- score using execution traces and balance changes
- second-round refinement for top candidates
- optional patch variant using test-driven selection

Why it fits the hackathon:

- Flashiest verifier-based demo.
- Excellent for showing real test-time scaling instead of just "parallel prompting."

Recommended compute policy:

- 4 cheap candidates
- top 2 survive
- top 1 gets final refinement budget

Best demo:

- Show four candidate exploit traces.
- Show the controller selecting the one that actually moves funds or gets closest.

## Project 4: Adaptive EVM Swarm

Best paper:

- ACTS

What it is:

- An adaptive controller that watches progress signals and decides whether to continue, critique, fork, or stop each Codex branch.

What you build:

- branch health monitor
- stall detector
- critique injector
- budget reallocator

Why it fits the hackathon:

- Strong research flavor.
- Strong "compute allocation" story.
- Best as a layer on top of Project 1 or 3, not standalone.

Recommended compute policy:

- small initial branch budgets
- promote by progress
- cut dead branches aggressively

Best demo:

- Show a stuck branch getting killed while its budget moves to a promising sibling.

## Project 5: Audit Budget Router

Best paper:

- Scaling Laws for Neural Language Models

What it is:

- A fixed-budget scheduler for EVMBench that chooses how many Codex workers to spawn and how long to run them based on audit complexity and diminishing returns.

What you build:

- static audit complexity scorer
- branch count policy
- step-limit policy
- small evaluation showing better score-per-dollar or score-per-minute

Why it fits the hackathon:

- Lowest engineering risk after Project 1.
- Easy to measure.
- Turns the scaling-law intuition into a very practical benchmark scheduler.

Recommended compute policy:

- complexity bucket -> branch count and step limit
- optionally choose detect-only vs detect+exploit escalation

Best demo:

- Show two audits with different complexity scores receiving different budgets.
- Show same total budget, but better results than uniform allocation.

## What I Would Actually Build In 6.5 Hours

If you want the best balance of hackathon viability and long-term value, build this stack:

1. Start with Project 1 as the minimum shippable core.
2. Add the sparse activation idea from Project 2.
3. Add one S*-style verifier loop only if time remains.
4. Add ACTS-style adaptive stopping only as a stretch layer.

That becomes a single strong project:

- `codex-evm-swarm`
- `mini-swe-agent` orchestrator
- native EVMBench Codex workers
- detect-first TTS with role-specialized branching
- optional exploit verification for the top finding

That is the project most aligned with your repo objectives:

- improve EVMBench through test-time scaling
- do multi-agent detect/patch/exploit orchestration
- keep the work publishable as a new repo forked from `mini-swe-agent`

## Best Recommendation

If you only pick one idea, pick `Forest of Auditors`.

Why:

- it is more distinctive than a plain ToT runner,
- it still fits your detect-first roadmap,
- it naturally showcases multi-agent Codex orchestration,
- and it lets you reuse the exact EVMBench artifact contract without touching the graders.
