# Co-Habitat Backend: FastAPI Service

The Co-Habitat Backend is a high-performance, asynchronous REST API service built with Python 3.14+ and FastAPI. It interfaces with a PostgreSQL database to manage society billing, ledger transactions, security logbooks, interactive notices, and service desk assignments.

---

## 🛠️ Technology Stack

* **Web Framework**: [FastAPI](https://fastapi.tiangolo.com/) (fully asynchronous routing)
* **ASGI Server**: [Uvicorn](https://www.uvicorn.org/)
* **ORM**: [SQLAlchemy 2.0 (Async)](https://docs.sqlalchemy.org/)
* **Migration Engine**: [Alembic](https://alembic.sqlalchemy.org/)
* **Database Driver**: [asyncpg](https://github.com/MagicStack/asyncpg) (async driver for PostgreSQL)
* **Package & Dependency Manager**: [uv](https://github.com/astral-sh/uv)
* **Caching & Session Storage**: [Redis](https://redis.io/) (for OTP delivery tracking with automatic fallback)
* **Authentication**: Passwordless OTP flow with JWT (JSON Web Tokens) and Token Refresh Rotation
* **Validation**: [Pydantic v2](https://docs.pydantic.dev/) (request payloads & response serialization, with E.164 phone regex enforcement)

---

## 📂 Project Structure

```
backend/
├── app/
│   ├── api/v1/                # Endpoint routers
│   │   ├── auth.py            # Passwordless OTP requests, verification, and refresh
│   │   ├── complaints.py      # Helpdesk grievances, technician assignments, work history
│   │   ├── finance.py         # Financial ledger, expenses, budgets, invoices, payments
│   │   ├── notices.py         # Notice board postings, announcements, voting polls
│   │   ├── users.py           # User profile info, flat directories, and profile modifications
│   │   └── visitors.py        # Visitor pre-approvals, daily help directory, gate check-in/out
│   │
│   ├── core/                  # Engine settings & platform core
│   │   ├── config.py          # Environment settings configuration (Required SECRET_KEY, dynamic CORS)
│   │   ├── database.py        # PostgreSQL/SQLite Async Engine & DB session dependency
│   │   ├── deps.py            # FastAPI Dependencies (Auth verification, Role checks)
│   │   └── security.py        # JWT generation, Redis OTP cache operations, and verifications
│   │
│   ├── crud/                  # SQLAlchemy query transactional functions
│   ├── models/                # DB relational tables mapping (SQLAlchemy base models)
│   └── schemas/               # Request/Response validation schemas (Pydantic objects)
│
├── migrations/                # Alembic database migration revisions
├── scripts/                   # Seeding and helper terminal scripts
├── tests/                     # Asynchronous Integration Tests (pytest)
│
├── .env                       # Local development credentials
├── alembic.ini                # Alembic migration engine configuration
├── pyproject.toml             # Python dependencies and metadata configuration
└── uv.lock                    # Locked exact dependency tree
```

---

## 🔒 Production Hardening & Safety Features

### 1. Redis Caching & Memory Fallback
OTPs are cached inside Redis with a strict 5-minute TTL. The system will automatically fall back to local in-memory storage if the Redis server is unreachable, ensuring a seamless development flow.

### 2. Fail-Fast Security Setup
* `SECRET_KEY` is required in the environment variables without a default fallback. The app will throw a initialization error and fail fast on startup if the key is missing.
* CORS configuration accepts dynamic, comma-separated lists from the `BACKEND_CORS_ORIGINS` environment variable. A wildcard (`*`) is blocked in production mode.

### 3. Concurrency Safeguards
* **Advisory Lock**: When verifying registration for the first time, a database-level advisory lock prevents race conditions where concurrent registration workers each attempt to register the user as the initial `admin`.
* **Atomic Receipt Generation**: Payments fetch and lock the next sequential receipt number using a database `SELECT FOR UPDATE` transaction block to avoid collisions during concurrent payment processing.
* **SQLite WAL mode**: When running on SQLite locally, WAL mode, transaction busy timeouts (10s), and explicit transaction boundaries prevent database locking issues.

### 4. Input & Data Integrity
* **E.164 Regex Validation**: All incoming phone number payloads are validated using strict E.164 formats (`^\+[1-9]\d{1,14}$`).
* **Soft Delete**: Invoices and payments are soft-deleted by setting `is_deleted = True` and updating the `deleted_at` timestamp. Query layers automatically omit soft-deleted records.
* **DB-Level Enum Role Constraints**: A SQL-level check constraint on the `users` table prevents invalid roles from ever being stored.

### 5. Aggregate Optimizations
Dashboard statistics (billed, collected, pending, expenses) are calculated in a single-pass optimized SQL query, eliminating N+1 database operations.

---

## 🔑 Role-Based Access Control (RBAC)

The backend implements custom RBAC checks using FastAPI dependency injection (`RoleChecker` defined in `app/core/deps.py`):

1. **`admin` (RWA Committee)**: full access to create flats, bill flats (invoices), record society expenses, allocate budgets, publish polls/notices, and assign work orders.
2. **`resident` & `tenant`**: access to own flat invoices, pay outstanding dues, view financial summary & ledger (for transparency), pre-approve visitor passes, log new complaints, RSVP to events, and cast poll votes.
3. **`security` (Gate Guards)**: access to check-in/out pre-approved visitor passcodes, log unannounced walk-in guests, and view daily help rosters. **Finance/Ledger endpoints will return `403 Forbidden`**.
4. **`staff` (Technicians)**: access to view assigned work orders and transition status in Kanban. **Finance/Ledger endpoints will return `403 Forbidden`**.

---

## ⚙️ Development Setup

### 1. Prerequisites
Install `uv` (Fast Python Package Installer):
```bash
# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

### 2. Configure Environment Variables
Create a `.env` file in the `backend` directory (default database user is `postgres` with password `root`):
```env
DATABASE_URL=postgresql+asyncpg://postgres:root@localhost:5432/cohabitat
SECRET_KEY=super_secure_production_only_secret_key_string_min_32_chars
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
REDIS_URL=redis://localhost:6379/0
ENVIRONMENT=development
```

### 3. Run Migrations & Database Setup
Initialize the database schema by applying migrations:
```bash
uv run alembic upgrade head
```

### 4. Seed Database
Populate the database with mock flats, accounts, bills, and transactions for local testing:
```bash
uv run python scripts/seed.py
```

### 5. Launch API Server
```bash
uv run uvicorn main:app --reload
```
Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser to explore the interactive OpenAPI swagger documentation.

---

## 🧪 Running Integration Tests

Automated integration tests run against an isolated database configuration:
```bash
# Correctly set Python path and execute pytest
$env:PYTHONPATH="."
uv run pytest
```
Output:
```
======================== 7 passed in 6.16s =========================
```
Test categories covered:
* OTP credentials verification
* Token refresh flow & rotation
* Profile reads & updates
* Admin role protection guards
* Society invoicing & payments ledger checks
* Notice board and multi-choice poll casting
* Visitor gate entry verification
