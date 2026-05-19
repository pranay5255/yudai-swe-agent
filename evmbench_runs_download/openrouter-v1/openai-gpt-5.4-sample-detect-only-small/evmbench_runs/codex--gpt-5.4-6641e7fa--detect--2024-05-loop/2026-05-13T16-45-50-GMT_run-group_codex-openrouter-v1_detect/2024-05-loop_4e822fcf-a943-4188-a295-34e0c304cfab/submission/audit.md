# LoopFi PrelaunchPoints Audit Report

## Scope
- In-scope contract: `audit/src/PrelaunchPoints.sol`
- Focus: vulnerabilities that can directly or indirectly lead to loss of user or protocol assets.

## Findings

### [H-01] Any ETH forcibly present in the contract can be stolen by the next LRT claimer

**Severity rationale**
- High: stray ETH held by `PrelaunchPoints` is fully assignable to whichever user claims a non-ETH position next, allowing direct theft of assets that do not belong to that claimant.

**Description**
- The contract assumes that, when an LRT claim is executed, the contract holds no ETH except the proceeds of that claimant's just-executed 0x swap.
- This assumption is explicitly documented in code, but it is not enforced. In `_claim()`, the non-ETH branch converts the user's token to ETH via `_fillQuote()`, then mints `lpETH` using **the contract's entire ETH balance**:
  - `_fillQuote()` performs the swap and leaves the bought ETH in the contract.
  - `_claim()` then sets `claimedAmount = address(this).balance` and deposits that full amount into `lpETH` for the current claimant.
- Because `receive()` is unrestricted, anyone can force-send ETH to the contract (e.g. via `selfdestruct`) or accidentally transfer ETH directly. Those funds are not tracked in `balances`, are not recoverable by `recoverERC20()`, and are not excluded from later claim calculations.
- As a result, the next user claiming any non-ETH token receives `lpETH` backed by both their own swap output **and all pre-existing ETH in the contract**, stealing that ETH from its rightful owner/source.

**Root cause**
- The non-ETH claim path uses a global balance snapshot (`address(this).balance`) instead of the delta introduced by the claimant's swap.
- The contract accepts arbitrary ETH in `receive()` and has no accounting or rescue path for it.

**Impact**
- Any ETH accidentally sent or forcibly pushed into the contract can be extracted by an arbitrary LRT claimant.
- Depending on integrations, this can also sweep ETH left behind by unexpected exchange behavior or operational mistakes.

**Exploit scenario**
1. Someone accidentally transfers ETH to `PrelaunchPoints`, or an attacker force-sends ETH via `selfdestruct`.
2. A user with any non-ETH balance calls `claim()` or `claimAndStake()`.
3. `_fillQuote()` swaps only that user's LRT amount.
4. `_claim()` computes `claimedAmount = address(this).balance`, which now includes both the swap proceeds and the unrelated ETH.
5. The claimant receives `lpETH` for the full amount, capturing ETH that did not belong to them.

**Code references**
- Unrestricted ETH reception: `audit/src/PrelaunchPoints.sol:392`
- Vulnerable assumption/comment: `audit/src/PrelaunchPoints.sol:257`
- Swap leaves ETH in contract: `audit/src/PrelaunchPoints.sol:491`
- Claim mints against full contract ETH balance: `audit/src/PrelaunchPoints.sol:262`
- Global ETH conversion also relies on raw balance accounting: `audit/src/PrelaunchPoints.sol:321`

**Proof-of-concept sketch**
```solidity
// 1. Force-send 10 ETH to PrelaunchPoints via selfdestruct from another contract.
// 2. Attacker locks a small amount of an allowed LRT.
// 3. After claim period starts, attacker calls claim(LRT, 100, ..., valid0xData).
// 4. Suppose the swap yields 1 ETH.
// 5. _claim() deposits address(this).balance == 11 ETH and sends attacker 11 lpETH.
```

**Remediation thoughts**
- In `_claim()` non-ETH path, calculate the ETH delta around `_fillQuote()` and deposit only that delta, mirroring the pattern already used inside `_fillQuote()`:
  - record `ethBefore = address(this).balance`
  - execute `_fillQuote()`
  - set `claimedAmount = address(this).balance - ethBefore`
- Consider rejecting unsolicited ETH except from `WETH.withdraw()` / the exchange proxy, or adding an explicit ETH rescue/accounting mechanism that cannot dilute claim fairness.

## Notes
- I reviewed the rest of the in-scope code for direct loss-of-funds vectors, including reentrancy on `withdraw()` / `claim()`, proportional ETH distribution, token recovery, timelock gating, and 0x calldata validation. I did not identify additional credible asset-loss issues beyond the finding above.
