"""
Authentication Routes.

Endpoints for human user registration and JWT login.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.config.database import get_db_session
from engine.core.auth.jwt import create_access_token, get_password_hash, verify_password
from engine.core.models.tenant import Tenant
from engine.core.models.tenant_member import TenantMember
from engine.core.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    tenant_name: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str | None = None
    tenant_name: str | None = None


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: UserRegisterRequest,
    session: AsyncSession = Depends(get_db_session)
) -> Any:
    """
    Register a new user and create their default tenant workspace.
    """
    # Check if user exists
    stmt = select(User).where(User.email == request.email)
    result = await session.execute(stmt)
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
        
    # 1. Create User
    new_user = User(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        full_name=request.full_name
    )
    session.add(new_user)
    await session.flush()
    
    # 2. Create Tenant
    # Generate a slug based on tenant_name and user_id to ensure uniqueness
    slug = f"{request.tenant_name.lower().replace(' ', '-')}-{str(new_user.id)[:8]}"
    new_tenant = Tenant(
        name=request.tenant_name,
        slug=slug,
        email=request.email,
    )
    session.add(new_tenant)
    await session.flush()
    
    # 3. Create TenantMember (Owner role)
    member = TenantMember(
        user_id=new_user.id,
        tenant_id=new_tenant.id,
        role="owner"
    )
    session.add(member)
    await session.commit()
    
    # 4. Generate JWT Token
    token_data = {"sub": str(new_user.id)}
    access_token = create_access_token(data=token_data)
    
    return {
        "access_token": access_token,
        "tenant_id": str(new_tenant.id),
        "tenant_name": new_tenant.name,
    }


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: AsyncSession = Depends(get_db_session)
) -> Any:
    """
    OAuth2 compatible token login, getting an access token for future requests.
    """
    stmt = select(User).where(User.email == form_data.username)
    result = await session.execute(stmt)
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Fetch default tenant for this user
    stmt_member = select(TenantMember).where(TenantMember.user_id == user.id)
    res_member = await session.execute(stmt_member)
    member = res_member.scalars().first()
    
    tenant_id = None
    tenant_name = None
    if member:
        stmt_tenant = select(Tenant).where(Tenant.id == member.tenant_id)
        res_tenant = await session.execute(stmt_tenant)
        tenant = res_tenant.scalars().first()
        if tenant:
            tenant_id = str(tenant.id)
            tenant_name = tenant.name

    token_data = {"sub": str(user.id)}
    access_token = create_access_token(data=token_data)
    
    return {
        "access_token": access_token,
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
    }
