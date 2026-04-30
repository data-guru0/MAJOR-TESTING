FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir "ragas==0.1.21" "langchain-openai==0.1.25" psycopg2-binary datasets
COPY scripts/evaluate.py .
CMD ["python", "evaluate.py"]
