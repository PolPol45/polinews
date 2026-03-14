# compliance_data_policy_v1

Version: 2026-03-14-v1

## Purpose
Define GDPR-safe data export rules and MiCA-safe token communication rules for Poli-News v0.2.

## GDPR and data export rules
- Exported datasets must be pseudonymized before leaving the transactional DB.
- `user_id` is replaced with a rotating daily hash.
- No direct PII fields are allowed in export payloads.
- Data buyers must sign a DPA before receiving any export.
- `DELETE /user/data` must remove user-linked behavioral records from export-ready datasets.

## Annotation data policy
- Users are informed in terms of service that quiz interactions can improve AI systems.
- No biometric or special category data is collected.
- Annotation task exports require campaign_id traceability and consent-compatible legal basis.

## MiCA-safe communication rules
- `$POLI` is described as utility token only.
- No promise of appreciation, dividends, or fixed yield.
- Public docs must state token value is not guaranteed.
- Phase 2 mainnet rollout requires legal review before EU launch.

## Operational controls
- Audit log retained for every dataset export.
- Export access requires researcher or buyer API key.
- Emergency stop: pause all exports if compliance checks fail.

