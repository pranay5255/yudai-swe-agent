# Panoptic Loss-of-Funds Audit Report

## Scope
- `audit/src/HypoVault.sol`
- `audit/src/accountants/PanopticVaultAccountant.sol`

## Findings

### [H-01] `computeNAV()` double-counts underlying when a pool token already equals the vault underlying

**Severity rationale**
- High. `HypoVault` uses the accountant-reported NAV as the sole pricing input for both deposit fulfillment and withdrawal fulfillment. Any NAV overstatement causes real value transfer: new depositors can be minted too few shares, or withdrawing users can be paid too many underlying assets. This is a direct loss-of-funds condition.

**Root cause**
- For each pool, `computeNAV()` adds the vault-held spot balances of `token0` and `token1` into `poolExposure0` / `poolExposure1` whenever the corresponding `skipToken*` flag is false:
  - `audit/src/accountants/PanopticVaultAccountant.sol:197`
  - `audit/src/accountants/PanopticVaultAccountant.sol:202`
- If one of those tokens is already the vault `underlyingToken`, that balance is therefore already included in the pool exposure and later added into `nav` at:
  - `audit/src/accountants/PanopticVaultAccountant.sol:250`
- However, after the pool loop finishes, the function separately adds `IERC20Partial(underlyingToken).balanceOf(_vault)` again unless the literal underlying address was observed in `underlyingTokens`:
  - `audit/src/accountants/PanopticVaultAccountant.sol:253`
  - `audit/src/accountants/PanopticVaultAccountant.sol:258`
- This means the exact same underlying token balance is counted twice whenever it is both:
  1. held directly by the vault, and
  2. exposed as a pool token balance that contributes to the per-pool exposure.

**Why this is a real issue**
- The repository’s own passing test demonstrates the behavior. When both `token0` and `token1` are set to the vault underlying and the vault holds `1000e18` underlying, `computeNAV()` returns `2125e18`, which the test comments identify as `underlying(1000) + token0(1000) + collateral0(50) + collateral1(75)`:
  - `audit/test/PanopticVaultAccountant.t.sol:517`
  - `audit/test/PanopticVaultAccountant.t.sol:553`
- Economically, there is only one direct `1000e18` underlying balance in the vault. Counting it once as spot inventory and again as “standalone underlying” inflates NAV by `1000e18`.

**Impact**
- `HypoVault.fulfillDeposits()` computes the share mint amount from the accountant NAV:
  - `audit/src/HypoVault.sol:480`
  - `audit/src/HypoVault.sol:486`
- `HypoVault.fulfillWithdrawals()` computes withdrawal assets from the same NAV source:
  - `audit/src/HypoVault.sol:522`
  - `audit/src/HypoVault.sol:531`
- Therefore a duplicated underlying balance directly misprices shares and creates a loss channel:
  - during deposit fulfillment, depositors receive too few shares for their assets, gifting value to incumbent shareholders;
  - during withdrawal fulfillment, exiting users can reserve and later claim more assets than their shares should receive, diluting remaining shareholders.

**Exploit scenario**
1. The vault is configured with a Panoptic pool whose `token0` or `token1` is the same ERC20 as the vault `underlyingToken`.
2. The vault holds a large direct balance of that underlying.
3. The manager performs an otherwise normal `fulfillWithdrawals()`.
4. `computeNAV()` counts the underlying balance once inside pool exposure and once again at the end of the function.
5. `assetsReceived` is overstated, allowing withdrawing users to pull excess assets from the vault.

**Code references**
- `audit/src/accountants/PanopticVaultAccountant.sol:197`
- `audit/src/accountants/PanopticVaultAccountant.sol:202`
- `audit/src/accountants/PanopticVaultAccountant.sol:250`
- `audit/src/accountants/PanopticVaultAccountant.sol:253`
- `audit/src/accountants/PanopticVaultAccountant.sol:258`
- `audit/src/HypoVault.sol:480`
- `audit/src/HypoVault.sol:522`
- `audit/test/PanopticVaultAccountant.t.sol:517`
- `audit/test/PanopticVaultAccountant.t.sol:553`

**Proof-of-concept notes**
- A minimal repro already exists in the provided suite: `forge test --match-test test_computeNAV_exactCalculation_onlyUnderlyingToken`.
- That test passes today and confirms the overvaluation.

**Remediation thoughts**
- Track direct vault token balances globally and add each economic asset exactly once.
- If a pool token equals `underlyingToken`, do not add the standalone `underlyingToken.balanceOf(_vault)` again at the end.
- More generally, replace the current ad hoc `underlyingTokens` array bookkeeping with a canonical de-duplication scheme keyed by economic asset address.

## Notes
- I reviewed both in-scope contracts with focus on direct/indirect loss-of-funds paths.
- The README explicitly marks stale manager prices, differing array lengths, trusted-owner actions, and small rounding loss as known / invalid classes; those were excluded.
- I did not identify any additional distinct, credible loss-of-funds vulnerabilities beyond the NAV overvaluation issue above.
