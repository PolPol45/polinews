# Environment Naming Convention

- dev: local development and unstable tests.
- staging: pre-pilot validation environment.
- pilot: controlled live pilot environment.

Naming rules:
- Prefix logs with env name.
- Prefix dashboards with env name.
- Prefix DB names with env name.

Examples:
- `dev_ingestion_worker`
- `staging_api`
- `pilot_rewards_ledger`
