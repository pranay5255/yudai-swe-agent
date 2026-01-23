# 1. Persistent Data and Context in AI Interactions

## Anchor from the a16z crypto x AI text
- Generative AI needs persistent context; today context is not portable across sessions or platforms.
- Blockchains can store key context elements as portable assets and enforce interoperability.
- Onchain context enables marketplaces for prompts and knowledge modules while preserving data custody.

## Application using this repo's capability
### Primary application: "Audit Context Passport"
A portable, onchain "context capsule" that stores a protocol's security posture, invariants, previous findings, accepted risks, and preferred testing workflows. The capsule can be loaded by the mini-swe-agent / YudaiV4 security agent at the start of any audit or PR review, giving the agent immediate project awareness.

### Why this repo fits
- The repo already performs security workflows (compile, test, static analysis, fuzzing, simulation) using Foundry and common security tools.
- The agent can export structured outputs (findings, invariants, assumptions) and re-import them in later runs.
- Multiple surfaces exist (CLI, GitHub PR bot, mini-app), so portability across surfaces is immediately useful.

## Problem and opportunity
- Smart contract security work is context-heavy: invariant assumptions, trusted roles, past incidents, and bespoke testing scripts are re-learned on every engagement.
- Audit knowledge is siloed within firms and per-tool context is non-portable.
- A portable, shareable context layer can reduce repeated discovery time and improve consistency across audits.

## Product concept
- Context capsule schema: protocol metadata, invariants, access control map, known attack surfaces, preferred tools, test scripts, and prior findings.
- Onchain registry for capsules with access control (private by default, shareable for bounty or audit partners).
- Agent integration: `mini --import-context` and `mini --export-context` to load and store context.
- Optional marketplace: teams can license curated context modules (e.g., DeFi lending, DEX hooks, staking vaults).

## TAM and SAM (assumptions, replace with sourced numbers)
- TAM (top-down): global smart contract security and dev tooling spend.
  - Assumption: 3k to 7k active protocol teams globally.
  - Assumption: $50k to $500k annual security spend per team.
  - TAM range: $150M to $3.5B.
- SAM (bottom-up): EVM teams using Foundry or similar tooling that can adopt this agent.
  - Assumption: 30% to 50% of TAM is reachable initially.
  - SAM range: $45M to $1.75B.

## GTM: low-cost validation experiments
- Open-source wedge: ship a simple context import/export feature and publish 5 example context capsules for major protocol types.
- Community distribution: post a "security context pack" on Farcaster and GitHub; offer a free audit memory template to early adopters.
- Partner experiment: a pilot with one audit firm or protocol that includes a public, sanitized context capsule.
- Success metrics: number of context capsules created, reuse rate across projects, time saved per audit, and repeat usage.

## Risks and dependencies
- Context quality risk: a bad capsule can encode wrong assumptions and propagate errors.
- Privacy risk: context may include sensitive architecture details.
- Adoption friction: protocols must standardize a schema before portability works.

## Next build steps
1. Define a JSON schema for security context in `src/minisweagent/config/`.
2. Add CLI flags for import/export and a local registry.
3. Build a demo capsule for a sample protocol in `docs/examples/`.
