# PrelaunchPoints audit report

## Scope
- In-scope contract: `/home/agent/audit/src/PrelaunchPoints.sol`
- Focus: credible loss-of-funds issues only

## Findings

### 1. Untracked ETH can be redistributed or outright stolen because claims use the raw contract balance

Severity: Medium

`PrelaunchPoints` keeps explicit accounting only for ETH/WETH locked through the intended entry points (`totalSupply` and `balances[user][ETH]`) and for LRT balances stored in `balances[user][token]`.

However, the contract also accepts arbitrary ETH through `receive()` and never distinguishes tracked ETH from untracked ETH afterward:

- `_processLock()` is the only place that credits tracked ETH balances and `totalSupply` (`/home/agent/audit/src/PrelaunchPoints.sol:172`, `/home/agent/audit/src/PrelaunchPoints.sol:180`, `/home/agent/audit/src/PrelaunchPoints.sol:190`)
- `receive()` accepts arbitrary ETH without crediting any user (`/home/agent/audit/src/PrelaunchPoints.sol:392`)
- `convertAllETH()` deposits the entire `address(this).balance`, not just accounted ETH (`/home/agent/audit/src/PrelaunchPoints.sol:315`, `/home/agent/audit/src/PrelaunchPoints.sol:321`)
- LRT claims also convert the entire `address(this).balance` into `lpETH` for the current claimer (`/home/agent/audit/src/PrelaunchPoints.sol:257`, `/home/agent/audit/src/PrelaunchPoints.sol:262`)

This creates two loss-of-funds paths:

1. Before `startClaimDate`, any ETH accidentally or forcibly sent to the contract is silently folded into `convertAllETH()` and redistributed to ETH/WETH lockers even though it was never locked through the protocol.
2. After `startClaimDate`, the next user who claims with any allowed LRT can sweep all stray ETH already sitting in the contract, because `_claim()` mints `lpETH` from the full contract balance instead of the ETH delta produced by that specific swap.

The pre-conversion path is actively gameable because deposits remain open until the owner calls `setLoopAddresses()`. A late depositor can observe a mistaken ETH transfer, lock ETH/WETH afterward, and still receive a proportional share of the earlier donation when `convertAllETH()` runs.

Exploit scenario after launch:

1. The owner has already called `convertAllETH()`, so the contract is expected to hold no ETH.
2. A victim accidentally transfers ETH to the contract, or ETH is force-sent via `selfdestruct`.
3. An attacker with even a minimal allowed-LRT position calls `claim()`.
4. `_fillQuote()` swaps the attacker’s token, but `_claim()` then sets `claimedAmount = address(this).balance`.
5. The attacker receives `lpETH` backed by both their own swap output and the victim’s unrelated ETH.

Impact:

- Untracked ETH is not merely stuck; it can be reassigned to other users.
- After the claim phase starts, the next LRT claimer can steal all stray ETH in a single transaction.

Remediation ideas:

- Track ETH obtained from the current swap as a balance delta and deposit only that delta.
- Keep a dedicated accounting variable for tracked ETH and have `convertAllETH()` use that value instead of `address(this).balance`.
- Consider rejecting arbitrary ETH transfers except from WETH unwrapping / trusted swap flows, or add an ownerless rescue path for untracked ETH.

### 2. Supported tokens transferred directly to the contract become permanently unrecoverable

Severity: Low

The contract only credits user balances when assets are deposited through the lock functions, but it permanently blocks recovery of all supported assets:

- user balances live exclusively in `balances[user][token]` (`/home/agent/audit/src/PrelaunchPoints.sol:50`)
- `_processLock()` is the only code path that credits those balances (`/home/agent/audit/src/PrelaunchPoints.sol:172`)
- `recoverERC20()` explicitly forbids recovering any `isTokenAllowed[token]` asset (`/home/agent/audit/src/PrelaunchPoints.sol:379`, `/home/agent/audit/src/PrelaunchPoints.sol:380`)

As a result, if a user directly transfers any supported LRT or `WETH` to `PrelaunchPoints` instead of calling `lock()`, the tokens are never attributed to any account and also cannot be rescued by the owner. No later withdrawal or claim path can recover them because every user-facing redemption path reads from `balances`.

Exploit / loss scenario:

1. A user, router, bridge, or integration transfers a supported token directly to `PrelaunchPoints`.
2. The transfer succeeds, but no `balances[user][token]` entry is updated.
3. The owner cannot call `recoverERC20()` because the token is marked as allowed.
4. The assets remain trapped forever.

Impact:

- Any direct transfer of supported assets is permanently lost.
- This especially affects integrations that may use plain ERC20 `transfer()` instead of the lock API.

Remediation ideas:

- Add an explicit rescue flow for unaccounted balances of supported tokens.
- Alternatively, reject unsupported transfer paths at the integration layer and document that plain transfers are unrecoverable.

### 3. Directly transferred `lpETH` is mis-accounted: it is either socialized to ETH claimers or stuck forever

Severity: Low

`lpETH` is also treated as a protected asset that cannot be rescued, but it is never tracked with per-user accounting:

- `convertAllETH()` snapshots `totalLpETH` from the live `lpETH.balanceOf(address(this))` (`/home/agent/audit/src/PrelaunchPoints.sol:321`, `/home/agent/audit/src/PrelaunchPoints.sol:324`)
- ETH claimants redeem against that fixed snapshot (`/home/agent/audit/src/PrelaunchPoints.sol:248`, `/home/agent/audit/src/PrelaunchPoints.sol:249`)
- `recoverERC20()` permanently blocks rescue of `lpETH` (`/home/agent/audit/src/PrelaunchPoints.sol:379`, `/home/agent/audit/src/PrelaunchPoints.sol:380`)

Because of that, the outcome of a direct `lpETH` transfer depends entirely on timing:

1. If `lpETH` is sent to the contract after `setLoopAddresses()` but before `convertAllETH()`, the extra balance is included in `totalLpETH` and silently redistributed to ETH/WETH claimers.
2. If `lpETH` is sent after `convertAllETH()`, it is excluded from the frozen `totalLpETH` snapshot and becomes permanently stuck, because no user balance points to it and the owner cannot recover it.

In both cases the sender loses funds, and the protocol has no way to distinguish intentional protocol-owned `lpETH` from accidental direct transfers.

Remediation ideas:

- Account only for the `lpETH` amount minted by `convertAllETH()` instead of the full live `balanceOf(address(this))`.
- Add a rescue path for untracked `lpETH` that is provably outside the accounted claim pool.
