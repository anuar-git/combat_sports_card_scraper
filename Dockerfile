FROM python:3.12-slim

WORKDIR /app

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY monitoring/ ./monitoring/

EXPOSE 8000

CMD uvicorn monitoring.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
