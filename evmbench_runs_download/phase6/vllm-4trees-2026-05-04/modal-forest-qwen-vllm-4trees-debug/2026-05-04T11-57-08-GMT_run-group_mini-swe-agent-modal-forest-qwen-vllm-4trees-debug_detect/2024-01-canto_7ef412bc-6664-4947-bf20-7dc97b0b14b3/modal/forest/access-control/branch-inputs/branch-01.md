# Access Control Branch Report — Branch 01 of 01

## Scope
- **In-scope contract:** `src/LendingLedger.sol` (106 SLOC)
- **Related contracts (for context, out of scope but referenced):** `src/GaugeController.sol`, `src/VotingEscrow.sol`
- **Focus:** Missing modifiers, confused ownership, initializer mistakes, role escalation, unsafe delegatecall/upgrade hooks, admin-only flows reachable by untrusted users

---

## Finding AC-01: Governance address not validated against `address(0)` in constructor and `setGovernance`

**Severity:** Low (can lead to permanent loss of governance control)

**Contracts:** `LendingLedger.sol` (lines 45-47, 52-53), `GaugeController.sol` (lines 57-59, 66-67)

**Description:**
Both `LendingLedger` and `GaugeController` accept the `_governance` address parameter in their constructors and in their respective `setGovernance()` functions without validating it is not `address(0)`. If `address(0)` is set as the governance address:
- The `onlyGovernance()` modifier will check `msg.sender == address(0)`, which can never be true for any externally owned account or contract.
- All privileged functions (`setRewards`, `whiteListLendingMarket` in LendingLedger; `add_gauge`, `remove_gauge`, `remove_gauge_weight` in GaugeController) become permanently inoperable.
- Governance can never be transferred away from `address(0)` because no function is callable by governance to change it.

**Code references:**
```solidity
// LendingLedger.sol line 45-47
constructor(address _gaugeController, address _governance) {
    gaugeController = GaugeController(_gaugeController);
    governance = _governance;  // no zero-address check
}

// LendingLedger.sol lines 52-53
function setGovernance(address _governance) external onlyGovernance {
    governance = _governance;  // no zero-address check
}
```

**Impact:** If the deployment script accidentally passes `address(0)` as governance, the protocol becomes permanently unupgradable and ungovernable. This is a deployment-time risk that, while unlikely, has a total impact on protocol functionality.

**Remediation:** Add `require(_governance != address(0), "Zero address")` to both constructor and `setGovernance`.

---

## Finding AC-02: `setGovernance` emits no event — governance changes are untraceable

**Severity:** Low (operational/auditing concern)

**Contracts:** `LendingLedger.sol` (line 52-53), `GaugeController.sol` (line 66-67)

**Description:**
The `setGovernance` function reassigns the governance address but does not emit any event. This means:
- There is no on-chain audit trail of governance transfers.
- Off-chain watchers and auditors cannot track when/why governance changed.
- This makes detecting unauthorized or suspicious governance changes impossible without reading storage directly.

**Impact:** Operational/auditing risk. While it doesn't directly cause loss of funds, it undermines transparency and trust in governance operations.

**Remediation:** Add an event: `event GovernanceTransferred(address indexed oldGovernance, address indexed newGovernance);`

---

## Finding AC-03: `whiteListLendingMarket` toggle logic — can be called twice with same boolean due to check

**Severity:** Informational / Low

**Contracts:** `LendingLedger.sol` (lines 137-143)

**Description:**
```solidity
function whiteListLendingMarket(address _market, bool _isWhiteListed) external onlyGovernance {
    require(lendingMarketWhitelist[_market] != _isWhiteListed, "No change");
    lendingMarketWhitelist[_market] = _isWhiteListed;
    if (_isWhiteListed) {
        marketInfo[_market].lastRewardBlock = uint64(block.number);
    }
}
```

The `require` condition `lendingMarketWhitelist[_market] != _isWhiteListed` prevents no-op calls. However, the whitelisting check is only `!=`, meaning if a market is already whitelisted, you can only set it to `false` (removing it). There is no duplicate prevention if you call with different markets but same address — though this is minor.

More critically, once a market is whitelisted, there is **no restriction on which user a whitelisted lending market can modify** via `sync_ledger`.

**Impact:** Low. This is a design observation. The real concern is below (AC-04).

---

## Finding AC-04: Any whitelisted lending market can update any user's reward balance — no market-to-user binding

**Severity:** Medium

**Contracts:** `LendingLedger.sol` (lines 82-100, `sync_ledger`)

**Description:**
The `sync_ledger` function is callable by **any whitelisted lending market** (`msg.sender` must be whitelisted), and accepts **any `_lender` address** as a parameter:

```solidity
function sync_ledger(address _lender, int256 _delta) external {
    address lendingMarket = msg.sender;
    update_market(lendingMarket); // Checks if the market is whitelisted
    MarketInfo storage market = marketInfo[lendingMarket];
    UserInfo storage user = userInfo[lendingMarket][_lender];
    // ... updates user.amount, user.rewardDebt, user.secRewardDebt
}
```

There is **no check** that the `_lender` address has any relationship to the calling market. A malicious (or compromised) whitelisted lending market can:
1. **Inflate any user's rewards** by calling `sync_ledger(userAddress, positiveDelta)` — creating fake deposit amounts that generate unrecoverable reward claims.
2. **Reduce any user's rewards** (though this would require negative delta and user.amount must be large enough).
3. **Drain contract funds** if the contract has sufficient CANTO balance — a malicious market could inflate thousands of users' reward debts to claim everything.

**Exploit path:**
1. Attacker deploys a contract and gets it whitelisted as a lending market (requires governance — but if governance is compromised, or via social engineering).
2. Attacker calls `sync_ledger(randomUserAddress, 1000 ether)` repeatedly for many user addresses.
3. Those users now have artificially inflated `rewardDebt` values.
4. When those users call `claim()`, the contract sends them CANTO from its treasury.
5. The attacker has drained the contract's CANTO balance by inflating arbitrary users' balances.

**Impact:** If the contract holds a significant CANTO balance for reward distribution, this could lead to total loss of funds. The contract has a `receive()` function and receives CANTO from governance — making this a real concern.

**Remediation Options:**
1. Require that the caller of `sync_ledger` is the actual `_lender` (i.e., `require(msg.sender == _lender || authorized[msg.sender][_lender])`).
2. Add a market-to-user registration mechanism where only registered users can have their balance updated by that market.
3. Use a merkle proof or signed message approach for balance updates.

---

## Finding AC-05: `claim` sends value to `msg.sender` (the claimer) but updates happen after update_market external call

**Severity:** Informational (reentrancy guard covers this)

**Contracts:** `LendingLedger.sol` (lines 104-117, `claim`)

**Description:**
```solidity
function claim(address _market) external {
    update_market(_market); // external call to gaugeController.gauge_relative_weight_write
    // ...
    if (cantoToSend > 0) {
        (bool success, ) = msg.sender.call{value: uint256(cantoToSend)}("");
        require(success, "Failed to send CANTO");
    }
}
```

The `update_market` function makes an external call to `gaugeController.gauge_relative_weight_write(_market, epoch)` which can modify `marketInfo` storage. The `user.rewardDebt` is updated **before** the external call to `msg.sender.call`. Since there's no `nonReentrant` guard on `claim` or `sync_ledger`, a malicious gauge controller or lending market could theoretically cause reentrancy.

However, since `user.rewardDebt` is set to `accumulatedCanto` (the claimed value) **before** the ETH transfer, and there's no state change after the transfer in `claim`, this is actually safe from reentrancy exploitation within the claim function itself. The `update_market` call's effects are already committed before the balance check.

**Impact:** Low — the code is actually safe here due to the check-effects-interaction pattern being correctly applied within `claim`.

---

## Finding AC-06: `VotingEscrow.withdraw` checks `delegatee == msg.sender` — but `createLock` and `increaseAmount` can set delegatee to another address, making withdrawal impossible without delegation reset

**Severity:** Medium (usability / potential lock-up)

**Contracts:** `VotingEscrow.sol` (lines 326-346, `withdraw`)

**Description:**
```solidity
function withdraw() external nonReentrant {
    LockedBalance memory locked_ = locked[msg.sender];
    require(locked_.amount > 0, "No lock");
    require(locked_.end <= block.timestamp, "Lock not expired");
    require(locked_.delegatee == msg.sender, "Lock delegated");  // <-- critical
    // ... sends funds back
}
```

When a user calls `createLock` or `increaseAmount`, the `delegated` balance and `delegatee` are set to `msg.sender`. However, if a user delegates their voting power to another address via `increaseAmount` (which sets `delegatee` to someone else when `delegatee != msg.sender`), the original depositor can **never withdraw** their locked funds because `locked_.delegatee == msg.sender` will fail.

The `withdraw` function requires that the current `delegatee` equals `msg.sender` — meaning only the **current delegatee** (not the original depositor) can withdraw. This is by design in Curve's VotingEscrow, but it's a significant access control concern:

1. If a user delegates to another address and their lock expires, they cannot withdraw — only the delegatee can.
2. A delegatee could potentially claim someone else's expired lock.

**Impact:** A user who delegates and then lock expires cannot recover their deposited CANTO unless the delegatee is themselves or they undelagate first. This is a lock-up of user funds.

**Note:** This is documented/expected behavior in Curve's VotingEscrow pattern, and the README notes this is a fork/adaptation. However, the delegatee check in `withdraw` combined with the fact that `increaseAmount` can change the delegatee creates a potential fund lock-up scenario.

---

## Finding AC-07: `sync_ledger` has no reentrancy protection and calls `update_market` which has external call

**Severity:** Low to Medium (contextual — depends on whether markets can be malicious)

**Contracts:** `LendingLedger.sol` (lines 82-100, `sync_ledger`)

**Description:**
`sync_ledger` is called by whitelisted lending markets. The function:
1. Calls `update_market(lendingMarket)` which makes an external call to `gaugeController.gauge_relative_weight_write(_market, epoch)`
2. Updates state variables: `user.amount`, `user.rewardDebt`, `user.secRewardDebt`, `lendingMarketTotalBalance[lendingMarket]`

Since `update_market` performs an external call and state is updated after it, a reentrant malicious gauge controller could potentially manipulate the state. However, the external call goes to `GaugeController`, which is a governance-controlled contract (not user-controlled), so this risk is limited.

**Impact:** Low — the external call is to a governance-controlled `GaugeController`, not user-controlled. Reentrancy via the gauge controller would require governance compromise.

---

## Finding AC-08: `gauge_relative_weight_write` is publicly callable on `GaugeController` — any address can update gauge weights

**Severity:** Low (governance bypass vector)

**Contracts:** `GaugeController.sol` (lines 179-182)

**Description:**
```solidity
function gauge_relative_weight_write(address _gauge, uint256 _time) external returns (uint256) {
    _get_weight(_gauge);
    _get_sum();
    return _gauge_relative_weight(_gauge, _time);
}
```

This function is callable by **any address** (no access control modifier). It writes to `points_weight` and `points_sum` storage. While it doesn't change the actual weight values (only "fills" historical data), a malicious actor could:
1. Call this repeatedly for many gauges, causing state writes that could be used to manipulate timing-dependent calculations.
2. Potentially cause griefing by forcing state updates that affect downstream calculations in `LendingLedger.update_market`.

In `LendingLedger.update_market`, the external call to `gaugeController.gauge_relative_weight_write` is made inside a loop. Any address interacting with LendingLedger (calling `claim` or `sync_ledger`) indirectly triggers this public write function on GaugeController.

**Impact:** Low — the function only updates historical tracking data and doesn't change actual weights. Weights can only be changed via governance functions (`add_gauge`, `remove_gauge`, `vote_for_gauge_weights`).

---

## Summary Table

| ID | Title | Severity | Contract(s) |
|----|-------|----------|-------------|
| AC-01 | No zero-address check on governance | Low | LendingLedger, GaugeController |
| AC-02 | `setGovernance` emits no event | Low | LendingLedger, GaugeController |
| AC-03 | `whiteListLendingMarket` toggle restriction | Info | LendingLedger |
| AC-04 | Whitelisted market can update any user's balance | **Medium** | LendingLedger (`sync_ledger`) |
| AC-05 | `claim` reentrancy analysis | Info | LendingLedger |
| AC-06 | Delegation blocks original depositor from withdrawing | **Medium** | VotingEscrow (`withdraw`) |
| AC-07 | `sync_ledger` reentrancy via external call | Low | LendingLedger |
| AC-08 | `gauge_relative_weight_write` is publicly callable | Low | GaugeController |

## False Leads / Passed to Tree-Local Judge
- **Gas optimizations and style issues** identified by 4naly3er (e.g., using bools for storage, missing custom errors, pragma version) are not access-control vulnerabilities and should be filtered out by the tree-local judge.
- **Slither reentrancy warnings** on `LendingLedger.update_market` and `sync_ledger` — while flagged by Slither, the actual exploitability is limited because the external calls are to governance-controlled contracts (GaugeController), not user-controlled contracts. These should be evaluated in the full audit context.
- **Missing events on `setGovernance`** — while important for transparency, this is more of an operational concern than a direct loss-of-funds vector.

## Evidence Reviewed
- Full source of `LendingLedger.sol` (143 lines)
- Full source of `GaugeController.sol` (322 lines)
- Full source of `VotingEscrow.sol` (500+ lines)
- Test files: `LendingLedger.t.sol`, `GaugeController.t.sol`, `VotingEscrow.t.sol`
- 4naly3er automated report
- Slither analysis output
- README.md for scope and context
- `scope.txt` confirming only `LendingLedger.sol` is in scope

---

*Report generated by Access Control Specialist, Branch 1 of 1.*
