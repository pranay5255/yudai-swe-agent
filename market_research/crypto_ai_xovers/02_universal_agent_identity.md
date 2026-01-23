# 2. Universal Identity for Agents

## Anchor from the a16z crypto x AI text
- Agents need a portable "passport" that acts as wallet, API registry, changelog, and social proof.
- Identity should be permissionless, not locked to a single marketplace or platform.
- A credibly neutral identity layer enables better discovery and payments across ecosystems.

## Application using this repo's capability
### Primary application: "Security Agent Passport Registry"
An onchain identity layer for security agents (including this repo's audit agent) that publishes capabilities, versioning, audit provenance, and payment addresses. This allows any platform (GitHub, Slack, email, a mini-app) to resolve the agent, verify its version, and pay for tasks.

### Why this repo fits
- The agent already has structured workflows and can expose capabilities and config templates.
- It can produce signed, reproducible outputs (tests, simulations) that map well to a verifiable identity.
- The roadmap already includes multi-surface distribution, which benefits from a shared identity layer.

## Problem and opportunity
- AI agent distribution is fragmented and identity is typically proprietary to a platform.
- For security use cases, buyers need to verify the agent version and methodology before trusting outputs.
- A portable identity reduces integration overhead and allows consistent reputation tracking.

## Product concept
- Agent passport contract: metadata (capabilities, model, toolchain, version), payment address, and audit history references.
- API resolver: look up an agent from any integration and verify its signature.
- Reputation layer: verified audit outputs and user ratings tied to the agent identity.

## TAM and SAM (assumptions, replace with sourced numbers)
- TAM: security automation + agent infrastructure spend in Web3 and adjacent dev tools.
  - Assumption: 2k to 5k orgs willing to pay for automated security agents.
  - Assumption: $10k to $100k annual spend per org.
  - TAM range: $20M to $500M.
- SAM: orgs running EVM contracts and willing to run agent-based workflows.
  - Assumption: 30% to 40% of TAM reachable early.
  - SAM range: $6M to $200M.

## GTM: low-cost validation experiments
- Ship a minimal passport spec and a free registry contract on a testnet.
- Launch a "verified agent" badge for audit reports created via this repo.
- Add a GitHub Action that embeds the agent identity into PR comments.
- Success metrics: number of agents registered, number of reports with verified identity, and paid pilot requests.

## Risks and dependencies
- Identity without distribution has limited value; needs integration partners.
- Reputation gaming if outputs are not verifiable or reproducible.
- Onchain metadata must avoid leaking sensitive details.

## Next build steps
1. Define an agent identity JSON format and signature scheme.
2. Add an opt-in flag to sign audit outputs with the agent identity.
3. Publish a lightweight resolver API for integrations.
