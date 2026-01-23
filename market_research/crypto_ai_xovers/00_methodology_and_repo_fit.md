# Crypto x AI Crossover Research - Methodology and Repo Fit

## Scope and assumptions
- This research uses only the provided a16z crypto x AI crossover text for the core conceptual framing.
- No external data sources were accessed. Market sizes are expressed as ranges and sizing formulas with explicit assumptions.
- All ideas are constrained to be buildable from this repo's capabilities: a minimal AI agent stack plus a Foundry-based smart contract security toolchain ("YudaiV4" in docs).

## Repo capability summary (how this repo can ship product)
- Minimal agent loop and model integration for reliable CLI or API workflows.
- Execution environments (local, Docker, Foundry) that can compile, test, and simulate smart contracts safely.
- Security toolchain baked into the Foundry image: Slither, Aderyn, Mythril, Echidna, solc-select, Anvil for forked simulations.
- Config templates for audit and security workflows that can be reused by product surfaces: CLI, GitHub PR bot, and mini-app UI.

In practical terms, this repo is already a programmable security agent for smart contracts. That capability can be extended to: agent identity and reputation, onchain provenance for findings, micropayment rails, or onchain registries for security knowledge.

## TAM and SAM approach
Because external data is not used, TAM and SAM are computed using transparent formulas and clearly stated assumptions:

- TAM (Total Addressable Market):
  - Top-down: Global spend in the closest adjacent market (cybersecurity, software developer tools, or blockchain infrastructure).
  - Bottom-up: Number of target entities * average annual spend on the product category.

- SAM (Serviceable Addressable Market):
  - Subset of TAM that is reachable by this repo's scope (smart contract teams, Web3 protocols, audit firms, builders using Foundry or EVM-like chains).
  - Adjusted for initial geography or channel constraints (developer tools, GitHub-based flows, Farcaster distribution).

Each deep dive includes explicit assumptions. Replace the assumptions with sourced data as you refine.

## GTM (low-cost validation) criteria
Each idea includes a low-cost GTM plan oriented around fast signal and minimum engineering:
- Distribution anchor: one core surface (CLI, GitHub app, Farcaster mini-app, or API) that is already supported by this repo's patterns.
- First buyer: a narrow persona (smart contract dev, audit firm lead, DeFi protocol, NFT studio, or DAO) with immediate pain.
- Measurable signal: conversions to trial, repos added, PRs scanned, bounties paid, or paid pilot deals.
- Minimal marketing: targeted community posts, open-source wedge, small paid bounty or demo campaigns.

## Experiment matrix factors
The matrix in `market_research/crypto_ai_xovers/experiment_matrix.md` scores ideas on:
- Speed to prototype (weeks)
- Integration complexity
- Distribution leverage (does the channel already exist)
- Revenue clarity
- Regulatory risk
- Competitive intensity
- Strategic fit with this repo

## Next data inputs to request
If you want tighter numbers, provide:
- Target chain(s) and geography.
- Existing customer list or community channels.
- Expected pricing or budget ranges.
- Preferred distribution surface (CLI, GitHub, Farcaster mini-app, API).
