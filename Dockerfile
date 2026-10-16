
FROM node:22.15.0-alpine AS frontend
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build
FROM python:3.12.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY migrations/ migrations/
COPY alembic.ini .
COPY --from=frontend /ui/dist frontend/dist
USER 65534:65534
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8017"]
