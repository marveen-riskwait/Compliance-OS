# Single-app deploy: build the React front, then serve it + the API from one
# Python process on one origin (so the httpOnly auth cookies just work — no CORS).

# --- Stage 1: build the front into dist/ ---
FROM node:20-slim AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# --- Stage 2: Python runtime that serves the API + the built dist/ ---
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    FLASK_APP=src/app.py
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pipenv
COPY Pipfile Pipfile.lock ./
RUN pipenv install --deploy --system

COPY src/ ./src/
COPY migrations/ ./migrations/
COPY --from=frontend /app/dist ./dist
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

EXPOSE 8080
CMD ["./docker-entrypoint.sh"]
