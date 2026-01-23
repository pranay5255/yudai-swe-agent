# 3. Forwards-Compatible Proof of Personhood

## Anchor from the a16z crypto x AI text
- The web is flooded with bots and deepfakes; proof of personhood (PoP) is becoming critical infrastructure.
- Decentralized PoP is portable, permissionless, and controlled by the user.
- Adoption accelerates as more applications recognize the same PoP ID.

## Application using this repo's capability
### Primary application: "PoP-Verified Bug Bounty Submissions"
Require a proof-of-personhood attestation for high-value bug bounty submissions. The agent validates reports and runs safe exploit simulations, while PoP ensures that submissions and payouts are tied to a unique human.

### Why this repo fits
- The repo already supports safe exploit simulation and audit workflows in Foundry.
- It can produce reproducible evidence that can be linked to a PoP attestation.
- The agent can serve as a verification layer for bounty intake.

## Problem and opportunity
- Bug bounty programs face sybil spam, low-quality submissions, and coordination overhead.
- Human verification can increase signal quality and reduce spam without centralizing identity control.
- Combining PoP with automated verification makes bounty ops cheaper and more reliable.

## Product concept
- Submission flow: submitter signs a PoP attestation and a proof bundle (PoC, tests, reproduction script).
- Agent runs verification, generates a report, and attaches PoP proof to the result.
- Smart contract or payout system releases funds to PoP-verified contributors.

## TAM and SAM (assumptions, replace with sourced numbers)
- TAM: global bug bounty spend across cybersecurity and Web3.
  - Assumption: $500M to $2B annual global bounty spend.
- SAM: Web3 and smart contract bounties, plus security audit incentive programs.
  - Assumption: 10% to 25% of TAM.
  - SAM range: $50M to $500M.

## GTM: low-cost validation experiments
- Pilot with one protocol: PoP required only for payouts above a threshold.
- Hackathon experiment: run a PoP-verified security challenge using this repo's validation pipeline.
- Success metrics: reduction in spam, higher verification pass rate, and time-to-payout.

## Risks and dependencies
- PoP adoption: without a commonly accepted PoP standard, friction remains.
- Privacy concerns: ensure the attestation does not expose personal data.
- Legal/regulatory: payout programs may have compliance requirements.

## Next build steps
1. Add a PoP verification hook in the bounty intake CLI workflow.
2. Create a signed evidence bundle format that includes PoP references.
3. Publish an example integration spec for a bounty platform.
