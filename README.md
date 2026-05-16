# SwiftDrop — Flash Sale Platform

> High-concurrency flash sale platform with atomic Redis reservations, real-time WebSocket sync, and ML-based bot detection architecture.

---

## 🏗️ Architecture Overview

```
Browser (React) ──── REST/JWT ─────► FastAPI (Port 8080)
    │                                      │           │
    │◄──── WebSocket (stock updates) ──────┤           │
    │                                ┌─────▼─────┐     │
    │                                │   Redis   │     │
    │                                │ Lua Script│     │
    │                                │ (Atomic)  │     │
    │                                └─────┬─────┘     │
    │                                      │           │
    │                               BackgroundTask      │
    │                                      │           │
    │                               ┌──────▼──────┐    │
    │                               │  PostgreSQL  │    │
    │                               └─────────────┘    │
    │                                                   │
    │             asyncio Scheduler ◄───────────────────┘
    │             (auto-activate events every 30s)

🤖 ML Bot Detection (Edge Layer — Architecture):
    Request → [Nginx/LB] → [Random Forest Classifier] → FastAPI
    Features: req_per_sec, click_latency_ms, is_mobile, header_consistency
    Model: backend/ML/bot_model.joblib (sklearn RandomForest, 100 estimators)
```

**Full architecture + edge cases document**: See [`architecture_solution_edgecases.md`]

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+, Node.js 18+, Docker

### 1. Start Infrastructure
```bash
docker-compose up -d
```

### 2. Backend
```bash
cd backend
python3 -m venv ../venv && source ../venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python3 init_db.py      # Create tables
PYTHONPATH=. python3 seed_data.py    # Seed admin + sample event
uvicorn app.main:app --reload --port 8080
```

### 3. Frontend
```bash
cd frontend && npm install && npm run dev
```

### 4. Test Concurrency
```bash
./venv/bin/python3 load_test.py
# 200 requests vs 100-unit stock → exactly 100 succeed, 100 rejected, 0 errors
```

---

## 🔐 Default Accounts

| Role | Email | Password |
|---|---|---|
| Admin | `admin@swiftdrop.com` | `password123` |
| Customer | `maya@swiftdrop.test` | `password123` |

> Public `/register` always creates **customer** accounts. Admins are created via `POST /api/v1/auth/admin/create` (requires admin JWT).

---

## 🌱 Environment Variables (`backend/.env`)

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/swiftdrop
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-super-secret-jwt-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=60
PROJECT_NAME=SwiftDrop
```

---

## 📋 API Reference

### Auth
| Method | Route | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register` | No | Register (always customer) |
| POST | `/api/v1/auth/login` | No | Login → JWT |
| GET | `/api/v1/auth/me` | JWT | Current user |
| POST | `/api/v1/auth/change-password` | JWT | Change password (strength validated) |
| POST | `/api/v1/auth/admin/create` | JWT (Admin) | Create admin account |

### Events
| Method | Route | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/events` | JWT | List all events + items |
| POST | `/api/v1/events` | JWT (Admin) | Create event (items: 100–500 stock each) |
| PUT | `/api/v1/events/{id}` | JWT (Admin) | Edit locked event |
| POST | `/api/v1/events/{id}/state` | JWT (Admin) | Force open/close |

### Purchases & Profile
| Method | Route | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/purchases` | JWT | Buy item (atomic Redis) |
| GET | `/api/v1/profile/orders` | JWT | Confirmed orders only |
| PATCH | `/api/v1/profile` | JWT | Update display name |

### WebSocket
```
ws://localhost:8080/ws/events/{event_id}
→ {"type": "STOCK_UPDATE", "item_id": 3, "new_stock": 97}
```

---

## 🔒 Security

- Passwords: **bcrypt hashed**, never stored in plain text
- Password policy: ≥ 8 chars, must include letter + digit (enforced on register & change-password)
- Auth: **JWT HS256** — all protected routes validate token on every request
- RBAC: Admin endpoints return HTTP 403 for non-admin tokens
- Deactivated users: rejected at login with HTTP 403

---

## 🤖 ML Bot Detection (Architecture)

**Model**: `backend/ML/bot_model.joblib` — Random Forest Classifier (100 estimators, sklearn)

**Training features**:
- `req_per_sec` — bots send unnaturally fast requests
- `click_latency_ms` — bot clicks have near-zero or irregular latency
- `is_mobile` — most bots don't emulate mobile headers
- `header_consistency` — bots often have missing/inconsistent browser headers

**Design**: The model is kept at the **edge/gateway layer** (Nginx → WAF sidecar), not embedded in FastAPI. This allows stateless, low-latency blocking before requests reach application code. Re-train: `cd backend/ML && python3 train.py`

---

## ⚠️ Key Edge Cases Handled

1. **Zero overselling** — Redis Lua atomic DECR prevents race conditions
2. **Weak passwords** — Rejected on register and change-password
3. **Deactivated accounts** — Blocked at login
4. **Bot traffic** — ML classifier at edge layer
5. **Auto event activation** — asyncio loop checks go_live_time every 30s
6. **Duplicate email** — DB unique constraint + application check
7. **Edit after live** — Backend rejects edits to live/closed events
8. **Sold-out guard** — Lua returns -2 when stock = 0, no partial sells

---

## 📁 Project Structure

```
SwiftDrop/
├── backend/
│   ├── ML/
│   │   ├── train.py           # Random Forest bot detection trainer
│   │   └── bot_model.joblib   # Trained model artifact
│   ├── app/
│   │   ├── api/v1/            # Routers: auth, events, purchases, profile
│   │   ├── core/              # Config, DB, Redis Lua, WebSocket Manager
│   │   ├── domain/            # SQLAlchemy models + Pydantic schemas
│   │   └── services/          # Auth, Event, Purchase business logic
│   ├── init_db.py
│   └── seed_data.py
├── frontend/
│   └── src/
│       ├── App.jsx             # All views + state management
│       ├── components/         # UI, Features, AuthScreen
│       ├── hooks.js            # useCountdown, useToast
│       └── api.js              # Shared fetch helpers
├── docker-compose.yml
└── load_test.py                # Concurrency proof test
```
