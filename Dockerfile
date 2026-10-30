FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements/project.lock requirements/project.lock
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements/project.lock \
    && useradd --create-home --uid 10001 app

COPY alembic.ini ./
COPY migrations migrations
COPY config config
COPY src src
COPY data/staging/pilot_accounts.csv data/staging/pilot_accounts.csv

USER app
EXPOSE 8000
CMD ["uvicorn", "networking_intel.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--no-server-header"]
