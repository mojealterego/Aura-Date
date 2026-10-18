# AURA Date · Relationship OS

**Status: early technical vertical slice — not authorized for public release.**

AURA Date is a dating platform built around intentional introductions rather than endless swiping. This repository starts from the supplied 19-page Polish architecture brief and turns its **core** into a testable monorepo. The brief's optional biometric, psychological and blockchain concepts are tracked separately, not assumed safe or production-ready.

## Repository layout

```text
apps/
  api/                FastAPI + SQLAlchemy / Python
    aura_api/          Auth, users, introductions, conversations, safety
    tests/             API integration tests
  mobile/             Expo + React Native / TypeScript
    src/               API client and design tokens
docs/
  ARCHITECTURE.md      Decisions, limitations, threat boundaries
  PRIVACY.md           Data practices and launch requirements
  ROADMAP.md           Implemented and pending engineering stages
.github/workflows/ci.yml
Dockerfile
compose.yaml
```

## Backend — local startup

Requires Python 3.11+.

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
uvicorn aura_api.main:app --reload --host 127.0.0.1 --port 8000
# On another terminal, from apps/api:
pytest -q
```

Local API: http://127.0.0.1:8000/docs · Health: http://127.0.0.1:8000/health/live

**Important:** API initializes local tables with SQLAlchemy `create_all`. Database migrations, rate limiting, confirmed adult identity and a staffed moderation process are missing. Do not publish this server on the internet.

## Mobile — development

Requires Node.js 20+ and a compatible Android or iOS device/emulator.

```bash
cd apps/mobile
npm install
# Set EXPO_PUBLIC_API_URL to a reachable backend:
# Android emulator example: http://10.0.2.2:8000
# Physical phone: http://<your-lan-ip>:8000
EXPO_PUBLIC_API_URL=http://10.0.2.2:8000 npm start
npm run typecheck
```

Set the mobile URL to your own backend's actual reachable address. When testing on a phone, an HTTP LAN endpoint is for development **only**; public deployment requires HTTPS. The backend must explicitly bind to an appropriate local interface for phone testing, and your local firewall must allow it. Never expose a debug server to the public internet.

The application currently supports creating an account, profile preferences, one daily introduction, incoming invitations, mutual consent, messaging, blocking, reporting and account deletion. All communication uses the same REST API. No image reveal, live AI interview, age identity verification or real biometric processing is claimed.

## Development containers

Copy `.env.example` to `.env` and set unique `AURA_SECRET_KEY` and `AURA_POSTGRES_PASSWORD` before running:

```bash
docker compose up --build
```

Compose is an **integration development configuration**, not a production deployment manifest. PostgreSQL is intended for later multi-user integration and migrations.

## Security / ethics baseline

- Adults-only intent is currently enforced by **self-reported age**, not verified age: **launch blocker**.
- Mutual opt-in required before chat. Chat concurrency cap is only locally enforced.
- Passwords are Argon2-hashed. Bearer tokens are 12-hour signed JWTs.
- Users can block, report and delete their own accounts and associated messages.
- Matching is deterministic and explainable based on age-range compatibility and self-declared values. It does not infer medical conditions or romantic chemistry.
- HRV, FaceTec, on-chain Karma and the Oracle interview from the brief are **not implemented**. See [architecture](docs/ARCHITECTURE.md) and [privacy](docs/PRIVACY.md).

## Engineering status

Track actual completion and deployment evidence in [ROADMAP.md](docs/ROADMAP.md). Passing unit tests or merging code does not constitute independent security clearance, GDPR compliance or readiness for production.
