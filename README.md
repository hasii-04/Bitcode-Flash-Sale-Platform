# Bitcode Flash Sale Platform

SwiftDrop is a Dockerized FastAPI, PostgreSQL, Redis, and static frontend flash-sale platform built for high-concurrency limited-stock events.

## Start Locally

```powershell
cd "C:\Users\ASUS VIVOBOOK\Downloads\Bitcode-Flash-Sale-Platform"
docker compose up --build
```

Backend health:

```text
http://localhost:8000/health
```

API docs:

```text
http://localhost:8000/docs
```

Frontend:

```text
frontend/index.html
```

## Environment

Docker Compose sets these automatically:

```text
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/swiftdrop
REDIS_URL=redis://redis:6379/0
SECRET_KEY=change-this-secret-for-local-dev
```

## Seeded Accounts

Seed data is created during backend startup.

- Customer: `maya@swiftdropdemo.com` / `password123`
- Admin: `admin@swiftdropdemo.com` / `password123`

Admin accounts are seeded in the database or created by an existing admin through the protected admin endpoint. Public registration always creates customer accounts only.

## Main Features

- Customer registration, login, logout token revocation, profile update, and password change.
- Admin-only event creation, locked-event editing, force open, force close, event dashboard, and customer activation controls.
- Customer marketplace with locked countdowns, live stock, sold-out states, and WebSocket stock updates.
- Purchase flow with atomic Redis stock reservation, payment confirmation, cancellation with stock release, duplicate-purchase prevention, and order history.
- Structured JSON API errors and role-protected backend routes.

## Architecture

See [docs/architecture-diagram.svg](docs/architecture-diagram.svg).

Purchase flow:

1. Customer clicks Buy Now.
2. FastAPI validates JWT and live event state.
3. Redis Lua script atomically checks stock and reserves one unit.
4. Backend creates a reserved order in PostgreSQL and broadcasts stock changes over WebSocket.
5. Customer confirms payment to mark the order confirmed, or cancels to release stock back through Redis.

## Edge Cases Covered

- Duplicate customer registration is rejected.
- Public admin self-registration is not available.
- Inactive users cannot log in.
- Non-admin users cannot access event and customer management endpoints.
- Locked events cannot be purchased.
- Live or closed events cannot be edited.
- Item stock is constrained to 100-500 units on event create/update.
- Sold-out items reject further purchase attempts.
- Duplicate item purchases by the same customer are rejected.
- Purchase buttons disable during request processing.
- Cancelled reservations release stock back to Redis and PostgreSQL.
- Logout revokes the current JWT.

## Useful Commands

Rebuild only the backend:

```powershell
docker compose build --no-cache backend
docker compose up --force-recreate
```

Open PostgreSQL shell:

```powershell
docker compose exec db psql -U postgres -d swiftdrop
```

## Machine Learning Bot Detection

To protect the high-concurrency flash sales from automated bots, a machine learning model is integrated directly into the FastAPI backend.

- **Trainer Agent (`backend/ml/train.py`)**: Trains a Scikit-Learn Random Forest Classifier on historical behavioral data (`backend/ml/bot_training_data.csv`).
- **Middleware Integration (`backend/app/main.py`)**: A custom `BotDetectionMiddleware` loads the trained model at startup. It evaluates incoming `POST /api/v1/purchases/*` requests by extracting 4 behavioral features from custom headers:
  - `X-Req-Per-Sec`
  - `X-Click-Latency-Ms`
  - `X-Is-Mobile`
  - `X-Header-Consistency`
- **Enforcement**: If the model predicts a `≥50%` probability that a request is a bot, it intercepts and rejects it immediately with a `403 Forbidden` response, safeguarding real customer stock.
- **Verification (`tests/verify_ml.py`)**: A standalone test suite that validates the model's accuracy by sending known human and bot profiles against the live API.
