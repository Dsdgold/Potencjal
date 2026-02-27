FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY packages/ /app/packages/
COPY apps/api/ /app/apps/api/
COPY apps/worker/ /app/apps/worker/

ENV PYTHONPATH=/app/apps/worker:/app/apps/api:/app
