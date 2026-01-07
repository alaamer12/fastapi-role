"""
Main FastAPI application for testing pure general RBAC.
Demonstrates resource-agnostic access control with dynamic roles.
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from .database import create_tables, init_sample_data, get_db
from .config import settings
from .auth import get_current_user, authenticate_user, create_access_token
from .models import User
from .schemas import MessageResponse, UserResponse

# Import routers (will be created in next steps)
from .routers import auth, users, documents, projects, tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - setup and teardown"""
    # Startup
    create_tables()
    
    # Initialize sample data
    db = next(get_db())
    try:
        init_sample_data(db)
    finally:
        db.close()
    
    yield
    
    # Shutdown (if needed)
    pass


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Generic RBAC test application demonstrating pure general access control",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(projects.router, prefix="/projects", tags=["Projects"])
app.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])


@app.get("/", response_model=MessageResponse)
async def root():
    """Root endpoint"""
    return MessageResponse(message="Generic RBAC Test Application - Pure General Access Control")


@app.get("/health", response_model=MessageResponse)
async def health_check():
    """Health check endpoint"""
    return MessageResponse(message="Application is healthy")


@app.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse.from_orm(current_user)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "test_fastapi.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )