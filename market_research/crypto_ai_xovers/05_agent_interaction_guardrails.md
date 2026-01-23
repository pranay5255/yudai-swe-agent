# 5. Infrastructure and Guardrails for Agent-to-Agent Interactions

## Anchor from the a16z crypto x AI text
- Agents will increasingly need to request data and services from other agents.
- There are no generalized agent-to-agent markets; APIs are siloed and closed.
- Blockchains can provide open standards and payment rails, plus guardrails to keep agents aligned with user intent.

## Application using this repo's capability
### Primary application: "Agentic Security Workflow with Onchain Guardrails"
A multi-agent security pipeline where specialized agents (static analysis, fuzzing, simulation, report writing) interact via an onchain workflow ledger. Guardrails enforce allowed actions, scope, and budget limits.

### Why this repo fits
- The repo already unifies multiple security tools under a single agent loop.
- Its execution model is modular and can be extended to call out to other agents or services.
- Audit workflows require strict safety constraints, which map well to guardrails.

## Problem and opportunity
- As security workflows become more agentic, errors or unbounded actions can be costly.
- Enterprises need visibility and policy enforcement for agent actions.
- A shared guardrail layer reduces risk and increases trust in automated workflows.

## Product concept
- Onchain workflow registry: defines allowed tasks, budgets, and scope.
- Agent-to-agent payment standard with receipts tied to workflow ID.
- Policy enforcement layer that blocks actions outside scope.

## TAM and SAM (assumptions, replace with sourced numbers)
- TAM: agent operations + security automation spend across Web3.
  - Assumption: 2k to 5k orgs, $20k to $150k annual agent ops spend.
  - TAM range: $40M to $750M.
- SAM: orgs actively running automated security pipelines.
  - Assumption: 30% of TAM.
  - SAM range: $12M to $225M.

## GTM: low-cost validation experiments
- Open-source guardrail spec + sample policies for audit tasks.
- Pilot with one audit firm: apply guardrails to internal workflows and measure incident reduction.
- Success metrics: policy violations caught, time saved in manual review, and adoption by teams.

## Risks and dependencies
- Standards adoption: needs multiple agents to use the same workflow format.
- Policy overhead: too many constraints can slow the pipeline.
- Onchain costs: keep logs minimal and use offchain storage for large payloads.

## Next build steps
1. Define a policy schema and enforce it in the agent runner.
2. Add a workflow ID and receipts to every tool call.
3. Build a minimal onchain registry for policies.
