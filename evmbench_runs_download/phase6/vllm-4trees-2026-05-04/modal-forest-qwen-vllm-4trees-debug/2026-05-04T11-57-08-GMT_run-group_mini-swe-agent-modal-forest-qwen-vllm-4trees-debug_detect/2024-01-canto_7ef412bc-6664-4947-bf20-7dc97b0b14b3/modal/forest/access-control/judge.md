# Access Control Tree — Merged Report

## Summary
After thorough review of the branch report (branch-01.md) and independent analysis of the in-scope contract `LendingLedger.sol`, this tree identifies **one** concrete, high-signal access control finding that may survive final review. Seven branch findings were rejected as insufficiently concrete, out of scope, or non-impactful.

---

## ✅ Accepted Findings

### AC-04: Whitelisted Lending Market Can Update Arbitrary User Reward Balances
**Severity:** Medium  
**Contract:** `LendingLedger.sol` — `sync_ledger()` (lines 82–100)

**Description:**  
The `sync_ledger(address _lender, int256 _delta)` function is callable by any whitelisted lending market (checked via `update_market(msg.sender)` on line 84). However, it accepts `_lender` as a parameter with **no verification** that the calling market is authorized to modify that user's balance. The mapping `userInfo[lendingMarket][_lender]` allows any whitelisted market to read/write another user's position in any whitelisted market's data.

A compromised or malicious whitelisted market can call `sync_ledger(randomUser, largePositiveDelta)` for arbitrary users, inflating their `rewardDebt`/`secRewardDebt` values. When those users subsequently call `claim()`, the contract sends CANTO from its treasury to the inflated user addresses, draining funds.

**Exploit scenario:**
1. An attacker (or compromised partner) operates a whitelisted lending market contract.
2. Attacker calls `sync_ledger(userA, 1000000000000000000000)` for many user addresses.
3. Each affected user now has artificially inflated reward balances.
4. Affected users call `claim(_market)` and receive CANTO from the contract's treasury.
5. Contract treasury is drained proportionally to the sum of inflated rewards.

**Root cause:** Missing authorization between the calling market and the target user `_lender` in `sync_ledger()`.

**Remediation:** Require that the caller is authorized to update the specified user — e.g., `require(msg.sender == _lender || authorizedMarket[msg.sender][_lender], "Unauthorized")` or use a signed-off balance update mechanism.

---

## ❌ Rejected Findings

### AC-01 — No zero-address check on governance (Rejected as Weak)
While technically a valid deployment-time concern, the scenario is extremely unlikely in practice. Governance addresses are set by deployment scripts under full operator control, and `address(0)` would be immediately caught during testing. The `onlyGovernance` modifier correctly prevents unprivileged calls to `setRewards` and `whiteListLendingMarket`. The risk of misconfigured deployment does not constitute an independent access control vulnerability in the running contract. **Severity too low; marginal signal.**

### AC-02 — `setGovernance` emits no event (Rejected — Not a vulnerability)
Missing events are an operational/auditing concern, not a loss-of-funds vulnerability. Does not meet the scope criterion of "directly or indirectly lead to a loss of user or platform assets."

### AC-03 — `whiteListLendingMarket` toggle restriction (Rejected — Informational only)
The `require(lendingMarketWhitelist[_market] != _isWhiteListed, "No change")` correctly prevents no-op calls. This is a design observation, not a vulnerability.

### AC-05 — `claim` reentrancy (Rejected — Code is safe)
The branch itself correctly identifies that `claim` follows the check-effects-interaction pattern: `user.rewardDebt` is set before the external call, so reentrancy cannot double-spend.

### AC-06 — VotingEscrow `withdraw` delegation check (Rejected — Out of scope)
`VotingEscrow.sol` is explicitly listed as out of scope in the audit scope. The VotingEscrow's delegation behavior is documented Curve Finance pattern behavior.

### AC-07 — `sync_ledger` reentrancy via GaugeController (Rejected — Not sufficiently concrete)
The external call targets `gaugeController.gauge_relative_weight_write()`, which is a governance-controlled contract, not a user-controlled contract. Exploiting this would require governance compromise, which the README states is assumed non-malicious. The risk is theoretical and not independently actionable.

### AC-08 — `gauge_relative_weight_write` publicly callable (Rejected — Out of scope)
`GaugeController.sol` is explicitly out of scope. Additionally, the function only writes historical tracking data and does not change actual weights.

---

## Final Assessment

This tree submits **1 finding** (AC-04) for global review. This is a genuine access control vulnerability: any whitelisted lending market can arbitrarily inflate any user's reward balance, leading to potential treasury drainage when those users claim. The vulnerability is in the in-scope contract (`LendingLedger.sol`), has a concrete exploit path, and results in direct loss of funds.

*Tree-local merged report by Access Control Specialist.*
