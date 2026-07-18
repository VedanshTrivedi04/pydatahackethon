"""
Tests for LLMUsageTracker.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from engine.core.llm.usage_tracker import LLMUsageTracker


@pytest.fixture
def mock_session():
    """Mock SQLAlchemy AsyncSession."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_get_today_cost(mock_session, mock_tenant_id):
    """Test that today's LLM cost is aggregated properly."""
    # Setup the mocked query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = 12.55
    mock_session.execute.return_value = mock_result

    tracker = LLMUsageTracker(session=mock_session)
    
    cost = await tracker.get_today_cost(tenant_id=mock_tenant_id)
    
    assert cost == 12.55
    mock_session.execute.assert_called_once()
    
    # Check that a SELECT statement was executed
    stmt_passed = mock_session.execute.call_args[0][0]
    assert "SELECT sum(llm_usage.cost_usd)" in str(stmt_passed)
