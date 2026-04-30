FROM python:3.11-slim
WORKDIR /app
COPY services/reviewer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/reviewer/ .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
