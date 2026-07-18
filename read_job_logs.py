import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)

from engine.config.database import AsyncSessionLocal, engine
from engine.core.jobs.repository import JobRepository
from sqlalchemy import select
from engine.core.models.artifact import Artifact
import uuid

async def main():
    job_id = uuid.UUID('866632ac-7468-4000-9d9c-73caf011fad7')
    tenant_id = uuid.UUID('d3c89532-fa95-4e6b-a5d1-cbdb6628039e')
    try:
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            job = await repo.get_by_id(job_id, tenant_id)
            if not job:
                print("Job not found!")
                return
            print(f"Job Status: {job.status}")
            print(f"Result (jsonb): {job.result}")
            print(f"Error: {job.error}")
            
            print("\n--- DB Artifacts ---")
            stmt = select(Artifact).where(Artifact.job_id == job_id)
            res = await session.execute(stmt)
            arts = res.scalars().all()
            for art in arts:
                print(f"- Artifact: {art.file_name} (S3 Key: {art.s3_key})")
    except Exception as e:
        print("Error during execution:", e)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
