from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import select, update

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from models import Settings, Finding, Pattern, LearnRequest

settings = Settings()
engine = create_async_engine(settings.database_url)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

app = FastAPI()
Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/learn")
async def learn(request: LearnRequest):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Finding)
            .where(
                Finding.pr_id == request.pr_id,
                Finding.severity.in_(["warning", "error"]),
            )
        )
        findings = result.scalars().all()

        for finding in findings:
            stmt = (
                insert(Pattern)
                .values(
                    repo_full_name=request.repo_full_name,
                    pattern_text=finding.message,
                    frequency=1,
                )
                .on_conflict_do_update(
                    index_elements=["repo_full_name", "pattern_text"],
                    set_={"frequency": Pattern.frequency + 1},
                )
            )
            await session.execute(stmt)

        await session.commit()

    return {"status": "ok"}
