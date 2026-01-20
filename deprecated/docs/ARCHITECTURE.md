# YudaiV4 Architecture and Task Unification

> Consolidated from `compass_artifact_wf-2fdf31b7-0548-4f5e-bd00-ddaaf80202c6_text_markdown.md`
> and recent codebase commits (Jan 2026).

## Executive Summary

YudaiV4 is an AI coding agent that teaches developers to find, understand, and fix smart contract vulnerabilities. It targets a market where only 8 percent of real-world attacks are prevented by existing tools and where logic-related vulnerabilities remain largely undetected. The product unifies education, auditing, and safe exploit simulation into a single pipeline built on mini-swe-agent, Foundry, and Base mini-app distribution.

## 1. Current Codebase Reality (Commit-Backed)

Recent commits implement the foundation layer required for a Foundry-driven agent:

- Unified Docker image with Foundry + security tooling in `docker/Dockerfile.yudai`.
- Foundry execution environment and orchestration in `src/minisweagent/environments/foundry.py`.
- Agent config templates for development and auditing in `src/minisweagent/config/foundry.yaml` and `src/minisweagent/config/security.yaml`.
- Foundry environment registry in `src/minisweagent/environments/__init__.py`.

These pieces establish a working execution substrate but do not yet wire in Base mini-app UI, GitHub integration, or the educational modules.

## 2. Architecture Overview

```
+-------------------------------------------------------------------+
|                          Product Surfaces                          |
|   Base Mini-App UI     GitHub PR Bot/CI     CLI (mini -c foundry)  |
+-------------------------+-------------------+----------------------+
|                         AI Agent Layer                           |
|  - DefaultAgent, InteractiveAgent                                  |
|  - Config templates (foundry.yaml, security.yaml)                  |
+-------------------------+-------------------+----------------------+
|                     Execution Environment                          |
|  FoundryEnvironment (Docker) + Anvil orchestration                 |
+-------------------------------------------------------------------+
|                           Toolchain                                |
|  Forge / Cast / Anvil / Chisel  +  Slither / Aderyn / Mythril /     |
|  Echidna / solc-select                                            |
+-------------------------------------------------------------------+
|                       Knowledge & Checks                           |
|  EIP checklists, Uniswap V4 hooks, DeFi patterns, MEV patterns     |
+-------------------------------------------------------------------+
```

## 3. Task Unification Model

All YudaiV4 experiences map to a shared set of task primitives. This keeps the agent behavior consistent whether the entry point is a mini-app, CLI, or GitHub PR.

### 3.1 Task Primitives

1. Discover context (read docs, configs, diffs).
2. Generate or modify contracts/tests/scripts.
3. Compile and test (Forge).
4. Analyze (Slither, Aderyn, Mythril, Echidna).
5. Simulate and validate (Anvil fork + Cast traces).
6. Explain and teach (plain-English reasoning).
7. Report and recommend (fixes, severity, remediation).
8. Share and distribute (casts, PR comments, badges).

### 3.2 Unified Experience Map

| Experience | Trigger | Core Primitives | Execution | Outputs |
| --- | --- | --- | --- | --- |
| Learning module | Mini-app lesson | 1,2,3,5,6 | Foundry + Anvil | Exploit result + fix quiz |
| Audit session | CLI task | 1,3,4,6,7 | Foundry + Sec tools | Audit report + fixes |
| PR review | GitHub webhook | 1,3,4,7 | Foundry + Sec tools | Inline PR comments + score |
| Research sandbox | CLI or internal | 1,2,5,6 | Chisel + Anvil | Notes + reproducible script |

This unification is the key architectural decision: all workflows are different surface layers over the same execution pipeline.

## 4. End-to-End Flows

### 4.1 Interactive Vulnerability Learning

```
User selects module
  -> Agent generates vulnerable contract and test scaffold
  -> Forge compile/test
  -> Anvil fork + exploit simulation
  -> Agent explains root cause and defense
  -> User answers quiz / re-run with fix
```

### 4.2 AI-Augmented Audit

```
Project docs + contracts
  -> Forge compile
  -> Slither + Aderyn + Mythril + Echidna
  -> AI logic review with EIP and protocol checklists
  -> Severity report + patch recommendations
```

### 4.3 GitHub PR Security Review

```
PR opened
  -> Diff-aware scan
  -> Targeted tooling run
  -> Inline comments with evidence
  -> Security score update
```

### 4.4 Base Mini-App Distribution

```
MiniKit app load
  -> sdk.actions.ready()
  -> wallet connect + Farcaster auth
  -> Module selection
  -> Task run via agent backend
  -> Share result via cast
```

## 5. Execution Environment and Toolchain

### 5.1 Docker Image

`docker/Dockerfile.yudai` installs:
- Foundry tools: `forge`, `cast`, `anvil`, `chisel`
- Security tools: `slither`, `aderyn`, `mythril`, `echidna-test`
- Compiler: `solc 0.8.24` via `solc-select`

### 5.2 FoundryEnvironment

`src/minisweagent/environments/foundry.py` provides:
- Docker container orchestration
- Project volume mounts
- Anvil lifecycle helpers
- Environment variables forwarding

### 5.3 Agent Configs

- `src/minisweagent/config/foundry.yaml`: build/test scripts, Foundry-first workflow.
- `src/minisweagent/config/security.yaml`: audit workflow and security tooling commands.

These config templates encode the behavior of the agent in each workflow while keeping execution consistent.

## 6. Security Knowledge Domain (Checks to Encode)

### 6.1 EIP Checklist

- EIP-4626: protect against inflation attacks (virtual offsets, round-down issuance).
- EIP-2612: prevent permit replay (chainId in domain separator, nonce checks).
- EIP-3156: verify flash loan callback return value.
- EIP-712: dynamic chainId handling and safe typed data encoding.

### 6.2 Uniswap V4 Hooks

Key risks for hook-based pools:
- Missing `onlyPoolManager` access control.
- Delta sign errors (negative means hook receives tokens).
- Unsettled deltas before `unlock()`.
- Hook address permission bits (CREATE2 mining required).

### 6.3 Protocol Patterns to Teach

- Aave/Compound liquidity models and oracle manipulation.
- Curve StableSwap invariant and LLAMMA liquidation.
- Access control and logic error patterns (largest losses in 2024).

### 6.4 MEV-Aware Design

- Commit-reveal, batch auctions, slippage guards.
- Flash loan governance defenses (token holding > 1 block).
- Use private relays for safe bundle testing.

## 7. Distribution and Identity

Base mini-app integration should follow:
- Install `@coinbase/onchainkit`.
- Call `sdk.actions.ready()` to hide splash.
- Serve `/.well-known/farcaster.json` manifest.
- Wallet auth via `<ConnectWallet>` for in-app smart wallet.
- Use `useAuthenticate()` for trusted Farcaster identity.
- Treat `useMiniKit()` context as untrusted metadata.

## 8. Safety and Trust Boundaries

Non-negotiable constraints:
- All exploits run on Anvil forks or local testnets.
- No mainnet or production signing in the agent flow.
- Confirm-mode command execution for safety (as configured).
- Wallet auth is for UX, Farcaster auth for identity verification.

## 9. Roadmap and Unified Task Backlog

### Phase 1: Foundation (Done)
- Docker image with Foundry + security tooling.
- FoundryEnvironment orchestration.
- Foundry and security agent configs.

### Phase 2: Core Learning and Audit
- Vulnerability sandbox generator (module templates).
- Exploit validation harness.
- Defense pattern database.
- Multi-tool finding synthesizer.
- Invariant generator for fuzzing.

### Phase 3: GitHub Integration
- Webhook handler and PR comment bot.
- Diff-aware targeted scans.
- Security score tracking.
- Solodit cross-references.

### Phase 4: Distribution
- Base mini-app frontend.
- OnchainKit wallet flow and Farcaster auth.
- Cast sharing and viral loop.
- Paymaster gas sponsorship.

## 10. File Map

```
docs/ARCHITECTURE.md
compass_artifact_wf-2fdf31b7-0548-4f5e-bd00-ddaaf80202c6_text_markdown.md
docker/Dockerfile.yudai
src/minisweagent/environments/foundry.py
src/minisweagent/environments/__init__.py
src/minisweagent/config/foundry.yaml
src/minisweagent/config/security.yaml
```

## 11. References

- Foundry Book: https://book.getfoundry.sh
- Base mini-app docs: https://docs.base.org/buildwithbase/mini-apps/
- OnchainKit: https://onchainkit.xyz
- Slither: https://github.com/crytic/slither
