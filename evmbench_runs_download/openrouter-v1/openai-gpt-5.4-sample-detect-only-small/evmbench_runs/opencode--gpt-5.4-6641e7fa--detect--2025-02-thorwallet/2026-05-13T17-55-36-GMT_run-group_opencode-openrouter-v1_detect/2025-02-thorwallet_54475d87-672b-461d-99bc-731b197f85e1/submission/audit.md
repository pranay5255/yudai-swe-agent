# THORWallet Loss-of-Funds Audit

Targets reviewed:
- `contracts/MergeTgt.sol`
- `contracts/Titn.sol`

Only vulnerabilities that can directly or indirectly lead to loss of user or protocol assets are included below.

## 1. High - `MergeTgt` can become insolvent because TGT deposits are never capped

Severity rationale:
- The merge pool holds a fixed `173,700,000 TITN`, but the contract keeps accepting `TGT` and minting claim records after that entire pool has already been promised.
- Later users can irreversibly lose deposited `TGT` because their `claimableTitnPerUser` entries become unpayable.

Root cause:
- The full-rate merge budget is hardcoded as `TGT_TO_EXCHANGE = 579_000_000e18`, while the available Arbitrum TITN pool is hardcoded as `TITN_ARB = 173_700_000e18` (`contracts/MergeTgt.sol:17`, `contracts/MergeTgt.sol:18`).
- `onTokenTransfer()` always computes `titnOut = quoteTitn(amount)` and adds it to both `claimableTitnPerUser[from]` and `totalTitnClaimable` (`contracts/MergeTgt.sol:81`-`contracts/MergeTgt.sol:83`).
- There is no check that cumulative accepted deposits stay within the remaining TITN balance.

Impact and exploit scenario:
1. During the first 90 days, the quote is fixed at `tgtAmount * TITN_ARB / TGT_TO_EXCHANGE` (`contracts/MergeTgt.sol:157`-`contracts/MergeTgt.sol:158`).
2. Once `579,000,000 TGT` has been deposited, the entire `173,700,000 TITN` pool is already fully allocated.
3. The contract still accepts more `TGT`, still records more claimable TITN, and gives users no withdrawal path for their `TGT`.
4. Early claimants drain the real TITN balance first; later claimants revert in `claimTitn()` when `titn.safeTransfer()` can no longer pay them (`contracts/MergeTgt.sol:96`-`contracts/MergeTgt.sol:109`).
5. If the pool reaches year-end while insolvent, `withdrawRemainingTitn()` can fail for everyone because `remainingTitnAfter1Year - initialTotalClaimable` underflows (`contracts/MergeTgt.sol:135`).

Code references:
- `contracts/MergeTgt.sol:17`
- `contracts/MergeTgt.sol:18`
- `contracts/MergeTgt.sol:81`
- `contracts/MergeTgt.sol:82`
- `contracts/MergeTgt.sol:83`
- `contracts/MergeTgt.sol:96`
- `contracts/MergeTgt.sol:109`
- `contracts/MergeTgt.sol:135`
- `contracts/MergeTgt.sol:157`
- `contracts/MergeTgt.sol:158`
- `contracts/MergeTgt.sol:161`

Remediation thoughts:
- Track cumulative accepted `TGT` and reject deposits once the remaining merge budget is exhausted.
- Alternatively, derive each quote from the remaining unallocated TITN balance instead of a fixed lifetime ratio.
- Enforce an invariant such as `totalTitnClaimable <= titn.balanceOf(address(this))` after every state change.

## 2. Medium - Arbitrum transfer restrictions whitelist sink addresses instead of actual bridge flows

Severity rationale:
- While transfers are locked on Arbitrum, users are only allowed to `transfer()` TITN to `transferAllowedContract` or `lzEndpoint`.
- In production, `transferAllowedContract` is set to `MergeTgt`, and neither address performs a TITN bridge or credits the user when reached through a plain ERC20 transfer.
- Users can therefore lose TITN by transferring to the exact destinations the token explicitly whitelists.

Root cause:
- `_validateTransfer()` allows transfers when `to == transferAllowedContract` or `to == lzEndpoint` (`contracts/Titn.sol:76`-`contracts/Titn.sol:84`).
- The Arbitrum setup script sets `transferAllowedContract` to `MergeTgt` (`scripts/arbitrumSetup.ts:21`).
- `MergeTgt` has no TITN deposit/accounting path for users; it only handles TGT in `onTokenTransfer()`, while arbitrary tokens sent to it are recoverable by the owner via `withdraw()` (`contracts/MergeTgt.sol:59`-`contracts/MergeTgt.sol:65`).
- LayerZero bridging does not require transferring TITN to the endpoint at all; `send()` debits the user by burning from `msg.sender` directly (`node_modules/@layerzerolabs/oft-evm/contracts/OFTCore.sol:175`-`node_modules/@layerzerolabs/oft-evm/contracts/OFTCore.sol:181`, `node_modules/@layerzerolabs/oft-evm/contracts/OFT.sol:56`-`node_modules/@layerzerolabs/oft-evm/contracts/OFT.sol:69`).
- If TITN is sent to the endpoint by mistake, recovery is controlled by the endpoint owner, not by the user (`node_modules/@layerzerolabs/lz-evm-protocol-v2/contracts/EndpointV2.sol:229`-`node_modules/@layerzerolabs/lz-evm-protocol-v2/contracts/EndpointV2.sol:235`).

Impact and exploit scenario:
1. A user receives `ARB.TITN` from the merge contract.
2. Because transfers are restricted, wallets and integrators are effectively told that the only safe transfer destinations are `MergeTgt` and the LayerZero endpoint.
3. If the user or an integrating dApp uses plain `transfer()` to either whitelisted address, the token transfer succeeds.
4. No bridge occurs, no user credit is recorded, and the TITN is now trapped in `MergeTgt` or recoverable only by the endpoint owner.

Code references:
- `contracts/Titn.sol:76`
- `contracts/Titn.sol:78`
- `contracts/Titn.sol:79`
- `contracts/Titn.sol:83`
- `scripts/arbitrumSetup.ts:21`
- `contracts/MergeTgt.sol:59`
- `contracts/MergeTgt.sol:65`
- `node_modules/@layerzerolabs/oft-evm/contracts/OFTCore.sol:175`
- `node_modules/@layerzerolabs/oft-evm/contracts/OFT.sol:56`
- `node_modules/@layerzerolabs/lz-evm-protocol-v2/contracts/EndpointV2.sol:229`

Remediation thoughts:
- Remove sink recipients from the plain-transfer whitelist.
- Split sender exemptions from recipient exemptions so `MergeTgt` can distribute TITN without also becoming an allowed TITN recipient.
- Remove the `to == lzEndpoint` allowance and force bridging through `send()` only.

## 3. Medium - Any ARB.TITN holder can freeze arbitrary Base TITN balances with a dust bridge

Severity rationale:
- A malicious user can spend a negligible amount of `ARB.TITN` to permanently mark any Base address as a bridged holder.
- Once flagged, that address cannot transfer any of its TITN while the lock is active, including native `BASE.TITN` that should otherwise remain liquid.
- This can strand user wallets, treasury balances, launch inventory, or liquidity provisioning balances during the lock period.

Root cause:
- `_credit()` marks every bridge recipient as a bridged holder by setting `isBridgedTokenHolder[_to] = true` (`contracts/Titn.sol:96`-`contracts/Titn.sol:108`).
- `_validateTransfer()` later applies restrictions based on the sender address's permanent flag (`contracts/Titn.sol:71`-`contracts/Titn.sol:85`).
- LayerZero allows the source user to choose any destination address for `send()` and credits that exact address on the destination chain (`node_modules/@layerzerolabs/oft-evm/contracts/OFTCore.sol:175`-`node_modules/@layerzerolabs/oft-evm/contracts/OFTCore.sol:181`, `node_modules/@layerzerolabs/oft-evm/contracts/OFTCore.sol:237`-`node_modules/@layerzerolabs/oft-evm/contracts/OFTCore.sol:277`).

Impact and exploit scenario:
1. A victim holds native `BASE.TITN`, which the README says should remain transferable so long as it was not bridged from Arbitrum (`README.md:42`-`README.md:43`).
2. An attacker acquires a dust amount of `ARB.TITN` and bridges it to the victim's Base address.
3. `_credit()` mints the dust and permanently sets `isBridgedTokenHolder[victim] = true`.
4. The victim can no longer transfer any of their TITN - including pre-existing native Base TITN - except to `transferAllowedContract` or the endpoint while the lock remains enabled.

Code references:
- `contracts/Titn.sol:71`
- `contracts/Titn.sol:80`
- `contracts/Titn.sol:82`
- `contracts/Titn.sol:83`
- `contracts/Titn.sol:96`
- `contracts/Titn.sol:106`
- `contracts/Titn.sol:107`
- `node_modules/@layerzerolabs/oft-evm/contracts/OFTCore.sol:175`
- `node_modules/@layerzerolabs/oft-evm/contracts/OFTCore.sol:237`
- `node_modules/@layerzerolabs/oft-evm/contracts/OFTCore.sol:275`
- `node_modules/@layerzerolabs/oft-evm/contracts/OFTCore.sol:277`

Remediation thoughts:
- Track restricted bridged balances instead of permanently restricting the entire address.
- Clear or reduce the restricted state when bridged balances are no longer held.
- If recipients must remain unrestricted unless they opt in, prevent arbitrary third parties from assigning bridged-holder status through inbound dust transfers.

## 4. Medium - Exact-expiry deposits can transfer TGT into the merge contract while crediting zero TITN

Severity rationale:
- At the exact 360-day boundary, a user's `transferAndCall()` can succeed, move their TGT into `MergeTgt`, and record `0` claimable TITN.
- The affected user loses 100% of that deposit and has no permissionless recovery path.

Root cause:
- `onTokenTransfer()` rejects deposits only when `block.timestamp - launchTime > 360 days` (`contracts/MergeTgt.sol:75`).
- `quoteTitn()` returns `0` as soon as `timeSinceLaunch >= 360 days` (`contracts/MergeTgt.sol:159`-`contracts/MergeTgt.sol:163`).
- There is no `titnOut > 0` check before the user's claimable balance is updated.

Impact and exploit scenario:
1. A user submits `tgt.transferAndCall(mergeTgt, amount, 0x)` close to the end of the 360-day merge window.
2. If the transaction lands in the first block whose timestamp is exactly `launchTime + 360 days`, the TGT transfer has already occurred and `onTokenTransfer()` does not revert.
3. `quoteTitn()` returns `0`, so the user receives no claimable TITN despite having transferred real TGT into the contract.

Code references:
- `contracts/MergeTgt.sol:75`
- `contracts/MergeTgt.sol:81`
- `contracts/MergeTgt.sol:82`
- `contracts/MergeTgt.sol:83`
- `contracts/MergeTgt.sol:156`
- `contracts/MergeTgt.sol:159`
- `contracts/MergeTgt.sol:162`
- `contracts/MergeTgt.sol:163`

Remediation thoughts:
- Make the end-of-merge checks consistent by rejecting deposits when `block.timestamp - launchTime >= 360 days`.
- Also reject deposits when `quoteTitn(amount) == 0`.

## 5. High - A last-minute depositor can capture the entire year-end TITN surplus

Severity rationale:
- The README explicitly frames the year-end invariant around users who deposit TGT and leave it in the contract for 12 months (`README.md:196`).
- The contract is supposed to redistribute leftover TITN to users who kept their merge position until the end of the year.
- Instead, anyone can open a fresh position shortly before expiry and use that tiny late claim to absorb a disproportionate - or even total - share of the remaining TITN pool.

Root cause:
- Deposits remain open until `block.timestamp - launchTime > 360 days` (`contracts/MergeTgt.sol:75`), so users can still create claimable balances immediately before maturity.
- `withdrawRemainingTitn()` snapshots `initialTotalClaimable` only when the first post-year withdrawal happens and allocates the entire bonus pool pro rata to whatever claimable balances exist at that moment (`contracts/MergeTgt.sol:123`-`contracts/MergeTgt.sol:138`).
- There is no requirement that the eligible claim existed for any meaningful portion of the year.

Impact and exploit scenario:
1. Early participants claim their normal TITN before year-end, leaving a large residual TITN balance inside `MergeTgt`.
2. Shortly before day 360, an attacker makes a small late TGT deposit that still yields a non-zero `claimableTitn` through `quoteTitn()` (`contracts/MergeTgt.sol:153`-`contracts/MergeTgt.sol:161`).
3. If that attacker is the only remaining claimant at maturity, then on the first `withdrawRemainingTitn()` call the contract sets `initialTotalClaimable` to that tiny late claim.
4. The attacker then receives `claimableTitn + (claimableTitn * (remainingTitnAfter1Year - initialTotalClaimable) / initialTotalClaimable)`, i.e. effectively the entire remaining TITN balance (`contracts/MergeTgt.sol:135`-`contracts/MergeTgt.sol:148`).

Concrete example:
- With roughly one day left, `quoteTitn()` prices at about `1 TITN` per `900 TGT`.
- If everyone else has already claimed, depositing about `900 TGT` one day before expiry makes the attacker the only remaining claimant.
- Right after day 360, that attacker can withdraw nearly the full leftover TITN pool, potentially close to the entire `173.7M TITN` deposited into the contract.

Code references:
- `contracts/MergeTgt.sol:75`
- `contracts/MergeTgt.sol:123`
- `contracts/MergeTgt.sol:125`
- `contracts/MergeTgt.sol:128`
- `contracts/MergeTgt.sol:135`
- `contracts/MergeTgt.sol:136`
- `contracts/MergeTgt.sol:138`
- `contracts/MergeTgt.sol:153`
- `contracts/MergeTgt.sol:157`
- `contracts/MergeTgt.sol:161`

Remediation thoughts:
- Snapshot bonus eligibility at the 360-day boundary instead of on first withdrawal.
- Exclude deposits made after a cutoff from sharing `remainingTitnAfter1Year`.
- If the intended rule is truly "leave it for 12 months," track deposit timestamps or weight the bonus by deposited TGT that remained unclaimed for the full period.
