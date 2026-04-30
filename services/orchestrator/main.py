import time

import httpx
import jwt
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from models import Settings, Finding, Pattern, AnalyzeRequest
from graph import build_graph

settings = Settings()
engine = create_async_engine(settings.database_url)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

app = FastAPI()
Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze", status_code=202)
async def analyze(request: AnalyzeRequest):
    token = await get_installation_token(request.installation_id)
    diff = await fetch_diff(request.repo_full_name, request.pr_number, token)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Pattern)
            .where(Pattern.repo_full_name == request.repo_full_name)
            .order_by(Pattern.frequency.desc())
            .limit(10)
        )
        patterns = [row.pattern_text for row in result.scalars().all()]

    state = build_graph().invoke({"diff": diff, "patterns": patterns, "findings": []})
    findings_data = state.get("findings", [])

    async with AsyncSessionLocal() as session:
        for f in findings_data:
            session.add(Finding(
                pr_id=request.pr_id,
                file=f.get("file"),
                line=f.get("line"),
                severity=f.get("severity"),
                message=f.get("message"),
                agent=f.get("agent"),
            ))
        await session.commit()

    async with httpx.AsyncClient() as client:
        await client.post(
            "http://reviewer:8003/post-review",
            json={
                "pr_id": str(request.pr_id),
                "repo_full_name": request.repo_full_name,
                "pr_number": request.pr_number,
                "installation_id": request.installation_id,
                "findings": findings_data,
            },
            timeout=60,
        )

    return {"status": "accepted"}


async def get_installation_token(installation_id: int) -> str:
    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 600, "iss": settings.github_app_id}
    private_key = settings.github_app_private_key.replace("\\n", "\n")
    encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {encoded_jwt}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        response.raise_for_status()
        return response.json()["token"]


async def fetch_diff(repo_full_name: str, pr_number: int, token: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3.diff",
            },
        )
        response.raise_for_status()
        return response.text
