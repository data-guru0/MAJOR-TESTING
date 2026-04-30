FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir ragas langchain-openai psycopg2-binary datasets
COPY scripts/evaluate.py .
CMD ["python", "evaluate.py"]
