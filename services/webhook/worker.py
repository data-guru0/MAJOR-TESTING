import httpx
from celery import Celery
import os

redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
app = Celery("webhook", broker=redis_url, backend=redis_url)
app.conf.task_routes = {
    "analyze_pr": {"queue": "webhook"},
    "trigger_learning": {"queue": "learning"},
}


@app.task(name="analyze_pr")
def analyze_pr(pr_id: str, pr_number: int, repo_full_name: str, head_sha: str, installation_id: int):
    with httpx.Client() as client:
        client.post(
            "http://orchestrator:8002/analyze",
            json={
                "pr_id": pr_id,
                "pr_number": pr_number,
                "repo_full_name": repo_full_name,
                "head_sha": head_sha,
                "installation_id": installation_id,
            },
            timeout=120,
        )


@app.task(name="trigger_learning")
def trigger_learning(repo_full_name: str, pr_id: str):
    with httpx.Client() as client:
        client.post(
            "http://learner:8004/learn",
            json={"repo_full_name": repo_full_name, "pr_id": pr_id},
            timeout=60,
        )
