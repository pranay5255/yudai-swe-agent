# Accounting Tree — Merged Report

## Scope

Contract: `src/LendingLedger.sol` (106 SLOC) — the sole in-scope contract for the Canto Invitational audit.  
The `GaugeController` and `VotingEscrow` are referenced but not in scope; findings against them are treated as external-context only.

## Branch Report Assessment

- **branch-01.md**: "No report was extracted." — No branch claims to evaluate.

## Findings

### [A-1] Truncation in per-share reward accumulation permanently siphons user rewards

**Severity: Medium**

**Location:** `LendingLedger.update_market`, line 70

**Description:**  
In `update_market`, the accrued CANTO per-share is incremented as:
```solidity
market.accCantoPerShare += uint128((cantoReward * 1e18) / marketSupply);
```
The division `(cantoReward * 1e18) / marketSupply` truncates (rounds toward zero). The truncated remainder is permanently lost — it remains in the contract balance and is never distributed to users. Over many update calls, this truncation error compounds. The same pattern exists for `secRewardsPerShare` on line 71.

The `claim` function recalculates owed rewards as:
```solidity
int256 accumulatedCanto = int256((uint256(user.amount) * market.accCantoPerShare) / 1e18);
int256 cantoToSend = accumulatedCanto - user.rewardDebt;
```
This compounds the truncation from the sync phase (`sync_ledger` line 90) and the claim phase (line 108).

**Impact:** Users receive less than their fair share of CANTO rewards. The loss per user per claim is bounded by `accCantoPerShare * user.amount / 1e18` truncation error, which is at most `marketSupply - 1` units of the 1e18-scaled reward rate, amortized across all users. In practice, the loss per claim is small (a few wei to a small fraction of a token) but is permanent and cumulative.

**Rationale:** This is a known characteristic of Synthex/MasterChef-style reward pools (the README admits this is adapted from that pattern). The loss is small per event but systematic — every user is underpaid by a fraction of a unit in 1e18-scaled terms per update. Over a full epoch (~100K blocks) with low market supply, the accumulated loss can reach a significant fraction of a token.

### [A-2] secRewardsPerShare scaling is incomplete (no emission rate from governance)

**Severity: Low — Informational**

**Location:** `LendingLedger.update_market`, line 71

**Description:**  
```solidity
market.secRewardsPerShare += uint128((blockDelta * 1e18) / marketSupply); // TODO: Scaling
```
The secondary reward accumulator grows solely based on `blockDelta / marketSupply`. There is no governance-configurable emission rate (unlike `accCantoPerShare`, which is driven by `cantoPerBlock[epoch]` and the gauge weight). The TODO comment explicitly flags this as incomplete.

Secondary rewards are intended to be funded by "lending platforms that are integrated with Neofinance Coordinator" (per the README) based on the difference in `secRewardDebt` between transactions. However, because the `secRewardsPerShare` formula does not incorporate any per-block emission amount from governance, the total secondary reward "debt" generated is purely a function of time and supply — independent of any secondary emission schedule.

**Impact:** External reward providers must independently track and fund secondary rewards based on the delta of `secRewardDebt`. The contract does not enforce or track any secondary emission rate. If external platforms expect a specific emission rate, the current formula may not match their expectations, especially if multiple markets share supply dynamics differently.

**Rationale:** This is a design incompleteness rather than an exploit. The contract exposes `secRewardDebt` for external use, but the internal per-share accumulator lacks the emission-rate parameter that external systems may need to coordinate on.

### [A-3] uint128 overflow in accCantoPerShare and secRewardsPerShare under extreme conditions

**Severity: Low**

**Location:** `LendingLedger.update_market`, lines 70–71

**Description:**  
Both `accCantoPerShare` and `secRewardsPerShare` are stored as `uint128` (max value ≈ 3.4 × 10^38). These fields accumulate over time and are never reset.

For `accCantoPerShare`: each iteration adds `(cantoReward * 1e18) / marketSupply`. With `cantoReward` up to `cantoPerBlock[epoch]` (governance-set) and `marketSupply` as low as 1 wei, the per-iteration addition could be up to `cantoPerBlock[epoch] * 1e18`. If `cantoPerBlock` is, e.g., 10 CANTO = 10^19 wei per block, and supply is 1 wei, each iteration adds ~10^37. After ~3 iterations, `uint128` overflows.

For `secRewardsPerShare`: each iteration adds `blockDelta * 1e18 / marketSupply`. With supply = 1 and blockDelta = 1, each adds 1e18. Overflow takes ~3.4 × 10^20 iterations.

**Impact:** Under extreme conditions (very low market supply with very high per-block emissions), `accCantoPerShare` could overflow `uint128`, corrupting the reward accounting and potentially causing users to be over- or underpaid. `secRewardsPerShare` overflow is far less likely but theoretically possible over millions of years of operation.

**Rationale:** While unlikely under normal operating parameters, this is a concrete overflow risk for `accCantoPerShare` with very low-supply markets. The contract should either use `uint256` for these accumulators or document the safe parameter ranges.

## Rejected Branch Claims

No branch claims were submitted for evaluation.

## Summary

Three accounting-specific findings are forwarded for global review:

| ID | Title | Severity |
|----|-------|----------|
| A-1 | Truncation in per-share reward accumulation permanently siphons user rewards | Medium |
| A-2 | secRewardsPerShare scaling is incomplete (no emission rate from governance) | Low |
| A-3 | uint128 overflow in accCantoPerShare and secRewardsPerShare under extreme conditions | Low |

These findings focus on the Accounting specialist scope: share-price math, rounding direction, reward accrual, and invariant preservation. No claims of loss-of-funds exploits (e.g., direct theft, unauthorized minting) were identified in this analysis. The rounding truncation (A-1) is the most concrete and impactful finding, as it represents a systematic, guaranteed underpayment of users.
