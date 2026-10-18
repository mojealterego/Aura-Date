# AURA Date — living roadmap

Status legend: [x] code implemented; [~] partial; [ ] not implemented.
A checked item does not mean deployed or security-certified.

## P0 — monorepo foundation
- [x] Repository initialization and structural documentation
- [x] FastAPI app and relational core domain
- [x] Argon2 password hashing, short-lived signed JWT
- [x] Own-profile endpoints and controlled deletion
- [x] One introduction per UTC day, deterministic ranking and age-range rules
- [x] Mutual opt-in before chat and basic three-chat quota
- [x] Blocking, user-generated abuse reports, chat closing
- [x] Expo mobile UI for core interaction flows
- [x] Automated API tests and GitHub Actions definition
- [~] Local verification (check test outputs and CI run IDs separately)

## P1 — launch-blocking controls
- [ ] Verified adult age assurance; no minors onboarding
- [ ] Sessions: refresh-token rotation, revocation and device management
- [ ] Moderation dashboard, staff operations, appeal workflow and escalation
- [ ] API / login / message rate limits and anti-spam / anti-fraud controls
- [ ] Production PostgreSQL schema migrations and backups
- [ ] Transactional three-chat quota with PostgreSQL locking across nodes
- [ ] HTTPS, structured logs with PII redaction, metrics, tracing and alerts
- [ ] Secrets management, dependency lockfiles, SBOM, SAST/DAST, pentest
- [ ] End-to-end tests on Android and iOS; accessibility and localization
- [ ] Consent management, privacy notice, DPA/DPIA, deletion retention policy
- [ ] Protect private/public user data, media security, abuse response SLAs

## P2 — core AURA experience
- [ ] Progressive photo/voice reveal with mutually approved media grants
- [ ] Skan Duszy interactive voice onboarding with explicit opt-in
- [ ] Wyrocznia conversational assistance, prompt injection defenses and safety
- [ ] Anti-Chat shared quests and human-reviewed icebreaker library
- [ ] The Mirror privacy-respecting self-audit
- [ ] Quality and fairness evaluation of matching; user feedback controls
- [ ] Scheduling and safety tools for offline dates

## P3 — optional research, not baseline
- [ ] Feasibility of FaceTec provider SDK and alternative assurance routes
- [ ] HealthKit HRV only on specific opt-in, no emotion/chemistry inference
- [ ] Polygon KarmaSBT legal, ethics and erasure feasibility review
- [ ] Spotify integration with granular scopes and disconnect behavior

## Evidence required for release

- Green GitHub CI build linked to actual run ID and artifact hash.
- Two independent host integration tests with PostgreSQL and concurrent users.
- Privacy/security independent assessment and risk sign-off.
- Mobile app store requirements, clinical-claim review and operator acceptance.
