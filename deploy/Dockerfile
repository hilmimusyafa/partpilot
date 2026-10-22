FROM python:3.12-slim
WORKDIR /app
COPY deploy/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend /app/backend
COPY scripts /app/scripts
COPY frontend-web/out /app/frontend-web/out
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 1000:1000
CMD ["python", "scripts/demo_runtime.py", "api"]
