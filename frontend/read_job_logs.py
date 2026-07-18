import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"), override=True)

from engine.config.database import AsyncSessionLocal
from engine.core.jobs.repository import JobRepository
import uuid

async def main():
    job_id = uuid.UUID('eea8ec2b-acb2-42b5-95ce-63c5bfa8ba99')
    tenant_id = uuid.UUID('d3c89532-fa95-4e6b-a5d1-cbdb6628039e')
    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        job = await repo.get_by_id(job_id, tenant_id)
        if not job:
            print("Job not found!")
            return
        print(f"Job Status: {job.status}")
        print(f"Error: {job.error}")
        print("\n--- Logs ---")
        logs = await repo.get_logs(job_id, tenant_id)
        for log in logs:
            print(f"[{log.level}] {log.event}: {log.message}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
