FROM python:3.11-slim
WORKDIR /app
COPY services/webhook/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/webhook/ .
COPY db/ /db/
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
