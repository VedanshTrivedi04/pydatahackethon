"""
Feature Flags System (Mock Demo Implementation).

Allows enabling/disabling features globally or per-tenant.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

# Hardcoded feature flags for demo purposes
_GLOBAL_FLAGS = {
    "notebook_agent": True,
    "slack_integration": False, # Disabled globally
    "beta_dashboard": True,
}

def is_feature_enabled(feature_name: str, tenant_id: str | None = None) -> bool:
    """
    Check if a feature is enabled. 
    In a real system, this would query the database or LaunchDarkly.
    """
    return _GLOBAL_FLAGS.get(feature_name, False)

def require_feature(feature_name: str):
    """
    FastAPI Dependency to block routes if a feature is disabled.
    
    Usage:
        @router.post("/run", dependencies=[Depends(require_feature("notebook_agent"))])
    """
    async def _dependency(request: Request):
        tenant = getattr(request.state, "tenant", None)
        tenant_id = str(tenant.id) if tenant else None
        
        if not is_feature_enabled(feature_name, tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature_name}' is not enabled for your account."
            )
            
    return _dependency
