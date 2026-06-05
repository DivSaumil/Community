# Production Deployment Guide (Free Tier)

This guide outlines the prerequisites, service configuration, and deployment steps for hosting the FastAPI backend on **Render**, database on **Neon**, and OTP cache on **online Redis**.

---

## 📋 Checklist & Prerequisites

Before deploying, ensure you have set up accounts on:
1. **[Render](https://render.com/)** (for backend hosting)
2. **[Neon](https://neon.tech/)** (for PostgreSQL database)
3. **[Upstash](https://upstash.com/)** or **[Redis Cloud](https://redis.com/)** (for online Redis)

---

## 🗄️ 1. Database Setup (Neon PostgreSQL)

Neon provides a serverless PostgreSQL database with a generous free tier.

### Step-by-Step Configuration:
1. Create a new project in your **Neon** console.
2. Under **Connection Details**, copy your connection string. It will look like this:
   `postgresql://username:password@ep-cool-darkness-123456.us-east-2.aws.neon.tech/neondb?sslmode=require`
3. **Database URL Scheme (Auto-Handled)**:
   SQLAlchemy's `asyncpg` driver requires the connection scheme `postgresql+asyncpg://` and prefers `ssl=require` over `sslmode=require`. 
   *Note: We have updated `config.py` in the backend codebase to automatically rewrite `postgres://` or `postgresql://` to `postgresql+asyncpg://` and swap `sslmode=require` with `ssl=require`. You can paste the Neon connection string directly into your environment variable without manual edits!*
4. **Neon Serverless Inactivity**:
   Neon puts inactive databases to sleep after 5 minutes of inactivity. The backend is configured with `pool_pre_ping=True` in `app/core/database.py` to automatically wake the database up and handle reconnects when requests arrive.

---

## 🔴 2. OTP Store Setup (Online Redis)

A persistent online Redis store ensures that OTP validations are shared across backend restarts (vital since Render's free tier cycles apps daily).

### Step-by-Step Configuration:
1. Sign up on **[Upstash](https://upstash.com/)** (highly recommended for serverless/free tiers).
2. Create a new serverless Redis database.
3. Copy the **Redis URL** (SSL/TLS enabled) from your console. It will start with `rediss://` (the double `s` is required for TLS connection).
   - Format: `rediss://default:<password>@<host>:<port>`
4. **Resiliency**: The app is designed to fall back to in-memory dictionaries if Redis goes offline, but online Redis is strongly recommended for production stability.

---

## 🚀 3. Backend Hosting (Render)

Render hosts your FastAPI server. We have generated a `requirements.txt` file in the `backend/` directory so Render can automatically identify and build the application dependencies.

### Step-by-Step Configuration:
1. Push all local changes to your GitHub repository (including the updated `config.py` and `requirements.txt`).
2. Log into **Render** and click **New > Web Service**.
3. Link your GitHub repository and select the repository.
4. Configure the Web Service settings:
   - **Name**: `community-backend` (or similar)
   - **Environment**: `Python`
   - **Root Directory**: `backend` (very important since the python files are in the `backend` folder)
   - **Build Command**: `pip install -r requirements.txt` (Render should auto-detect this, but you can explicitly specify it)
   - **Start Command**: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
     *Note: Combining `alembic upgrade head && uvicorn ...` in the start command ensures that your database migrations run automatically on Neon every time you deploy or restart.*

5. Click **Advanced** to add the following **Environment Variables**:

| Variable Name | Value Description | Example / Note |
| :--- | :--- | :--- |
| `DATABASE_URL` | Neon Connection String | `postgresql://alex:password@ep-host.neon.tech/neondb?sslmode=require` |
| `REDIS_URL` | Cloud Redis URI | `rediss://default:password@my-redis.upstash.io:6379` |
| `SECRET_KEY` | Secure random string (min 32 chars) | *Must be set for production security* |
| `ENVIRONMENT` | `production` | *Disables mock OTPs and secures CORS settings* |
| `BACKEND_CORS_ORIGINS` | Comma-separated allowed domains | `https://your-frontend.onrender.com` (use only if hosting Flutter on Web) |

6. Click **Create Web Service**.

---

## 📱 4. Frontend Connection (Flutter)

1. Open your Flutter application in `frontend/`.
2. Locate your base API configuration (usually in a HTTP client service).
3. Update the base URL from `http://localhost:8000` to your Render Web Service URL (e.g. `https://community-backend.onrender.com`).
4. **CORS note**:
   - If running Flutter as a **mobile app (Android/iOS)**: Mobile apps bypass browser CORS, so `BACKEND_CORS_ORIGINS` is not strictly required.
   - If running Flutter as a **Web App**: You must include the domain where the Flutter Web app is hosted in the `BACKEND_CORS_ORIGINS` variable.

---

## 💡 Render Free Tier Limitations to Keep in Mind
- **Cold Starts**: Render spins down free web services after 15 minutes of inactivity. The first request after spin-down will trigger a spin-up cycle taking **50–70 seconds**.
- **Ephemeral Disk**: Render's free tier has an ephemeral disk. Files written locally will disappear when the service restarts. (This backend does not store local files, so it is safe).
