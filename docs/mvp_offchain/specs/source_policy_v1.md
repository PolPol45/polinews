# source_policy_v1

## Goals
- Reduce low quality and spam sources.
- Keep attribution clear and auditable.

## Policy fields per domain
- `domain`
- `status`: `allow`, `watch`, `deny`
- `reputation_score`: 0-100
- `last_reviewed_at`
- `notes`

## Runtime rules
- Drop sources with `status=deny`.
- Sources with `status=watch` are accepted but flagged.
- Minimum source quality score for story inclusion: 40.
- Story requires at least 1 allowed source.

## Review cadence
- Review top 50 domains weekly during pilot.
- Promote/demote only at checkpoint to avoid policy drift.
