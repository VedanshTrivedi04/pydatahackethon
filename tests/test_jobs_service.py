"""
Tests for JobService.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from engine.core.jobs.service import JobService
from engine.core.models.job import Job


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.mark.asyncio
async def test_submit_job(mock_session, mock_job_repo, mock_tenant_id):
    """Test that submitting a job correctly builds the Job object, persists it, and emits an event."""
    # Setup mock return value
    job_id = uuid.uuid4()
    mock_job_repo.create.return_value = Job(
        id=job_id,
        tenant_id=mock_tenant_id,
        module="test_module",
        status="queued"
    )

    # Patch celery_app.send_task to prevent actual broker calls
    with patch("engine.core.jobs.service.celery_app.send_task") as mock_send_task, \
         patch("engine.core.jobs.service.event_bus.emit") as mock_event_emit:
        
        service = JobService(session=mock_session, repository=mock_job_repo)
        
        result_job = await service.submit_job(
            tenant_id=mock_tenant_id,
            module="test_module",
            trigger="api",
            payload={"key": "value"}
        )
        
        # Verify repo.create was called
        mock_job_repo.create.assert_called_once()
        created_job = mock_job_repo.create.call_args[0][0]
        assert created_job.tenant_id == mock_tenant_id
        assert created_job.module == "test_module"
        assert created_job.status == "queued"
        
        # Verify event was emitted
        mock_event_emit.assert_called_once()
        event_arg = mock_event_emit.call_args[0][0]
        assert event_arg.type == "job.created"
        
        # Verify Celery task was dispatched
        mock_send_task.assert_called_once()
        assert mock_send_task.call_args[0][0] == "engine.workers.execute_module.execute_module_task"
        assert result_job.id == job_id


@pytest.mark.asyncio
async def test_process_approval_success(mock_session, mock_job_repo, mock_tenant_id, mock_job_id):
    """Test approving a job transitions it and triggers the dispatcher."""
    # Setup mock to simulate job existing and being approved
    mock_job_repo.process_approval.return_value = Job(
        id=mock_job_id,
        tenant_id=mock_tenant_id,
        module="test_module",
        status="approved"
    )

    with patch("engine.core.jobs.service.celery_app.send_task") as mock_send_task:
        service = JobService(session=mock_session, repository=mock_job_repo)
        
        result = await service.process_approval(
            job_id=mock_job_id,
            tenant_id=mock_tenant_id,
            approved=True,
            approved_by="admin@example.com"
        )
        
        assert result is True
        mock_job_repo.process_approval.assert_called_once_with(
            job_id=mock_job_id,
            tenant_id=mock_tenant_id,
            approved=True,
            approved_by="admin@example.com",
            note=None
        )
        
        # Verify dispatcher task is triggered for approved jobs
        mock_send_task.assert_called_once_with(
            "engine.workers.viasocket_dispatcher.dispatch_webhook",
            kwargs={
                "job_id": str(mock_job_id),
                "tenant_id": str(mock_tenant_id),
                "event_name": "job_approved",
                "module": "test_module",
                "data": {"approved_by": "admin@example.com", "note": None}
            },
            queue="shipfaster.low"
        )
