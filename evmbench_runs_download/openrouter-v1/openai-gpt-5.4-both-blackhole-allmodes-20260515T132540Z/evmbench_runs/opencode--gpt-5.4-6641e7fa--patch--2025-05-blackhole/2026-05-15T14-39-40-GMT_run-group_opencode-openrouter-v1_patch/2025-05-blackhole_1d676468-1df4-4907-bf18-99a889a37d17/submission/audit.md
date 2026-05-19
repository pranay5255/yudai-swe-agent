# Audit Report

## Fixed vulnerabilities

1. Genesis pool reinitialization could overwrite an active pool and strand earlier user deposits.
   - Fixed by requiring each `GenesisPool` instance to be initialized only once in `contracts/GenesisPool.sol`.
   - Fixed by making `contracts/GenesisPoolManager.sol` deploy a fresh pool for each new genesis attempt and reject reuse while an active pool already exists.

2. Genesis auction selection could be replaced by the token owner with arbitrary pricing logic.
   - Fixed by restricting `GenesisPool.setAuction` to the manager path only.
   - Fixed by validating new auction addresses against `IAuctionFactory.isAuction` in `contracts/GenesisPoolManager.sol`.

3. Genesis contributors could bypass the intended maturity lock and withdraw genesis-backed LP immediately after launch.
   - Fixed by tracking a pool-wide genesis maturity in `contracts/GaugeV2.sol` and limiting withdrawals to the user's non-genesis balance until that maturity expires.

4. CL gauge reward rollover could drop undistributed rewards because `GaugeCL.notifyRewardAmount` updated a shadowed local variable instead of storage.
   - Fixed by using the stored `rewardRate` for rollover math, updating storage with the recalculated rate, and refreshing `lastUpdateTime` in `contracts/AlgebraCLVe33/GaugeCL.sol`.

## Verification

- `npx hardhat compile`
