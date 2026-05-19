# THORWallet Loss-of-Funds Audit Report

## Scope
- `contracts/MergeTgt.sol`
- `contracts/Titn.sol`
- `contracts/interfaces/IMerge.sol`
- `contracts/interfaces/IERC677Receiver.sol`

## Findings

### [MED] Extra TITN present at the one-year snapshot can be captured by the owner instead of merge participants

**Severity rationale**
- The protocol’s documented invariant is that users who leave TGT in `MergeTgt` for 12 months should be able to claim their owed TITN plus a proportional share of any *remaining* TITN.
- `withdrawRemainingTitn()` computes each user’s bonus from a one-time balance snapshot, but `withdraw()` still lets the owner remove arbitrary TITN from the contract at any time.
- As a result, any TITN that becomes present in `MergeTgt` but is not incorporated into users’ fixed pro-rata formula can be permanently diverted by the owner rather than distributed to participants. This is a direct loss of assets that should otherwise accrue to users under the merge design.

**Root cause**
- The contract snapshots `remainingTitnAfter1Year` only once, on the first post-year withdrawal, and computes the distributable bonus as:
  - `unclaimedTitn = remainingTitnAfter1Year - initialTotalClaimable` in `contracts/MergeTgt.sol:123`
  - `userProportionalShare = (claimableTitn * unclaimedTitn) / initialTotalClaimable` in `contracts/MergeTgt.sol:136`
- That formula ignores any TITN that arrives after the first snapshot and also leaves final custody of any undistributed TITN entirely to the owner because `withdraw()` is unrestricted and can transfer out `titn` as well (`contracts/MergeTgt.sol:59`).

**Impact**
- Any TITN sent to `MergeTgt` outside the exact pre-funded accounting path can escape user distribution and be owner-withdrawable.
- This includes accidental transfers, operational top-ups, rescue deposits, or any TITN residue that is not modeled by `initialTotalClaimable` / `remainingTitnAfter1Year`.
- Users then receive less than the full remaining TITN pool, while the owner can extract the difference.

**Exploit / failure scenario**
1. Users deposit TGT over the year and some leave their `claimableTitnPerUser` unclaimed until after 360 days.
2. The first user calls `withdrawRemainingTitn()`, which snapshots `remainingTitnAfter1Year` and `initialTotalClaimable` (`contracts/MergeTgt.sol:123-128`).
3. Additional TITN is then present in the contract outside that snapshot path (for example, an accidental TITN transfer or an operational top-up intended for users).
4. Subsequent user withdrawals keep using the stale `remainingTitnAfter1Year` snapshot, so the newly present TITN is never included in `userProportionalShare` (`contracts/MergeTgt.sol:135-138`).
5. After all users have withdrawn, the leftover TITN remains in `MergeTgt` and the owner can take it using `withdraw()` (`contracts/MergeTgt.sol:59-61`).

**Why this is a real loss-of-funds issue**
- The README explicitly frames the 12-month path around users receiving “their share of TITN plus any remaining TITN left proportional to their deposit.”
- The implementation does not enforce that invariant for all TITN actually held by `MergeTgt`; instead it enforces distribution only for a frozen subset determined by the first post-year caller.
- Any excess TITN becomes owner-capturable rather than user-distributable.

**Code references**
- Snapshot initialization: `contracts/MergeTgt.sol:123`
- Frozen claimable baseline: `contracts/MergeTgt.sol:128`
- Bonus calculation: `contracts/MergeTgt.sol:135`
- User payout based on stale snapshot: `contracts/MergeTgt.sol:138`
- Owner withdrawal of arbitrary tokens, including `titn`: `contracts/MergeTgt.sol:59`

**Remediation thoughts**
- Disallow owner withdrawal of `titn` once merge is live, or at minimum once any user has accrued claimable TITN.
- In `withdrawRemainingTitn()`, compute each user’s share against the live remaining pool rather than a one-time static snapshot, or explicitly track an immutable distributable reserve and reject any external TITN transfers.
- If the intended behavior is that *all* TITN held by `MergeTgt` after one year belongs to participants, enforce that in code and add a dedicated rescue path only for clearly unrelated tokens.

## Conclusion
I found one credible in-scope loss-of-funds issue affecting `MergeTgt`’s year-end TITN distribution. I did not identify an additional distinct asset-loss vulnerability in `Titn.sol` beyond the documented owner-controlled transfer restrictions and expected admin trust assumptions.
