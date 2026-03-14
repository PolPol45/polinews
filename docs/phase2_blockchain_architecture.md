# Phase 2 Blockchain Architecture (v0.2)

## Objective
Enable on-chain `$POLI` claims after MVP validation using signed vouchers while keeping reading verification off-chain.

## Core contracts
- `PoliToken.sol` (ERC-20 utility token)
- `ReadingVault.sol` (USDC treasury plus emission controls)
- `RewardDistributor.sol` (ECDSA voucher verification and nonce anti-double-spend)

## Voucher flow
1. User completes off-chain verification.
2. Backend issues signed voucher with `user_address`, `amount_poli`, `story_id`, `nonce`, `expiry`.
3. User submits voucher on-chain to `RewardDistributor`.
4. Contract verifies signature and nonce uniqueness.
5. Contract calls vault/token for reward transfer or mint.

## Network rollout
- MVP testnet: Ethereum Sepolia.
- Main rollout target: Base or Arbitrum.
- Future optional route: Solana pool for lower transaction cost.

## Safety controls
- Max daily treasury outflow cap.
- Nonce registry to prevent replay.
- Pause role for emergency circuit breaker.
- Contract audit required before any mainnet deployment.

