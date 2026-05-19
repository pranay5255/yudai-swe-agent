# IdentityStaking audit report

## Scope

- Target: `audit/id-staking-v2/contracts/IdentityStaking.sol`
- Focus: vulnerabilities that could directly or indirectly lead to loss of user or protocol assets

## Executive summary

I reviewed the full in-scope `IdentityStaking` contract, its interface, the project documentation, and the supplied tests with emphasis on all token-moving and token-accounting flows:

- initialization and privileged control setup
- self/community staking and withdrawal
- slash accounting
- appeal/release accounting
- round transitions and burning
- upgrade authorization

I did not identify a credible, in-scope loss-of-funds vulnerability.

## Findings

### No confirmed loss-of-funds vulnerabilities found

After a full manual review, I did not find an unprivileged exploit path that enables:

- theft of user stake,
- unauthorized withdrawal of contract-held tokens,
- unauthorized release of slashed funds,
- improper burning of unslashed stake, or
- permanent loss of funds caused by inconsistent internal accounting,

subject to the trust assumptions explicitly documented by the project.

## Key review notes

### 1. Staking and withdrawals preserve custody boundaries

`selfStake()` and `communityStake()` only increase stake balances for `msg.sender` and then pull tokens from that same address via `transferFrom`:

- `audit/id-staking-v2/contracts/IdentityStaking.sol:229`
- `audit/id-staking-v2/contracts/IdentityStaking.sol:314`

`withdrawSelfStake()` and `withdrawCommunityStake()` only transfer unlocked, unslashed stake back to `msg.sender`:

- `audit/id-staking-v2/contracts/IdentityStaking.sol:285`
- `audit/id-staking-v2/contracts/IdentityStaking.sol:384`

There is no code path that transfers stake to an arbitrary third party.

### 2. Slashing only freezes value already attributed to the targeted stake

`slash()` computes the slash as a percentage of the current unslashed `amount`, subtracts it from the stake’s withdrawable balance, and adds it to `slashedAmount` and `totalSlashed[currentSlashRound]`:

- `audit/id-staking-v2/contracts/IdentityStaking.sol:424`
- `audit/id-staking-v2/contracts/IdentityStaking.sol:443`
- `audit/id-staking-v2/contracts/IdentityStaking.sol:473`

This prevents a slash from exceeding the currently tracked unslashed amount of the targeted stake. The only entity that can invoke this path is a trusted `SLASHER_ROLE`, which is explicitly part of the stated trust model.

### 3. Appeal releases restore stake accounting rather than leaking funds

`release()` does not transfer tokens out of the contract. Instead, it moves value from `slashedAmount` back into the relevant stake `amount`, and decrements `totalSlashed[slashRound]`:

- `audit/id-staking-v2/contracts/IdentityStaking.sol:535`
- `audit/id-staking-v2/contracts/IdentityStaking.sol:562`
- `audit/id-staking-v2/contracts/IdentityStaking.sol:573`
- `audit/id-staking-v2/contracts/IdentityStaking.sol:577`

That design matches the protocol description: appealed funds become staked funds again and remain withdrawable only under the normal lock rules.

### 4. Burn logic only burns matured slashed totals

`lockAndBurn()` burns exactly `totalSlashed[currentSlashRound - 1]`, then increments the round:

- `audit/id-staking-v2/contracts/IdentityStaking.sol:508`
- `audit/id-staking-v2/contracts/IdentityStaking.sol:512`
- `audit/id-staking-v2/contracts/IdentityStaking.sol:518`

Given the slash/release accounting, this mechanism burns only the currently outstanding amount attributed to the matured round. The consecutive-round rollover logic in `slash()` also prevents stale-but-unburned slash from becoming unreleasable.

### 5. Upgradeability is fully admin-trusted by design

The contract is UUPS-upgradeable and `_authorizeUpgrade()` is restricted to `DEFAULT_ADMIN_ROLE`:

- `audit/id-staking-v2/contracts/IdentityStaking.sol:218`

A malicious admin can always deploy a harmful implementation and seize or brick funds, but this is explicitly covered by the project’s trust assumptions in `audit/README.md` and is therefore not an in-scope vulnerability.

## Trust-assumption observations

These are important to fund safety, but they are consistent with the documented model rather than vulnerabilities:

- `DEFAULT_ADMIN_ROLE` is fully trusted, including for upgrades.
- `SLASHER_ROLE` is trusted to slash only legitimate stakes.
- `RELEASER_ROLE` is trusted to restore only legitimate appeals.
- `PAUSER_ROLE` can temporarily block withdrawals while paused, but cannot redirect funds.

## Conclusion

Within the project’s stated trust model and scope boundaries, I did not find a real loss-of-funds vulnerability in `IdentityStaking.sol`.
