import os
import sys

import psycopg2
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy


def main():
    database_url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT f.message, f.file
        FROM findings f
        JOIN pull_requests pr ON pr.id = f.pr_id
        ORDER BY f.created_at DESC
        LIMIT 50
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        print("No findings found, skipping evaluation.")
        sys.exit(0)

    data = {
        "question": [],
        "answer": [],
        "contexts": [],
    }

    for message, file in rows:
        data["question"].append("What issues exist in this code?")
        data["answer"].append(message or "")
        data["contexts"].append([file or ""])

    dataset = Dataset.from_dict(data)
    results = evaluate(dataset, metrics=[faithfulness, answer_relevancy])

    print("Evaluation results:")
    print(results)

    scores = results.to_pandas()
    faithfulness_score = scores["faithfulness"].mean() if "faithfulness" in scores.columns else 1.0
    print(f"Mean faithfulness: {faithfulness_score:.4f}")

    if faithfulness_score < 0.7:
        print(f"Faithfulness score {faithfulness_score:.4f} is below threshold 0.7")
        sys.exit(1)


if __name__ == "__main__":
    main()
