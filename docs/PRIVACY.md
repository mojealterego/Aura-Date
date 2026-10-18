# AURA Date — privacy and trust obligations

This is a working engineering policy draft, **not legal advice or an adopted public privacy notice**.

## Baseline data fields

- Registration: email, Argon2-hashed password, chosen display name, self-declared age.
- Profile: free-text biography, 1-10 self-chosen values, age preference range.
- Interactions: one introduction per UTC day, optional mutual acceptance,
  messages, manually created reports and block relationships.
- API bearer token is stored using Expo SecureStore on device.
- The server does not deliberately store facial scans, health readings,
  voice audio, precise GPS or wallet identifiers in this phase.

## Protections already coded

- Users only access introductions and conversations in which they participate.
- A conversation is created only after both participants explicitly accept.
- Blocking closes conversations; deletion removes related conversations,
  messages, reports, introductions and account records from the active database.
- Reports are not automatically converted into punitive reputation scores.

## Before beta with real participants

- Verify that users are adults; self-declaration is inadequate for deployment.
- Define and obtain appropriate legal basis and consent where necessary.
- DPIA for profiling and any later biometric/health processing; implement
  access, export, rectification, erasure, and consent-withdrawal workflows.
- Establish a retention schedule for backups, moderation evidence,
  access logs, fraud detection and incident investigation.
- Add encryption in transit, at rest, secret rotation and secure logging.
- Staff a moderation and appeal process, including urgent safety reports.
- Conduct data breach response exercises and verify backup deletion limits.
- Validate whether automated compatibility recommendations are explainable
  and offer manual control and an alternative to profiling.

## Features explicitly NOT authorized

- Publishing biometrics or immutable reputation scores on a public chain.
- Treating HRV/heart metrics as indicators of romance, safety or consent.
- Invisible AI monitoring of private conversations without explicit consent.
- Making medical or psychiatric diagnostic claims from a voice interview.

Any later biometric subsystem must be optional when feasible, minimized,
isolated, auditable and reviewed separately before collecting real data.
