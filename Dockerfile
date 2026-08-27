# ==============================================================================
# STAGE 1: Builder (Compile-time environment)
# ==============================================================================
# We use a build-stage image to install compilation tools and compile wheels.
# This keeps the final runner image extremely slim and free from security risks
# associated with build tools (gcc, make, etc.).
# ==============================================================================
FROM python:3.10-slim AS builder

# Prevent Python from writing .pyc files to disk and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install system dependencies required for compiling Python packages (e.g., PostgreSQL driver, cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and use a virtual environment to isolate dependencies cleanly
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip, setuptools, and wheel for building efficient wheels
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install dependencies from the requirements file
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Explicitly install Gunicorn (production WSGI server) in the virtual environment.
# This avoids editing the local requirements.txt, while ensuring a secure, production-grade web server is available.
RUN pip install --no-cache-dir gunicorn


# ==============================================================================
# STAGE 2: Runner (Production-hardened runtime environment)
# ==============================================================================
# The runner stage starts from a clean slim base and only copies the compiled
# virtual environment and source code. No build tools are present.
# ==============================================================================
FROM python:3.10-slim AS runner

# Optimize Python execution and configure runtime defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE="videostream.settings.prod" \
    PORT=8000

# Create a system-level non-root group and user for security isolation.
# We assign specific UIDs and GIDs (e.g., 10001) to run as an unprivileged user.
RUN groupadd -g 10001 django && \
    useradd -u 10001 -g django -m -s /bin/bash django

# Setup application working directory
WORKDIR /app

# Copy the pre-built virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Create directories for static and media assets.
# This ensures that even on read-only root filesystems, Django has write access
# to these specific folders under the non-privileged user account.
RUN mkdir -p /app/staticfiles /app/mediafiles && \
    chown -R django:django /app

# Copy application source code and entrypoint script
# (The .dockerignore file ensures only source code and entrypoint.sh are copied)
COPY --chown=django:django . .

# Ensure entrypoint is executable by the django user
RUN chmod +x /app/entrypoint.sh

# Switch runtime execution context to the non-root user
USER django

# Expose standard application port
EXPOSE 8000

# Set entrypoint to our robust database connection / environment verification script
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command starts the production WSGI server (Gunicorn).
# By default we configure Gunicorn to run with 4 worker processes and 2 threads per worker
# to optimize concurrent requests in production container environments.
# Note: In production, the command can be overridden to run Celery workers or beat schedulers.
CMD ["gunicorn", "videostream.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--timeout", "120"]
