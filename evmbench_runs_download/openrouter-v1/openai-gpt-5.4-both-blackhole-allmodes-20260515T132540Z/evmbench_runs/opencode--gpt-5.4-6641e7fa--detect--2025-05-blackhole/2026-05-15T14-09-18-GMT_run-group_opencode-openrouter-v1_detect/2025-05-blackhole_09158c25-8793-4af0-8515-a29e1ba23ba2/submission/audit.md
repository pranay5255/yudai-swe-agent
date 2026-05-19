# Blackhole second-pass audit report

## Findings

### 1. AVM-managed veNFT bribes are paid to child AVM vaults and become unrecoverable
- Severity: Medium
- Status: confirmed

Blackhole's AVM flow transfers veNFTs into per-bucket `AutoVotingEscrow` child contracts, not into the AVM manager itself (`/home/agent/audit/contracts/AVM/AutoVotingEscrowManager.sol:61-85`). Bribe claims, however, resolve the payout recipient as `ownerOf(tokenId)` and only special-case the AVM manager address (`/home/agent/audit/contracts/Bribes.sol:272-284`). Because the NFT owner is the child `AutoVotingEscrow` contract rather than the manager, claimed bribes are transferred to the child vault. `AutoVotingEscrow` only exposes lock-management helpers and has no ERC20 recovery/forwarding path (`/home/agent/audit/contracts/AVM/AutoVotingEscrow.sol:12-122`).

Exploit path:
1. A user enables auto-voting, so their veNFT is moved into an `AutoVotingEscrow` child (`/home/agent/audit/contracts/AVM/AutoVotingEscrowManager.sol:61-85`).
2. The user calls `GaugeManager.claimBribes(...)`, which correctly authorizes the original owner via `avm.getOriginalOwner(tokenId)` (`/home/agent/audit/contracts/GaugeManager.sol:519-524`, `/home/agent/audit/contracts/AVM/AutoVotingEscrowManager.sol:196-201`).
3. `Bribe.getReward()` transfers the bribe to `ownerOf(tokenId)`, i.e. the child AVM contract, because `_owner == avm` is false (`/home/agent/audit/contracts/Bribes.sol:272-284`).
4. The claimed bribe tokens remain stuck in the child AVM contract permanently.

### 2. `claim_many()` can permanently strand expired AVM rebases inside child AVM vaults
- Severity: Medium
- Status: confirmed

`RewardsDistributor.claim()` correctly reroutes expired AVM claims to the original owner by checking `avm.tokenIdToAVMId(tokenId)` and calling `avm.getOriginalOwner(tokenId)` (`/home/agent/audit/contracts/RewardsDistributor.sol:197-216`). The batch variant `claim_many()` omits this AVM handling and always transfers expired-lock rewards to `ownerOf(tokenId)` (`/home/agent/audit/contracts/RewardsDistributor.sol:219-245`). For auto-voted positions, `ownerOf(tokenId)` is the child `AutoVotingEscrow` vault (`/home/agent/audit/contracts/AVM/AutoVotingEscrowManager.sol:61-85`), which has no ERC20 escape hatch (`/home/agent/audit/contracts/AVM/AutoVotingEscrow.sol:12-122`). Because `claim_many()` is permissionless, any third party can trigger the loss once an AVM-held lock expires.

Exploit path:
1. A user leaves an expiring veNFT inside AVM.
2. After expiry, anyone calls `RewardsDistributor.claim_many([tokenId])` (`/home/agent/audit/contracts/RewardsDistributor.sol:219-245`).
3. The distributor transfers the matured BLACK rewards to `ownerOf(tokenId)`, i.e. the child AVM vault, instead of the original user (`/home/agent/audit/contracts/RewardsDistributor.sol:231-235`).
4. The rewards are stuck forever in the child vault.

### 3. Concentrated-route swaps ignore user slippage limits and can be sandwiched to near-zero output
- Severity: High
- Status: confirmed

All router entrypoints compute a quote with `getAmountsOut(...)` and only check that quoted amount against `amountOutMin` before execution (`/home/agent/audit/contracts/RouterV2.sol:541-560`, `563-585`, `587-600`, `603-626`). During execution, every concentrated-leg swap calls Algebra's `exactInputSingle` with `amountOutMinimum: 0` (`/home/agent/audit/contracts/RouterV2.sol:499-518`). This means the user's declared minimum output is never enforced on the actual concentrated swap. An MEV bot can move the CL price after the quote is read but before the swap executes, and the transaction will still settle at an arbitrarily bad price.

Exploit path:
1. Victim submits a swap containing at least one `routes[i].concentrated = true` hop with a protective `amountOutMin`.
2. The router quotes favorable output via `getAmountsOut(...)` and passes the pre-check.
3. A searcher sandwiches the transaction and moves the CL pool price.
4. `_swap()` still executes because `amountOutMinimum` is hardcoded to zero, so the victim receives far less than `amountOutMin` (`/home/agent/audit/contracts/RouterV2.sol:505-517`).

### 4. Empty genesis pairs can still be pre-seeded through `addLiquidityETH`, allowing launch-fund stranding/manipulation
- Severity: High
- Status: confirmed

Genesis pairs are supposed to reject third-party initial liquidity until the official genesis launch. The ERC20 path enforces this with `require(!(isGenesis(pair) && totalSupply()==0))` (`/home/agent/audit/contracts/RouterV2.sol:381-389`). The ETH path omits the same guard entirely (`/home/agent/audit/contracts/RouterV2.sol:391-415`). Once governance approves a genesis pool, `GenesisPoolManager` marks the empty pair as genesis (`/home/agent/audit/contracts/GenesisPoolManager.sol:148-169`, `/home/agent/audit/contracts/factories/PairFactory.sol:157-160`). If one side of the pair is WAVAX/WETH, an attacker can front-run launch by adding a tiny, highly skewed initial position through `addLiquidityETH`.

That poisoned reserve ratio is then consumed by the official launch, because `GenesisPool._addLiquidityAndDistribute()` ignores the actual token amounts returned by `router.addLiquidity(...)` and only records the LP minted (`/home/agent/audit/contracts/GenesisPool.sol:224-240`). Any unused native/funding tokens remain inside the genesis pool. On a full launch, `_setPoolStatus(PoolStatus.LAUNCH)` zeroes `refundableNativeAmount`, so stranded launch inventory is no longer claimable (`/home/agent/audit/contracts/GenesisPool.sol:205-217`, `253-281`).

Exploit path:
1. Governance approves a genesis pool whose funding side is WAVAX/WETH, which sets `isGenesis[pair] = true` while the pair is still empty (`/home/agent/audit/contracts/GenesisPoolManager.sol:148-169`).
2. An attacker calls `RouterV2.addLiquidityETH(...)` and seeds the empty genesis pair at an extreme price, bypassing the missing guard (`/home/agent/audit/contracts/RouterV2.sol:391-415`).
3. When the official genesis launch later calls `GenesisPool.launch(...)`, the router only uses the small "optimal" side that matches the attacker's skewed reserves, while the remainder stays in the genesis pool (`/home/agent/audit/contracts/GenesisPool.sol:224-240`).
4. Those leftover launch assets are stranded or economically compromised, causing direct loss to the token owner and/or genesis depositors.

### 5. Only the token owner is maturity-locked; genesis contributors can immediately unwrap their LP share
- Severity: Medium
- Status: confirmed

When genesis liquidity is staked into the launch gauge, the gauge records a maturity timestamp only for `tokenOwner` (`/home/agent/audit/contracts/GaugeV2.sol:221-233`). Contributor balances are not stored in `_balances`; instead, they are derived on demand from `GenesisPool.balanceOf(account)`, which gives depositors roughly half of the genesis LP and gives the token owner the remainder (`/home/agent/audit/contracts/GenesisPool.sol:323-327`). However, `GaugeV2._withdraw()` gates withdrawals solely on `maturityTime[msg.sender]` (`/home/agent/audit/contracts/GaugeV2.sol:271-285`). For every non-owner genesis contributor this value remains zero, so the maturity check is bypassed immediately after launch.

Exploit path:
1. A contributor deposits funding tokens into a genesis pool and waits for launch.
2. `GenesisPool.launch()` stakes all LP into the gauge, but `depositsForGenesis()` only sets `maturityTime[tokenOwner]` (`/home/agent/audit/contracts/GaugeV2.sol:221-233`).
3. The contributor calls `GaugeV2.withdraw(...)`; `_balanceOf(msg.sender)` includes their virtual genesis stake, and `block.timestamp >= maturityTime[msg.sender]` passes because their maturity is zero (`/home/agent/audit/contracts/GaugeV2.sol:271-323`).
4. The contributor receives transferable LP immediately and can burn it to extract both funding tokens and a pro-rata slice of the project's native launch inventory, defeating the intended lockup and draining launch liquidity early.

### 6. `swapExactTokensForTokensSimple()` ignores its `to` argument and can burn BLACK outputs to `address(0)`
- Severity: Medium
- Status: confirmed

`swapExactTokensForTokensSimple()` builds a one-hop `route` but never sets `route.receiver` (`/home/agent/audit/contracts/RouterV2.sol:541-546`). `_swap()` then ignores its `_to` argument and always forwards outputs to `routes[i].receiver` (`/home/agent/audit/contracts/RouterV2.sol:499-528`). For the simple helper, that receiver is the zero address. On vAMM/sAMM routes, `Pair.swap()` explicitly allows `to == address(0)` as long as it is not token0/token1 (`/home/agent/audit/contracts/Pair.sol:389-393`). BLACK itself does not reject zero-address transfers (`/home/agent/audit/contracts/Black.sol:55-65`). So a simple swap whose output token is BLACK will successfully send the purchased BLACK to `address(0)` instead of the user.

Exploit path:
1. A user calls `swapExactTokensForTokensSimple(..., tokenTo = BLACK, to = user, concentrated = false, ...)`.
2. The helper leaves `routes[0].receiver` unset (`/home/agent/audit/contracts/RouterV2.sol:541-546`).
3. `_swap()` routes the output to `address(0)` rather than the supplied `to` address (`/home/agent/audit/contracts/RouterV2.sol:499-528`).
4. `Pair.swap()` transfers BLACK to `address(0)`, burning the user's swap proceeds (`/home/agent/audit/contracts/Pair.sol:389-393`, `/home/agent/audit/contracts/Black.sol:55-65`).

## Rejected candidates / not credible

- `GenesisPoolManager.setRouter()` uses `require(_router == address(0))` (`/home/agent/audit/contracts/GenesisPoolManager.sol:313-316`), but this is an owner-only misconfiguration/DoS issue rather than an untrusted asset-loss path.
- `AutoVotingEscrowManager.setOriginalOwner()` is unimplemented (`/home/agent/audit/contracts/AVM/AutoVotingEscrowManager.sol:194-194`), but `getOriginalOwner()` does not rely on that mapping and instead derives ownership from the child AVM lock table (`/home/agent/audit/contracts/AVM/AutoVotingEscrowManager.sol:196-201`), so the empty setter is not itself a standalone loss-of-funds bug.
- The broader `route.receiver` / ignored `_to` behavior in multi-hop router entrypoints is dangerous UX, but for the generic `swapExactTokensForTokens(...)` / `swapExactETHForTokens(...)` APIs the caller explicitly supplies the full `route[]` and can set receivers themselves. I only treated the one-hop helper as a real loss path because it hardcodes an empty receiver while still exposing a misleading `to` parameter (`/home/agent/audit/contracts/RouterV2.sol:499-530`, `541-560`).
- `PairFactory.setReferralFee()` / `setCustomReferralFee()` do not cap referral bps (`/home/agent/audit/contracts/factories/PairFactory.sol:87-89`, `107-110`), but fee configuration is a trusted `feeManager` power in the stated threat model, so I did not count it as an exploitable privilege escalation.
- Re-using a launched `GenesisPool` for a second funding market looked risky because `GenesisPoolFactory.getGenesisPool()` returns the last non-`NOT_QUALIFIED` pool (`/home/agent/audit/contracts/factories/GenesisPoolFactory.sol:73-86`), but creating such a second market still requires governance-controlled whitelist/approval flow and did not yield a clean untrusted theft path from existing users.
