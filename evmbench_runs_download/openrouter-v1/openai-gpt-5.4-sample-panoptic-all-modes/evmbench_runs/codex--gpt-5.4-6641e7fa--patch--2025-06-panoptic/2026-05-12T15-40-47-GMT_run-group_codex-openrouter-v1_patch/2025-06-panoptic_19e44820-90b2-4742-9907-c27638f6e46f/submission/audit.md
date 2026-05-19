# Audit Report

## Fixed: deposit frontrun via external asset donation

- **Severity:** High
- **Component:** `src/HypoVault.sol`
- **Root cause:** `fulfillDeposits()` priced new shares using the accountant NAV minus only queued deposits and reserved withdrawals. Any underlying tokens transferred directly into the vault after a victim queued a deposit but before the manager fulfilled that epoch were still counted in `totalAssets`, while the victim's own queued deposit was excluded.
- **Impact:** An attacker could wait for a victim deposit, donate or otherwise force underlying into the vault, then queue a small deposit in the same epoch. Because the donation inflated `totalAssets`, the epoch minted too few shares for all queued deposits. The attacker could then redeem the underpriced shares for a disproportionate share of the donated assets, indirectly siphoning value from existing shareholders / the platform's asset pool.
- **Fix:** `fulfillDeposits()` now removes the vault's full underlying token balance from the pre-mint asset base, rather than only subtracting the current epoch's queued deposits. This prices deposits strictly against pre-existing strategy NAV and prevents idle underlying donations from diluting new share issuance. A bound check was also added so `assetsToFulfill` cannot exceed the epoch's queued deposits.
