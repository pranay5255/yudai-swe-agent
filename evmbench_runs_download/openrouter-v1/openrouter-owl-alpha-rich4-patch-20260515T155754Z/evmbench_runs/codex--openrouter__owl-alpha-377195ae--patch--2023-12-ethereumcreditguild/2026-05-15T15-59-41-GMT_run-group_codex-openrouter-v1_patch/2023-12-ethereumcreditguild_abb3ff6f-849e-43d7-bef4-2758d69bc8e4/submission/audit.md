# Audit Report: Ethereum Credit Guild

## Critical Vulnerability Found

### [CRITICAL] `SurplusGuildMinter.getRewards()` reads `userStake` before loading from storage, causing incorrect slashing

**File:** `src/loan/SurplusGuildMinter.sol:226-236`

**Severity:** Critical — Can lead to loss of user funds through incorrect slashing

**Description:**

In the `getRewards()` function, the `slashed` flag is checked against `userStake.lastGaugeLoss` BEFORE `userStake` is loaded from storage. Since `userStake` is a memory variable that hasn't been assigned yet, its fields default to zero. This means:

1. `userStake.lastGaugeLoss` is always `0` during the check on line 229
2. The condition `lastGaugeLoss > uint256(userStake.lastGaugeLoss)` is always true when `lastGaugeLoss != 0`
3. Therefore, `slashed` is always set to `true` whenever there's a gauge loss, even if the user has already applied that loss via `GuildToken.applyGaugeLoss()`

**Impact:**

- Users who have already applied a gauge loss (by calling `GuildToken.applyGaugeLoss()`) will incorrectly be marked as `slashed` again
- When `slashed` is true, the user's `guildReward` is set to 0 (line 251), denying them rightful GUILD rewards
- More critically, when `slashed` is true, the user's entire stake is zeroed out (lines 263-270), effectively confiscating their CREDIT contribution to the surplus buffer
- This can result in users losing their staked CREDIT even after they've properly applied losses

**Proof of Code:**

```solidity
function getRewards(address user, address term)
    public
    returns (uint256 lastGaugeLoss, UserStake memory userStake, bool slashed)
{
    bool updateState;
    lastGaugeLoss = GuildToken(guild).lastGaugeLoss(term);
    // BUG: userStake is not yet loaded from storage, so userStake.lastGaugeLoss == 0
    if (lastGaugeLoss > uint256(userStake.lastGaugeLoss)) {
        slashed = true;
    }

    // userStake is loaded AFTER the check
    userStake = _stakes[user][term];
    if (userStake.stakeTime == 0)
        return (lastGaugeLoss, userStake, slashed);
    // ...
}
```

**Fix:**

Move the `userStake` storage read BEFORE the `slashed` check:

```solidity
function getRewards(address user, address term)
    public
    returns (uint256 lastGaugeLoss, UserStake memory userStake, bool slashed)
{
    bool updateState;
    lastGaugeLoss = GuildToken(guild).lastGaugeLoss(term);

    // Load userStake BEFORE checking slashed condition
    userStake = _stakes[user][term];
    if (userStake.stakeTime == 0)
        return (lastGaugeLoss, userStake, slashed);

    // Now correctly compare against the user's stored lastGaugeLoss
    if (lastGaugeLoss > uint256(userStake.lastGaugeLoss)) {
        slashed = true;
    }
    // ...
}
```

**Status:** ✅ Fixed

---

## Additional Observations

### [INFO] Profit sharing rounding behavior

As noted in the README, in profit distribution, the savings rate (CREDIT holders via rebase) can receive rewards even if the split is 0%, because of rounding down in the other splits. This is acknowledged as a known issue.

### [INFO] Rate limited gUSDC minter does not take creditMultiplier into account

As noted in the README, the rate-limited gUSDC minter's buffer size and replenish rate don't account for `creditMultiplier`. This is acknowledged as a known issue.
