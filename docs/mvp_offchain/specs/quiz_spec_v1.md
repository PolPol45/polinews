# quiz_spec_v1

## Format
- 2-3 questions per attempt.
- Runtime selection from story-level pool.
- Mix: at least 1 comprehension, at least 1 detail question.

## Pool requirements
- Target pool size: 10 candidate questions when possible.
- Minimum viable pool: 4 questions for short stories.
- Mark story as `quiz_not_available` if pool quality fails.

## Attempt rules
- Max attempts per story per day: 3.
- Cooldown between attempts: 120 seconds.
- One reward per story per account.

## Scoring
- Pass threshold: 70%.
- Award base credits only when pass=true.

## Anti-abuse checks
- Reject attempts with elapsed time below min threshold (configurable).
- Flag repeated identical answer patterns across accounts.
