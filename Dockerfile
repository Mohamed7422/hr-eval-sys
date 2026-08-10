# ── Stage 1: build dependencies ──────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --prefix=/install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py collectstatic --noinput && python manage.py migrate && gunicorn hr_evaluation.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 60 --access-logfile -"]