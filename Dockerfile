# syntax=docker/dockerfile:1
# Single image, two roles: the web app, and (optionally) the sandbox.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Toolchains for the languages the platform can execute.  Drop the ones you do
# not need to shrink the image; the matching Language rows can be disabled in
# the admin instead.
RUN apt-get update && apt-get install --no-install-recommends -y \
        build-essential \
        g++ \
        default-jdk-headless \
        nodejs \
        sqlite3 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Unprivileged runtime user: submitted code must never be able to write here.
RUN useradd --create-home --uid 10001 dsa \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R dsa:dsa /app
USER dsa

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health/').read()"

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && python manage.py runserver 0.0.0.0:8000"]
