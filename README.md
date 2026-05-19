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
* **Authentication**: Passwordless OTP flow with JWT (JSON Web Tokens)
* **Validation**: [Pydantic v2](https://docs.pydantic.dev/) (request payloads & response serialization)

---

## 📂 Project Structure

```
backend/
├── app/
│   ├── api/v1/                # Endpoint routers
│   │   ├── auth.py            # Passwordless OTP requests and verification
│   │   ├── complaints.py      # Helpdesk grievances, technician assignments, work history
│   │   ├── finance.py         # Financial ledger, expenses, budgets, invoices, payments
│   │   ├── notices.py         # Notice board postings, announcements, voting polls
│   │   ├── users.py           # User profile info & flat directories
│   │   └── visitors.py        # Visitor pre-approvals, daily help directory, gate check-in/out
│   │
│   ├── core/                  # Engine settings & platform core
│   │   ├── config.py          # Environment settings configuration
│   │   ├── database.py        # PostgreSQL Async Engine & DB session dependency
│   │   ├── deps.py            # FastAPI Dependancies (Auth verification, Role checks)
│   │   └── security.py        # Token signature generation and password utilities
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
SECRET_KEY=dev_secret_key_for_jwt_tokens_generation_change_in_production
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### 3. Run Migrations & Database Setup
Initialize the PostgreSQL schema by applying migrations:
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

Automated integration tests run against an isolated database configuration (using SQLite/Postgres as configured in `conftest.py`):
```bash
# Correctly set Python path and execute pytest
uv run python -m pytest
```
Output:
```
======================== 6 passed in 3.77s =========================
```
Test categories covered:
* OTP credentials verification
* Profile reads
* Admin role protection guards
* Society invoicing & payments ledger checks
* Notice board and multi-choice poll casting
* Visitor gate entry verification
