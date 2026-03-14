# reward_policy_v1

Policy version: `2026-03-05-v1`

## Credit rules
- `base_reward`: 10 credits for quiz pass.
- `bonus_reward`: +5 credits for valid comment.
- `daily_cap`: 50 credits per user.
- `new_user_multiplier`: 0.3 for first 7 days.

## Redemption rules
- Option A: subscription discount coupon.
- Option B: 24h premium access.
- Redemption must be idempotent.

## Revoke rules
- Allowed reasons: fraud, duplicate reward, policy violation.
- Revoke writes a negative ledger entry with reason code.
- Revoke cannot delete prior ledger entries.
