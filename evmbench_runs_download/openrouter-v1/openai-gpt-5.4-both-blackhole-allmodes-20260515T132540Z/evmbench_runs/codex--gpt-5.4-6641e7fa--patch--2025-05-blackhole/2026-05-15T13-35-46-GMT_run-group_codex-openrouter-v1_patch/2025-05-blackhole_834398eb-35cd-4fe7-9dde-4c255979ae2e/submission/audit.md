# Audit Report

## Fixed vulnerability: Unauthorized reward claims in `RewardsDistributor`

- **Severity:** Medium
- **Impact:** Any account could call `claim()` or `claim_many()` for arbitrary veNFT token IDs.
- **Asset-loss angle:** For expired locks, this forced reward payout timing and transferred claimable emissions to the current owner/original AVM owner without their consent; for active locks, it forcibly compounded rewards into the lock. This lets third parties grief user reward management and force irreversible value movements.

### Root cause
`contracts/RewardsDistributor.sol` did not verify that the caller was the veNFT owner, an approved operator, or the AVM manager before processing claims for a token ID.

### Fix
- Added `_isApprovedOrOwnerOrAVM()` authorization helper.
- Gated both `claim()` and every entry in `claim_many()` with that authorization.
- Preserved AVM-driven claims by explicitly allowing the configured AVM manager for token IDs mapped into AVM.
- Aligned `claim_many()` expired-lock payout logic with `claim()` so AVM-owned locks pay the original owner.

### Files changed
- `audit/contracts/RewardsDistributor.sol`

### Validation
- Ran `npx hardhat compile` successfully.
