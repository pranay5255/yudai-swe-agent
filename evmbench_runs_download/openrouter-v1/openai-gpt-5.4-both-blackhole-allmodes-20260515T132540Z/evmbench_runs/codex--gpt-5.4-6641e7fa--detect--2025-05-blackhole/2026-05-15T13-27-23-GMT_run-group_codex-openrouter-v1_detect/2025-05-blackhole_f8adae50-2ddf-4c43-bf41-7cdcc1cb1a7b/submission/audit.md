# Blackhole Loss-of-Funds Audit Report

## Findings

### [HIGH] `GenesisPoolManager.setRouter` permanently bricks launches by only accepting the zero address

**Severity rationale**
A launched genesis pool is the only path that converts escrowed native/funding tokens into LP and stakes them for the token owner. If the owner ever uses `setRouter`, the function can only set `router` to `address(0)`, after which every subsequent launch path calls into the zero address and reverts. This can freeze all capital raised in approved genesis pools and strand both project tokens and contributor funding until governance migrates the system.

**Root cause**
`GenesisPoolManager.setRouter` contains an inverted validation:
- `require(_router == address(0), "ZA");` in `contracts/GenesisPoolManager.sol:313`

The manager therefore rejects every valid router address and only allows writing `address(0)` into storage. Later, launches unconditionally use `router`:
- `IGenesisPool(_genesisPool).launch(router, MATURITY_TIME);` in `contracts/GenesisPoolManager.sol:222`
- `IRouter(_router).addLiquidity(...)` in `contracts/GenesisPool.sol:225`

Calling `addLiquidity` on `address(0)` reverts, so `_launchPool` reverts and epoch processing cannot complete for affected pools.

**Impact**
Once `router` is set to zero, approved genesis pools can still accept funding deposits and even progress to `PRE_LAUNCH_DEPOSIT_DISABLED`, but they can no longer be launched into LP. The pool’s collected funding tokens and the project’s native tokens remain trapped in the genesis pool contract instead of being converted into LP and staked. This creates direct loss of access to user and protocol assets.

**Exploit scenario**
1. The system is operating normally and users deposit funding tokens into approved genesis pools.
2. The owner attempts a routine router update through `setRouter`.
3. Because of the inverted check, the only accepted value is `address(0)`, so `router` becomes zero.
4. At epoch flip, `_launchPool` calls `IGenesisPool.launch(router, ...)` with `router == address(0)`.
5. `GenesisPool.launch` reaches `_addLiquidityAndDistribute`, which calls `IRouter(address(0)).addLiquidity(...)` and reverts.
6. The launch never completes; native/funding assets remain locked inside the genesis pool instead of being turned into LP and distributed.

**Remediation**
Change the check to `require(_router != address(0), "ZA");` in `contracts/GenesisPoolManager.sol:313`.

### [HIGH] Genesis LP minted for contributors is not tracked in `GaugeV2`, causing contributor withdrawals to revert and their LP to become stuck

**Severity rationale**
After a genesis pool launches, contributor-owned LP is deposited into the gauge through `depositsForGenesis`. However, the gauge only increases `_totalSupply` and never credits any per-user balance. Because normal withdrawals deduct from `_balances[msg.sender]`, users whose position originates from genesis launch cannot withdraw their LP even after maturity. This strands contributor LP and the underlying assets it represents.

**Root cause**
During genesis launch, the entire LP position is transferred from the genesis pool to the gauge:
- `IGauge(liquidityPoolInfo.gaugeAddress).depositsForGenesis(genesisInfo.tokenOwner, ... , liquidity);` in `contracts/GenesisPool.sol:228`
- `TOKEN.safeTransferFrom(msg.sender, address(this), _totalAmount);` in `contracts/GaugeV2.sol:229`

But `GaugeV2._depositsForGenesis` only updates aggregate supply and the owner's maturity timestamp:
- `_totalSupply = _totalSupply + _totalAmount;` in `contracts/GaugeV2.sol:230`
- `maturityTime[_tokenOwner] = _timestamp;` in `contracts/GaugeV2.sol:231`

It never updates `_balances` for the token owner or any depositor.

Withdrawals still expose genesis balances via `balanceOf` by adding `IGenesisPool(genesisPool).balanceOf(account)`:
- `if(genesisPool != address(0)) balance += IGenesisPool(genesisPool).balanceOf(account);` in `contracts/GaugeV2.sol:179`

But `_withdraw` ultimately calls `_deductBalance`, which subtracts the non-genesis remainder from `_balances[msg.sender]`:
- `uint256 gaugeDeduction = _amount - genesisDeduction;` in `contracts/GaugeV2.sol:318`
- `_balances[msg.sender] = _balances[msg.sender] - gaugeDeduction;` in `contracts/GaugeV2.sol:320`

For a contributor whose entire position comes from genesis, `genesisDeduction` is rounded down from proportional accounting in `GenesisPool.deductAmount` and can be smaller than `_amount`, while `_balances[msg.sender]` remains zero. The subtraction underflows and the withdrawal reverts.

**Impact**
Genesis contributors can see a positive gauge balance, accrue emissions, and wait until maturity, but are unable to withdraw the LP that represents their funded position. Their liquidity remains trapped inside the gauge, creating direct loss of access to contributor funds.

**Exploit / failure scenario**
1. A genesis pool launches and mints `liquidity` LP tokens.
2. `GenesisPool.launch` deposits the full LP amount into the gauge through `depositsForGenesis`.
3. The gauge increases `_totalSupply` but never assigns any `_balances` to contributors.
4. A contributor later calls `withdrawAll()` after maturity.
5. `GaugeV2._balanceOf` reports a positive balance because it includes `GenesisPool.balanceOf(contributor)`.
6. `_withdraw` calls `_deductBalance`; due to integer rounding, `genesisDeduction < _amount` for many positions, so `gaugeDeduction > 0`.
7. `_balances[contributor]` is still zero, so `_balances[msg.sender] - gaugeDeduction` underflows and the withdrawal reverts.
8. The contributor’s LP remains stuck in the gauge.

**Code references**
- `contracts/GenesisPool.sol:228`
- `contracts/GaugeV2.sol:228`
- `contracts/GaugeV2.sol:230`
- `contracts/GaugeV2.sol:179`
- `contracts/GaugeV2.sol:318`
- `contracts/GaugeV2.sol:320`
- `contracts/GenesisPool.sol:325`
- `contracts/GenesisPool.sol:332`

**Remediation**
Track genesis-deposited LP with real per-user balances inside the gauge instead of synthesizing balances from the external genesis pool. A robust fix is to mint/credit the corresponding contributor and owner balances in `_balances` when the genesis position is created, and make genesis accounting a source-of-truth for ownership splits rather than an auxiliary view-only addition.

### [MEDIUM] `liveNativeTokensIndex` is never cleared, allowing duplicate live entries that can permanently block epoch processing and freeze other pools

**Severity rationale**
Genesis launches and disqualifications are processed by iterating `liveNativeTokens`. The removal helper never clears the removed token’s index, so the same native token can later be approved again and inserted multiple times. Once duplicates exist, a later epoch flip can process a stale duplicate entry whose pool is already removed; because the code does not guard against `genesisFactory.getGenesisPool(nativeToken) == address(0)`, the loop attempts an external call to `address(0)` and reverts. Since `EpochController.performUpkeep` calls `genesisManager.checkAtEpochFlip()` before fee/reward distribution, this can halt epoch processing and freeze launches for unrelated pools, trapping assets.

**Root cause**
Approvals append the native token and record a 1-based index:
- `liveNativeTokens.push(nativeToken);` in `contracts/GenesisPoolManager.sol:165`
- `liveNativeTokensIndex[nativeToken] = liveNativeTokens.length;` in `contracts/GenesisPoolManager.sol:166`

Removal swaps with the last element and pops, but never deletes the removed token’s mapping entry:
- `liveNativeTokens[index - 1] = replacingAddress;` in `contracts/GenesisPoolManager.sol:263`
- `liveNativeTokens.pop();` in `contracts/GenesisPoolManager.sol:264`
- `liveNativeTokensIndex[replacingAddress] = index;` in `contracts/GenesisPoolManager.sol:265`

The old `liveNativeTokensIndex[nativeToken]` remains non-zero forever.

If the same token is approved again after a rejection/launch cycle, `approveGenesisPool` pushes it again without checking whether it is already marked live. Duplicate entries can therefore accumulate.

Later, `checkAtEpochFlip` blindly resolves the pool for each live token and immediately calls into it:
- `address _genesisPool = genesisFactory.getGenesisPool(nativeToken);` in `contracts/GenesisPoolManager.sol:198`
- `_poolStatus = IGenesisPool(_genesisPool).poolStatus();` in `contracts/GenesisPoolManager.sol:199`

If a duplicate stale entry remains after the real live entry was removed, `getGenesisPool(nativeToken)` can return `address(0)`, and `IGenesisPool(address(0)).poolStatus()` reverts.

**Impact**
A previously launched or rejected token can poison `liveNativeTokens` with stale duplicates. On a later epoch flip, the upkeep transaction reverts before processing other pools. This can prevent approved pools from launching and leave already-collected native/funding tokens stuck in their genesis pool contracts.

**Exploit / failure scenario**
1. A native token is approved for genesis and added to `liveNativeTokens`.
2. The pool is later removed from the live set after launch or rejection.
3. Because `liveNativeTokensIndex[nativeToken]` is not cleared, the protocol later approves a new genesis pool for the same native token and appends it again.
4. The token now appears twice in `liveNativeTokens`.
5. During a future epoch flip, one duplicate entry causes the new pool to launch and `_removeLiveToken(nativeToken)` removes only one occurrence.
6. The stale duplicate remains in `liveNativeTokens`.
7. The loop reaches the stale entry, `genesisFactory.getGenesisPool(nativeToken)` returns `address(0)` (no current live pool), and `IGenesisPool(address(0)).poolStatus()` reverts.
8. `EpochController.performUpkeep` reverts, halting further genesis launches and fee/reward distribution for the epoch. Capital in other pending genesis pools remains frozen.

**Code references**
- `contracts/GenesisPoolManager.sol:165`
- `contracts/GenesisPoolManager.sol:166`
- `contracts/GenesisPoolManager.sol:198`
- `contracts/GenesisPoolManager.sol:199`
- `contracts/GenesisPoolManager.sol:257`
- `contracts/GenesisPoolManager.sol:265`

**Remediation**
Delete the removed token’s index in `_removeLiveToken` (`delete liveNativeTokensIndex[nativeToken]`) and reject duplicate live insertions in `approveGenesisPool`, e.g. by requiring `liveNativeTokensIndex[nativeToken] == 0` before `push`.
