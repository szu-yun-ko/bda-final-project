# Stage 1: build React frontend (Mapbox token baked in at build time)
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_MAPBOX_TOKEN
ENV VITE_MAPBOX_TOKEN=$VITE_MAPBOX_TOKEN
RUN npm run build

# Stage 2: Python API + static files
FROM python:3.11-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=8080

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY src/ ./src/
COPY data/sample/ ./data/sample/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

RUN mkdir -p data/cache outputs

EXPOSE 8080

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 4 --timeout 180 src.web_app:app"]
