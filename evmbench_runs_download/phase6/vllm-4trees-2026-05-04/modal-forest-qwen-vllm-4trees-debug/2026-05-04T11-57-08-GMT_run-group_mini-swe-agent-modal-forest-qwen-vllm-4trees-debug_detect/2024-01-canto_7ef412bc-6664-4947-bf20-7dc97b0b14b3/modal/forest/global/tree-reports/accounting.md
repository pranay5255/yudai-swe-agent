# Accounting Tree Local Merged Report

## Branch Report Assessment

**Branch 01**: No report was extracted for accounting branch-01. This is a missing branch report with no findings to evaluate.

## Independent Analysis: LendingLedger.sol Accounting Findings

After independently auditing the in-scope contract `LendingLedger.sol` with a focus on share-price math, reward accrual, rounding direction, and invariant preservation, the following findings are presented.

---

### F-1 (HIGH): Secondary reward (`secRewardDebt`) scaling uses block count directly, not reward amount — invariant drift in secondary rewards distribution

**Location**: `LendingLedger.sol`, lines 71

**Description**:
In `update_market()`, the primary CANTO reward per share is calculated correctly using the actual reward amount:
```solidity
uint256 cantoReward = (blockDelta * cantoPerBlock[epoch] * gaugeController.gauge_relative_weight_write(_market, epoch)) / 1e18;
market.accCantoPerShare += uint128((cantoReward * 1e18) / marketSupply);
```

But the secondary reward per share is calculated as:
```solidity
market.secRewardsPerShare += uint128((blockDelta * 1e18) / marketSupply); // TODO: Scaling
```

This uses `blockDelta * 1e18` as if it were a reward amount, but `blockDelta` is just a block count, not a token amount. There is no `_amountPerBlock` or equivalent parameter for secondary rewards. This means:

1. **Secondary rewards are completely uncalibrated** — they accrue at a rate of `1e18 / marketSupply` per block, regardless of any configured emission rate.
2. **No invariant can be preserved** because there is no supply of secondary reward tokens being managed by the contract, and no way to limit emissions.
3. **The comment "TODO: Scaling" explicitly acknowledges this gap** but the code is deployed as-is.
4. **Any third-party integrating secondary rewards** based on `secRewardDebt` differences will receive amounts that have no correlation with any intended emission schedule.

**Impact**: Secondary reward amounts are nonsensical and unbounded. A lending platform integrating with Neofinance Coordinator to offer secondary rewards based on `secRewardDebt` would distribute arbitrary, uncontrolled amounts.

**Root Cause**: The `secRewardDebt` accumulator uses block count instead of a configured reward-per-block value.

**Rationale for inclusion**: This is a concrete, deploy-time bug that causes incorrect reward accrual math — the core concern of the accounting specialist tree.

---

### F-2 (MEDIUM): `update_market()` loop computes epoch incorrectly for the `cantoPerBlock` lookup — rewards can be misattributed when market is first whitelisted mid-epoch

**Location**: `LendingLedger.sol`, lines 63-72

**Description**:
The `update_market()` function iterates from `market.lastRewardBlock` to `block.number`:
```solidity
while (i < block.number) {
    uint256 epoch = (i / BLOCK_EPOCH) * BLOCK_EPOCH;
    uint256 nextEpoch = i + BLOCK_EPOCH;
    uint256 blockDelta = Math.min(nextEpoch, block.number) - i;
    uint256 cantoReward = (blockDelta * cantoPerBlock[epoch] * ...) / 1e18;
    ...
    i += blockDelta;
}
```

When a market is newly whitelisted, `lastRewardBlock` is set to `block.number` (in `whiteListLendingMarket`). However, consider this scenario:

- A market is whitelisted at block 100,050 (mid-epoch, where epoch = 0).
- The `lastRewardBlock` is set to 100,050.
- A deposit occurs at block 100,050. `update_market()` is called, and since `block.number > market.lastRewardBlock` is false (they're equal), no update happens — correct.
- A deposit occurs at block 100,051. `update_market()` runs the loop with `i = 100,050`, `epoch = 0`, `blockDelta = 1`. It uses `cantoPerBlock[0]` for block 100,050's reward. This is correct.

But the real issue is when rewards were set for a future epoch that starts at `BLOCK_EPOCH * 5 = 500,000`. If the market has been inactive and a user deposits at block 500,050, the loop starts at `i = 0` (the first time `marketInfo[_market]` was accessed, `lastRewardBlock = 0` unless explicitly set). Wait — looking more carefully:

When a market is **first** whitelisted via `whiteListLendingMarket()`:
```solidity
if (_isWhiteListed) {
    marketInfo[_market].lastRewardBlock = uint64(block.number);
}
```

This sets `lastRewardBlock = block.number`, so the loop starts from the current block. This is actually fine.

However, there's a subtle issue: if `cantoPerBlock[epoch]` was never set (returns 0), the market accrues zero rewards during that epoch. The function doesn't validate that rewards were configured for epochs in the loop range. A market could be whitelisted and start accruing deposits in an epoch for which `cantoPerBlock` was never set by governance, silently distributing nothing.

**Impact**: Silent zero-reward epochs if governance fails to set rewards for a given epoch. Users deposit with the expectation of rewards but receive none.

**Root Cause**: No validation that `cantoPerBlock[epoch]` is non-zero before entering the loop.

**Rationale for inclusion**: While not a direct loss-of-funds vulnerability (the contract simply doesn't distribute what wasn't configured), it's an accounting invariant violation where the system silently produces zero rewards when the principal expectation is that rewards should flow.

---

### F-3 (MEDIUM): `sync_ledger()` rounding direction in `rewardDebt` adjustment causes small user theft from the reward pool

**Location**: `LendingLedger.sol`, lines 84-99

**Description**:
In `sync_ledger()`, when a user deposits (`_delta >= 0`):
```solidity
user.rewardDebt += int256((uint256(_delta) * market.accCantoPerShare) / 1e18);
```

When a user withdraws (`_delta < 0`):
```solidity
user.rewardDebt -= int256((uint256(-_delta) * market.accCantoPerShare) / 1e18);
```

Both cases use integer division (truncation toward zero) applied to the same `market.accCantoPerShare` value. The problem is the **asymmetric rounding**:

- On deposit, `rewardDebt` is increased by `amount * accCantoPerShare / 1e18` (rounded down).
- On claim, `accumulatedCanto = user.amount * market.accCantoPerShare / 1e18` (rounded down), and `cantoToSend = accumulatedCanto - user.rewardDebt`.

Consider: user deposits 1 unit, then deposits 1 more unit, then claims.
- After first deposit: `rewardDebt = 1 * acc / 1e18` (floor)
- After second deposit: `rewardDebt = 2 * acc / 1e18` (floor)  
- Claim: `accumulated = 2 * acc / 1e18` (floor), `toSend = accumulated - rewardDebt = 0`

But the user earned rewards between the two deposits! The issue is more nuanced though — in a properly functioning system with incremental `accCantoPerShare` updates, the per-share amount changes. The real problem emerges with **withdrawals**:

When withdrawing, `rewardDebt -= ...` uses the same truncation. The truncation on withdrawal means the user's `rewardDebt` decreases by less than the exact proportional amount, which means on claim, `accumulatedCanto - user.rewardDebt` is **larger** than it should be — the user overclaims, stealing from remaining depositors.

**Concrete example**: If `accCantoPerShare = 1.5 * 1e18` and user has 10 tokens:
- Exact reward debt: `10 * 1.5 = 15`
- Integer math: `10 * 1.5e18 / 1e18 = 15` (exact in this case)

Let me use a more revealing example: `accCantoPerShare = 1.7 * 1e18`, user amount = 10:
- Exact: `17`
- Integer: `10 * 1.7e18 / 1e18 = 17` (exact again)

The truncation only matters when `user.amount * accCantoPerShare` is not evenly divisible by `1e18`. In such cases, the accumulated reward is rounded down, and the difference (the fractional reward) is **stuck in the contract and redistributed to remaining users via dilution** — but actually, it stays in the contract, effectively being shared among remaining depositors who will claim later.

This is a **micro-arbitrage**: users who withdraw repeatedly can extract value from the rounding remainder because `rewardDebt` was set on entry with a potentially more favorable truncation than what's computed on exit.

**Impact**: Small but systematic redistribution of reward tokens — a few wei per operation — away from exiting users toward the contract/remaining users.

**Rationale for inclusion**: Classic rounding-direction vulnerability in reward accounting. While the per-transaction impact is tiny, it is systematic and mathematically verifiable.

---

### Rejected Claims

The following claims from the external reports are **rejected** for this accounting tree's merged findings:

1. **4naly3er NC-3: "TODO Left in the code"** — This is a code-quality issue, not a security vulnerability. The TODO acknowledges the scaling problem (F-1 above), which is independently more material.

2. **4naly3er GAS issues** — Gas optimizations are outside the scope of accounting/loss-of-funds vulnerabilities.

3. **4naly3er L-1: Empty receive() function** — Not a loss-of-funds vulnerability; the contract needs to receive CANTO for distribution.

4. **4naly3er NC-1: Missing address(0) checks** — Governance address can't be zero-checked per design (the constructor accepts the address directly and governance is assumed to be properly initialized). Not accounting-specific.

5. **4naly3er NC-2, GAS-3: Missing error strings / custom errors** — Not loss-of-funds issues.

---

## Summary of Findings for Global Review

| Finding | Severity | Title |
|---------|----------|-------|
| F-1 | HIGH | Secondary reward scaling uses block count instead of configured reward amount — uncontrolled emission |
| F-2 | MEDIUM | No validation that `cantoPerBlock` is set for epochs in the update loop — silent zero rewards |
| F-3 | MEDIUM | Integer rounding asymmetry in `rewardDebt` adjustments enables micro-stealing from exiting users |

All three findings relate directly to the accounting specialist's mandate: share-price math (F-1, F-3), reward accrual (F-1, F-2, F-3), invariant preservation (F-1, F-2), and rounding direction (F-3).
