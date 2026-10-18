# AURA Date — architecture decision record

## Product principles

The source brief describes a relationship operating system (rOS), not a swipe catalog:
one introduction per day, explicit mutual consent, up to three active conversations,
progressive disclosure, the Oracle voice interview and later identity assurance.
The source PDF is the input design brief, **not** verified executable software.

## Initial implementation (phase 0)

```text
Expo / React Native (TypeScript)
          |
       HTTPS API
          |
FastAPI / Pydantic -> SQLAlchemy -> SQLite (local) / PostgreSQL (target)
          |
User + Introduction + Conversation + Message + Block + Report
```

Backend uses Argon2 password hashes and signed short-lived JWTs.
Authorization is derived from the bearer token; no client-supplied user ID is
trusted for ownership. The one-per-day introduction is constrained by a
database unique key (user/day). Matching currently uses reciprocal age ranges
and shared self-declared values, with deterministic HMAC tie-breaking.
The matching score is a heuristic, not scientific proof of compatibility.

The 20-message reveal stage is metadata only: there are no photos to reveal
yet. One message is counted when its length is at least 20 characters; this is
a mechanical threshold, **not** a semantic definition of a meaningful message.

## Planned modular boundaries

- Identity + age assurance: verified adult status with privacy-preserving provider.
- Consent and profile controls: granular opt-in and profile/data deletion.
- Matching service: eligibility, exclusions, transparency, fairness tests.
- Oracle: explicitly consented voice interaction; isolated PII and auditable prompts.
- Moderation: reporting, review queue, appeals, abuse rate limits.
- Media: private encrypted object storage, image safety, progressive reveal.
- Platform: Postgres migrations, Redis quota enforcement, distributed transaction testing.

## High-risk concepts from PDF — not approved for launch

1. FaceTec integration is provider-dependent and subject to contract/licensing,
   privacy impact assessment and robust age assurance. Facial biometric material
   must not pass into user-visible logs or a blockchain.
2. HRV is **not** an objective detector of romantic chemistry, consent, or
   emotional safety. No behavior or match decision may be based on it.
3. Fisher archetype-to-neurotransmitter claims are not an established
   diagnostic algorithm. Optional personality prompts must not be presented
   as medical or psychological diagnoses.
4. Public immutable on-chain reputation can conflict with deletion and
   privacy rights and may amplify harassment. KarmaSBT is not implemented.
5. The PDF's WebSocket example lacks authentication, request budgets,
   correct interruption handling and privacy controls; it is not reused.

## Known architectural constraints

This is a **testable vertical slice**, not a production-ready dating service.
`create_all` bootstrapping is limited to local development; production needs
Alembic migrations. Matching scans eligible candidates (non-scalable).
SQLite is not sufficient for transactional conversation quotas under
multi-host concurrency. Public launch is blocked on verified age checks,
moderation operations, rate limits, E2EE strategy, data retention policy,
privacy/legal review, threat modeling, accessibility and external testing.
