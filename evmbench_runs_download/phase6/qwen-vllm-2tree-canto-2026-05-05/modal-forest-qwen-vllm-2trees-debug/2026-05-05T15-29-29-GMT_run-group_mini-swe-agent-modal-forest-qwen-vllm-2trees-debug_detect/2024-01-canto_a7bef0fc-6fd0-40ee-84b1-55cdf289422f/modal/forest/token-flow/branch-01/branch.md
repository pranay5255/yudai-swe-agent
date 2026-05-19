# Token Flow Analysis — Branch 1 of 1

## Contract Analyzed: `LendingLedger.sol` (in scope per scope.txt)

### Summary of Critical Findings

Three confirmed vulnerability findings have been identified in the `LendingLedger.sol` contract that affect token flows, reward accounting, and can lead to direct loss of funds from the contract's CANTO balance.

---

## Finding 1 (CRITICAL): Negative rewardDebt exploitation leads to unearned claim payout

**Severity:** CRITICAL  
**File:** `src/LendingLedger.sol`  
**Function:** `claim(address _market)` (lines 104–117)  
**Root Cause:** Incomplete reward accounting when user fully withdraws their deposit allows `cantoToSend` to become positive even when `user.amount == 0`.

### Description

The reward claiming logic in `claim()` computes:
```solidity
int256 accumulatedCanto = int256((uint256(user.amount) * market.accCantoPerShare) / 1e18);
int256 cantoToSend = accumulatedCanto - user.rewardDebt;
```

When `user.amount == 0`, `accumulatedCanto` is always 0. If `user.rewardDebt` is negative (i.e., less than zero), then `cantoToSend = 0 - negative = positive`, and the user receives CANTO they never earned.

**How `rewardDebt` becomes negative:**

1. User deposits tokens at time T1 when `accCantoPerShare = X`. Their `rewardDebt += amount * X / 1e18` (positive).
2. Rewards accrue. `accCantoPerShare` increases to Y > X via `update_market()`.
3. User withdraws ALL their tokens at time T2. Their `rewardDebt -= amount * Y / 1e18` (deduction is now larger because Y > X).
4. Since `rewardDebt` was increased only by X per unit deposited but is decreased by Y per unit withdrawn (where Y > X), the net `rewardDebt` becomes negative.

**Example numeric scenario:**
- User deposits 1,000 units when `accCantoPerShare = 1e18` (1.0)
- `rewardDebt = 1000 * 1e18 / 1e18 = 1000`
- Rewards accrue, `accCantoPerShare = 1.2e18` (1.2)
- User withdraws all 1,000 units
- `rewardDebt = 1000 - 1000 * 1.2e18 / 1e18 = 1000 - 1200 = -200`
- User calls `claim()`: `accumulatedCanto = 0 * 1.2e18 / 1e18 = 0`
- `cantoToSend = 0 - (-200) = 200` → User receives 200 CANTO despite having 0 balance!

### Exploit Path

1. Attacker becomes a lender (or exploits a real user's position if they can call `sync_ledger` on their behalf — see Finding 3)
2. Deposit tokens into a whitelisted market
3. Wait for rewards to accrue (or trigger `update_market` externally)
4. Withdraw ALL deposited tokens
5. Call `claim()` → receives CANTO payout for zero balance

### Impact

Direct loss of CANTO from the contract. The loss amount is proportional to the reward accrual rate between deposit and withdrawal. With sustained rewards, this can drain significant funds.

### Evidence

Code path verified:
- Line 89: `user.amount += uint256(_delta)` during deposit
- Line 90: `user.rewardDebt += int256((uint256(_delta) * market.accCantoPerShare) / 1e18)` — uses current accCantoPerShare
- Line 93: `user.amount -= uint256(-_delta)` during withdrawal  
- Line 94: `user.rewardDebt -= int256((uint256(-_delta) * market.accCantoPerShare) / 1e18)` — uses UPDATED (higher) accCantoPerShare after `update_market()` at line 84
- Line 108: `accumulatedCanto = 0` when amount is 0
- Line 109: `cantoToSend = accumulatedCanto - user.rewardDebt` — subtracts negative value

### Remediation

Add a guard: only allow claiming if `cantoToSend > 0 AND user.amount > 0`, or alternatively compute rewards owed separately from rewardDebt tracking. A simpler fix: ensure `cantoToSend` is computed as `max(accumulatedCanto - user.rewardDebt, 0)`, and additionally that `user.amount > 0` before allowing a claim (or maintain a separate rewards-owed counter that is only decremented on claim, not affected by withdrawals).

---

## Finding 2 (CRITICAL): Rounding loss in `sync_ledger` causes asymmetric reward debt adjustment

**Severity:** CRITICAL (confirms and strengthens Finding 1)  
**File:** `src/LendingLedger.sol`  
**Functions:** `sync_ledger(address _lender, int256 _delta)` (lines 82–100), `claim(address _market)` (lines 104–117)

### Description

The integer division `(uint256(_delta) * market.accCantoPerShare) / 1e18` in `sync_ledger` truncates. This means:

1. When depositing, the user's `rewardDebt` increase may be slightly LESS than their proportional reward share (due to truncation).
2. When withdrawing, the same truncation applies but now subtracts from a different base.
3. Over multiple deposit/withdraw cycles with changing