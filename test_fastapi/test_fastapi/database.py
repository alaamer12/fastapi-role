"""
Database setup for the generic test application.
Uses SQLite for simplicity - no business assumptions.
"""
import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base, User, Document, Project, Task

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test_app.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_sample_data(db: Session):
    """Initialize sample data for testing - generic roles and resources"""
    
    # Check if data already exists
    if db.query(User).first():
        return
    
    # Create sample users with generic roles
    users = [
        User(
            email="admin@example.com",
            name="System Administrator",
            role="admin",
            is_active=True
        ),
        User(
            email="manager@example.com", 
            name="Project Manager",
            role="manager",
            is_active=True
        ),
        User(
            email="user1@example.com",
            name="Regular User One",
            role="user",
            is_active=True
        ),
        User(
            email="user2@example.com",
            name="Regular User Two", 
            role="user",
            is_active=True
        ),
        User(
            email="viewer@example.com",
            name="Read Only Viewer",
            role="viewer",
            is_active=True
        )
    ]
    
    for user in users:
        db.add(user)
    db.commit()
    
    # Refresh to get IDs
    for user in users:
        db.refresh(user)
    
    # Create sample documents
    documents = [
        Document(
            title="Public Documentation",
            content="This is a public document accessible to all users.",
            owner_id=users[0].id,  # admin
            is_public=True
        ),
        Document(
            title="Manager's Private Notes",
            content="Private notes for project management.",
            owner_id=users[1].id,  # manager
            is_public=False
        ),
        Document(
            title="User Guide Draft",
            content="Draft of the user guide document.",
            owner_id=users[2].id,  # user1
            is_public=False
        )
    ]
    
    for doc in documents:
        db.add(doc)
    db.commit()
    
    # Create sample projects
    projects = [
        Project(
            name="Website Redesign",
            description="Complete redesign of the company website",
            owner_id=users[1].id,  # manager
            status="active",
            is_public=False
        ),
        Project(
            name="API Documentation",
            description="Create comprehensive API documentation",
            owner_id=users[2].id,  # user1
            status="active", 
            is_public=True
        ),
        Project(
            name="Security Audit",
            description="Comprehensive security audit of all systems",
            owner_id=users[0].id,  # admin
            status="active",
            is_public=False
        )
    ]
    
    for project in projects:
        db.add(project)
    db.commit()
    
    # Refresh to get IDs
    for project in projects:
        db.refresh(project)
    
    # Create sample tasks
    tasks = [
        Task(
            title="Design Homepage Mockup",
            description="Create initial mockup for the new homepage design",
            assignee_id=users[2].id,  # user1
            project_id=projects[0].id,  # Website Redesign
            status="in_progress",
            priority="high"
        ),
        Task(
            title="Write API Endpoints Documentation",
            description="Document all REST API endpoints with examples",
            assignee_id=users[3].id,  # user2
            project_id=projects[1].id,  # API Documentation
            status="todo",
            priority="medium"
        ),
        Task(
            title="Review Security Policies",
            description="Review and update all security policies",
            assignee_id=users[0].id,  # admin
            project_id=projects[2].id,  # Security Audit
            status="todo",
            priority="high"
        ),
        Task(
            title="Personal Task - Learn FastAPI",
            description="Study FastAPI documentation and best practices",
            assignee_id=users[3].id,  # user2
            project_id=None,  # No project - personal task
            status="in_progress",
            priority="low"
        )
    ]
    
    for task in tasks:
        db.add(task)
    db.commit()
    
    print("Sample data initialized successfully!")


def reset_database():
    """Reset the database - useful for testing"""
    Base.metadata.drop_all(bind=engine)
    create_tables()