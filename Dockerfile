# ──────────────────────────────────────────────────────────
# Stage 1: builder
# Installs all Python dependencies into a dedicated prefix
# so the runtime image stays lean and has no build tools.
# ──────────────────────────────────────────────────────────
FROM python:3.14-slim-bookworm AS builder

# Prevents Python from writing .pyc files and enables unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies (needed for some C-extension wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching —
# if requirements.txt hasn't changed, this layer is reused.
COPY requirements.txt .

# Install into an isolated prefix (not system Python)
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt


# ──────────────────────────────────────────────────────────
# Stage 2: runtime
# Lean production image — no compiler, no build artifacts.
# ──────────────────────────────────────────────────────────
FROM python:3.14-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/install/bin:$PATH"

WORKDIR /app

# Install only the runtime C libraries (no compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Create a non-root user for security
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# Copy application source
COPY --chown=appuser:appgroup . .

# Copy and set executable permissions on entrypoint
COPY --chown=appuser:appgroup entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to non-root user
USER appuser

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
