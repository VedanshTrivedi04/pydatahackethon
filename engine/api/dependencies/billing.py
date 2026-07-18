"""
Billing & Subscription Dependencies (Mock Demo Implementation).

Enforces tier limits (free, pro, enterprise) on specific routes.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status


def require_tier(allowed_tiers: list[str]):
    """
    FastAPI Dependency to block routes based on the tenant's subscription plan.
    
    Usage:
        @router.post("/heavy-job", dependencies=[Depends(require_tier(["pro", "enterprise"]))])
    """
    async def _dependency(request: Request):
        tenant = getattr(request.state, "tenant", None)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to verify subscription tier."
            )
            
        current_tier = getattr(tenant, "plan", "free").lower()
        
        if current_tier not in allowed_tiers:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"This feature requires one of the following plans: {', '.join(allowed_tiers)}. You are currently on the '{current_tier}' plan."
            )
            
    return _dependency
