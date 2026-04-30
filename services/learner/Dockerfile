FROM python:3.11-slim
WORKDIR /app
COPY services/learner/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/learner/ .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
