"""
Demo Tenant Seed Script.

Creates a demo tenant and prints their API key for local testing.

Usage:
    python scripts/seed_demo_tenant.py

This should be run AFTER:
    1. docker-compose up -d
    2. cp infra/.env.example .env  (and fill in values)
    3. alembic upgrade head
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"), override=True)

from engine.config.database import AsyncSessionLocal
from engine.core.tenants.repository import TenantRepository
from engine.core.tenants.service import TenantService


async def seed_demo_tenant() -> None:
    """Create a demo tenant for local testing."""
    async with AsyncSessionLocal() as session:
        repo = TenantRepository(session)
        service = TenantService(session=session, repository=repo)

        # Check if demo tenant already exists
        existing = await repo.get_by_slug("demo-corp")
        if existing:
            print(f"[SEED] Demo tenant already exists: {existing.id}")
            print("[SEED] To create a fresh key, use POST /api/v1/tenants/{id}/keys")
            return

        # Create demo tenant
        tenant, raw_key = await service.create_tenant(
            name="Demo Corporation",
            slug="demo-corp",
            email="demo@shipfaster.dev",
            plan="enterprise",
            initial_key_name="Local Dev Key",
        )
        await session.commit()

    print()
    print("=" * 60)
    print("  ShipFaster Demo Tenant Created!")
    print("=" * 60)
    print(f"  Tenant ID:  {tenant.id}")
    print(f"  Name:       {tenant.name}")
    print(f"  Slug:       {tenant.slug}")
    print(f"  Plan:       {tenant.plan}")
    print()
    print("  API KEY (shown once — save this!):")
    print(f"  {raw_key}")
    print()
    print("  Test with:")
    print(f'  curl http://localhost:8000/api/v1/tenants/{tenant.id} \\')
    print(f'    -H "Authorization: Bearer {raw_key}"')
    print("=" * 60)
    print()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_demo_tenant())
