# 8. Blockchains as a Registry for IP and Provenance

## Anchor from the a16z crypto x AI text
- AI needs programmable IP registries to track provenance and licensing.
- Onchain registries can enable remixing and derivative works while preserving ownership.
- Programmable IP flips AI's IP risk into a licensing opportunity.

## Application using this repo's capability
### Primary application: "Onchain Registry for Audit Reports and Vulnerability Patterns"
A registry where audit reports, vulnerability proofs, and fix patterns are hashed and licensed. AI agents can query and license these artifacts for training or for audit acceleration.

### Why this repo fits
- The agent generates reproducible audit outputs and fix suggestions.
- It can hash and publish report metadata at the end of each run.
- The repo can attach licensing terms directly to outputs.

## Problem and opportunity
- Security research is valuable but often untracked or leaked without attribution.
- AI models benefit from security data, but creators need a licensing path.
- A registry provides provenance and creates a market for security knowledge.

## Product concept
- Publish: onchain record with report hash, license, author, and access URI.
- Consume: agents can request access and pay to use proprietary reports.
- Remix: derive new patterns and attribute them back to original sources.

## TAM and SAM (assumptions, replace with sourced numbers)
- TAM: licensing value of security research and AI training data.
  - Assumption: $300M to $2B annual value globally.
- SAM: Web3 security research and audit outputs.
  - Assumption: 10% to 20% of TAM.
  - SAM range: $30M to $400M.

## GTM: low-cost validation experiments
- Launch a free registry for open-source audit reports and vulnerability PoCs.
- Partner with one audit firm to publish hashed reports with optional licensing.
- Success metrics: number of reports registered, paid access events, and reuse in audits.

## Risks and dependencies
- IP ambiguity: ownership of audit outputs can be disputed.
- Adoption: firms may resist publishing metadata.
- Enforcement: licensing requires compliance and monitoring.

## Next build steps
1. Add a report hashing and metadata export step to the agent.
2. Define a minimal onchain registry schema and a CLI publisher.
3. Create a public gallery page for registered artifacts.
