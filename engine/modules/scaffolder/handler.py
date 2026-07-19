import io
import zipfile
import logging
from typing import Dict, Any
from engine.core.models import ModuleResult
from engine.core import storage
from engine.core import llm_client
from engine.prompts.scaffolder import README_CUSTOMIZATION_PROMPT

logger = logging.getLogger("engine.modules.scaffolder")

# Comprehensive FastAPI Dockerized templates
FASTAPI_TEMPLATES = {
    "main.py": """from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from contextlib import asynccontextmanager

from database import engine, get_db, init_db
from models import User
from schemas import UserCreate, UserResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables on startup
    await init_db()
    yield

app = FastAPI(title="{project_name} API", lifespan=lifespan)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {{"message": "Welcome to {project_name}! Automated by ShipFaster."}}

@app.get("/health")
def health_check():
    return {{"status": "healthy"}}

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    stmt = select(User).where(User.email == user.email)
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    db_user = User(email=user.email, full_name=user.full_name)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@app.get("/users", response_model=list[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    stmt = select(User)
    result = await db.execute(stmt)
    return result.scalars().all()
""",
    "database.py": """import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/postgres")

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
""",
    "models.py": """from sqlalchemy import Column, Integer, String, Boolean
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
""",
    "schemas.py": """from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True
""",
    "Dockerfile": """FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    libpq-dev \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
    "docker-compose.yml": """version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/postgres
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
""",
    "requirements.txt": """fastapi>=0.100.0
uvicorn>=0.22.0
sqlalchemy>=2.0.0
asyncpg>=0.28.0
pydantic>=2.0.0
pytest>=7.0.0
httpx>=0.24.0
""",
    "tests/test_main.py": """import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_read_root():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert "Welcome" in response.json()["message"]

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {{"status": "healthy"}}
"""
}

async def run(job_id: str, tenant_id: str, payload: dict) -> ModuleResult:
    """
    Scaffolder module handler.
    Generates a project skeleton for the specified stack, packages it as a zip file,
    and saves it to storage.
    
    Payload shape:
    {
        "stack": str,         # e.g., "fastapi"
        "project_name": str,  # e.g., "my_api_project"
        "description": str    # optional description for README customization
    }
    """
    stack = payload.get("stack", "fastapi").lower()
    project_name = payload.get("project_name", "shipfaster_project")
    description = payload.get("description", "A fast API project generated by ShipFaster.")
    
    if stack != "fastapi":
        return ModuleResult(
            status="failed",
            output={},
            artifacts=[],
            error=f"Unsupported stack: '{stack}'. Only 'fastapi' is currently supported."
        )
        
    try:
        # 1. Custom README generation via LLM if a description is provided
        logger.info(f"Customizing README for project: {project_name}")
        system_instruction = README_CUSTOMIZATION_PROMPT.format(
            project_name=project_name,
            stack=stack,
            description=description
        )
        
        # We do a quick LLM call to get the customized README
        readme_content = await llm_client.complete(
            tenant_id=tenant_id,
            job_id=job_id,
            system=system_instruction,
            messages=[{"role": "user", "content": "Please generate the README.md"}]
        )
        
        # 2. Package files into a zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Write project template files
            for file_path, template_str in FASTAPI_TEMPLATES.items():
                content = template_str.format(project_name=project_name)
                zip_file.writestr(file_path, content)
                
            # Write custom README
            zip_file.writestr("README.md", readme_content)
            
        zip_bytes = zip_buffer.getvalue()
        
        # 3. Save zip archive to storage
        artifact_name = f"{project_name}.zip"
        s3_key = storage.save_artifact(
            job_id=job_id,
            tenant_id=tenant_id,
            file_name=artifact_name,
            file_content=zip_bytes,
            content_type="application/zip"
        )
        
        return ModuleResult(
            status="success",
            output={
                "artifact_key": s3_key,
                "project_name": project_name,
                "stack": stack,
                "readme_summary": readme_content[:200] + "..."
            },
            artifacts=[s3_key],
            error=None
        )
        
    except Exception as e:
        logger.error(f"Error in scaffolder module execution: {str(e)}")
        return ModuleResult(
            status="failed",
            output={},
            artifacts=[],
            error=str(e)
        )
