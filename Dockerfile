# --- フロントエンドビルド ---
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- バックエンド ---
FROM python:3.12-slim AS backend
WORKDIR /app

# pypdfium2 / pillow の実行に必要な最小ライブラリ
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
# ビルド済みフロントエンドを配信ディレクトリへ
COPY --from=frontend /app/frontend/dist ./frontend_dist

ENV DATA_DIR=/data
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
