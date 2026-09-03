# =============================================================================
# Android Device Quality CI/CD Pipeline - Runtime Container
# =============================================================================
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root system user and group for security compliance
RUN groupadd --system --gid 10001 appgroup && \
    useradd --system --uid 10001 --gid appgroup --create-home --home-dir /home/appuser appuser

WORKDIR /app

# Copy dependency specifications and project packaging metadata
COPY pyproject.toml requirements.txt README.md ./

# Install application in editable/wheel form
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Change ownership of /app to appuser
RUN chown -R appuser:appgroup /app

# Switch to non-root execution context
USER appuser

# Healthcheck / validation entrypoint
ENTRYPOINT ["python", "-m", "device_quality.runner"]
CMD ["--sample"]
