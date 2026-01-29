# Terminal UI Plan (Foundry/Slither Exploit Runner)

## Chosen library
- **Textual** for the TUI (already in dependencies, full-screen layouts, mouse support, rich widgets, async-friendly).
- **Typer** for the CLI entrypoint and flags (already in dependencies).
- **Rich** for non-TUI output and fallback logs.

---

## Step-by-step plan with questions

### 1) Scope the user journeys and CLI modes
**Task**: Define the two primary flows and how the user toggles between them.
- Flow A: Benchmark runs (`scripts/run_benchmark_exploit.py`).
- Flow B: Single local episode (`scripts/run_exploit_episode.py`).
- Decide between `--tui` mode (Textual) vs. `--no-tui` (existing CLI).

**Question**: Which initial flow should the TUI prioritize on launch? (single choice)
- [ ] Benchmark (benchmark.csv driven)
- [ ] Local episode (contract path driven)
- [ ] Always show a mode picker first

---

### 2) TUI information architecture + navigation map
**Task**: Sketch the screen hierarchy and navigation.
- Home / Mode Picker
- Setup / Environment (keys, RPCs, docker image, foundry/slither availability)
- Run Configuration (benchmark or local)
- Preflight (checks + optional agent actions)
- Execution (live logs, progress, abort)
- Results (summary + artifacts)

**Question**: Which navigation style do you want? (single choice)
- [ ] Stepper wizard (next/back)
- [ ] Sidebar tabs (jump between sections)
- [ ] Hybrid (wizard + quick jump)

---

### 3) Agent persona and interaction model
**Task**: Define the assistant persona voice, confirmation rules, and how it triggers Foundry/Slither actions.
- Persona: concise helper, asks permission before running commands unless "yolo" is set.
- Offer "Explain what I’m about to run" toggle.
- Provide a "Safe mode" with read-only commands.

**Question**: What level of autonomy should the terminal agent have by default? (single choice)
- [ ] Ask before every command
- [ ] Ask only for state-changing commands (cast send, forge script --broadcast)
- [ ] Always run without confirmation (yolo)

---

### 4) Benchmark flow form (based on `run_benchmark_exploit.py`)
**Task**: Build a form that captures all args and defaults.
- Case selection: index, case name, or filtered list from CSV.
- Filters: chain (mainnet/bsc/base), limit.
- Runtime: output dir, config, model, docker image, cost limit.
- Behavior: yolo, interactive, env file, cache dir, verbose.

**Question**: How should case selection work? (single choice)
- [ ] Search + select by case name
- [ ] Index selector (0-based)
- [ ] Filter by chain then multi-select cases

---

### 5) Local episode flow form (based on `run_exploit_episode.py`)
**Task**: Build a form for local contract runs.
- Contract path (required)
- Output dir, config path, model, image, cost limit
- yolo, interactive, env file
- Anvil settings (port, fork URL, block)

**Question**: Should the TUI include a contract file picker with preview? (single choice)
- [ ] Yes, show contract path + first 40 lines preview
- [ ] Yes, but no preview
- [ ] No, path input only

---

### 6) Environment + secrets setup screen
**Task**: Guide users through required env variables.
- `OPENROUTER_API_KEY`, `OPENROUTER_MODEL_NAME`
- Benchmark: `ETHERSCAN_API_KEY` optional, RPC URLs
- Local: `DEPLOYER_PRIVATE_KEY`/`PRIVATE_KEY`, `PLAYER_ADDRESS`, optional `PLAYER_BALANCE_*`
- Load `.env` and show missing keys

**Question**: How should secrets be handled in the TUI? (single choice)
- [ ] Read-only display of missing keys, user edits `.env` outside
- [ ] Inline editing with masked input
- [ ] Inline editing + save back to `.env`

---

### 7) Foundry/Slither preflight checks (agent helper)
**Task**: Create a preflight checklist the agent can execute.
- Detect tools: `forge`, `cast`, `anvil`, `slither`
- Validate RPC connectivity
- Check docker image availability
- For local episode: `forge build` and optional `slither .`

**Question**: Which preflight tasks should be auto-run by the agent? (multi-select)
- [ ] `forge --version`
- [ ] `slither --version`
- [ ] `forge build`
- [ ] `forge test`
- [ ] `slither . --json -`
- [ ] `cast chain-id --rpc-url ...`

---

### 8) Agent-driven Foundry/Slither helpers
**Task**: Add an "Agent Helper" panel with quick actions.
- "Run Slither and summarize findings"
- "Run forge build/test and report errors"
- "Start anvil fork with selected RPC"
- "Open last exploit result JSON"

**Question**: Which quick actions should appear by default? (multi-select)
- [ ] Slither summary
- [ ] Forge build
- [ ] Forge test
- [ ] Start anvil
- [ ] Open latest result/traj files

---

### 9) Execution screen for benchmark runs
**Task**: Show live progress + structured run summary.
- Current case, status, duration
- Last N log lines
- Buttons: pause/abort, open logs, copy result paths
- Update summary JSON and show aggregate stats

**Question**: Should logs stream in real-time or on-demand? (single choice)
- [ ] Real-time streaming (tail)
- [ ] On-demand refresh
- [ ] Both (toggle)

---

### 10) Execution screen for local episode
**Task**: Display episode ID, target contract, success, profit, output paths.
- Show parsed metrics and open result file
- Provide next-step shortcuts (rerun with tweaks)

**Question**: What should happen after an episode finishes? (single choice)
- [ ] Stay on results screen
- [ ] Return to config screen with previous values
- [ ] Ask to rerun with tweaks (cost limit, model, yolo)

---

### 11) Artifact explorer / history view
**Task**: Scan `exploit_results/` and show recent runs.
- Filter by run ID, case name, success
- Open `.traj.json` or `.result.json`

**Question**: Do you want a built-in viewer for JSON artifacts? (single choice)
- [ ] Yes, pretty-print in TUI
- [ ] No, open in external editor

---

### 12) Error handling + guardrails
**Task**: Define error states with recovery actions.
- Missing keys, missing model, missing contract, RPC failures
- Prompt with fix steps and retry

**Question**: Should the agent propose automatic fixes (e.g., create `.env` template)? (single choice)
- [ ] Yes, propose + apply
- [ ] Propose only
- [ ] No, just show instructions

---

### 13) CLI packaging plan (uv + PyPI)
**Task**: Define packaging questions and decisions before implementation.
- Determine package name, CLI command name, versioning strategy
- Decide whether to add a `project.scripts` entrypoint
- Decide whether to bundle Textual as optional or default dependency
- Define minimal supported Python versions

**Question**: What should the public CLI command be? (single choice)
- [ ] `yudai` (brand)
- [ ] `exploit-ui`
- [ ] `mini-exploit`
- [ ] Other (specify)

---

### 14) uv workflow and release checklist
**Task**: Plan the uv commands and metadata updates.
- `uv build`, `uv publish` flow
- README updates: install + usage + screenshots
- Confirm PyPI credentials and repository URL

**Question**: What release target do you want first? (single choice)
- [ ] TestPyPI
- [ ] PyPI
- [ ] Internal/private index

---

## Packaging questions to answer before publish
(These are needed to safely package as a CLI tool with uv.)

1. **Package identity**: What is the final package name, CLI command name, and short description?
2. **Entrypoints**: Do you want a dedicated command (e.g., `exploit-ui`) and should it default to TUI or accept `--tui/--no-tui`?
3. **Dependencies**: Should Textual be required or an optional extra (e.g., `mini-swe-agent[tui]`)?
4. **Python support**: Confirm minimum Python version (currently `>=3.10`).
5. **License**: Keep MIT or change?
6. **Distribution**: PyPI vs TestPyPI vs private; do you want signed releases?
7. **Versioning**: Manual version bump or auto (e.g., via git tags)?
8. **Docs**: Where should the usage docs live (README vs docs site)?
9. **Security**: Should we add warnings about private keys + safe mode defaults?
10. **Binary build**: Do you want a standalone binary later (e.g., via PyInstaller)?

---

## Notes from script study (for UI defaults)
- Benchmark script requires `OPENROUTER_API_KEY` and model (`OPENROUTER_MODEL_NAME` or `MSWEA_MODEL_NAME`).
- Local episode requires `OPENROUTER_API_KEY`, `OPENROUTER_MODEL_NAME`, `DEPLOYER_PRIVATE_KEY`/`PRIVATE_KEY`, and `PLAYER_ADDRESS`.
- Benchmark supports case selection by index or name, chain filters, limit, and caching sources.
- Local episode expects a contract path (default `contracts/SimpleBank.sol`).

