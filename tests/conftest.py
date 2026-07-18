"""
Pytest configuration and fixtures.
"""

import uuid
from unittest.mock import AsyncMock

import pytest
from engine.core.models.tenant import Tenant
from engine.core.models.job import Job

@pytest.fixture
def mock_tenant_id() -> uuid.UUID:
    return uuid.uuid4()

@pytest.fixture
def mock_job_id() -> uuid.UUID:
    return uuid.uuid4()

@pytest.fixture
def mock_job_repo():
    """Returns a mocked JobRepository."""
    from engine.core.jobs.repository import JobRepository
    repo = AsyncMock(spec=JobRepository)
    return repo
