"""
Generic database models for testing pure general RBAC.
No business assumptions - uses generic resource types.
"""
from typing import Optional, Union
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """Generic User model implementing UserProtocol - no business assumptions"""
    __tablename__ = "users"
    
    id: int = Column(Integer, primary_key=True, index=True)
    email: str = Column(String(255), unique=True, index=True, nullable=False)
    role: str = Column(String(50), nullable=False)
    name: str = Column(String(255), nullable=False)
    is_active: bool = Column(Boolean, default=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    
    # Relationships to generic resources
    documents = relationship("Document", back_populates="owner")
    projects = relationship("Project", back_populates="owner")
    tasks = relationship("Task", back_populates="assignee")
    
    def has_role(self, role_name: str) -> bool:
        """Check if user has this specific role"""
        return self.role == role_name
    
    def __str__(self) -> str:
        return f"User(id={self.id}, email={self.email}, role={self.role})"


class Document(Base):
    """Generic Document resource for testing ownership patterns"""
    __tablename__ = "documents"
    
    id: int = Column(Integer, primary_key=True, index=True)
    title: str = Column(String(255), nullable=False)
    content: str = Column(Text, nullable=True)
    owner_id: int = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_public: bool = Column(Boolean, default=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="documents")
    
    def __str__(self) -> str:
        return f"Document(id={self.id}, title={self.title}, owner_id={self.owner_id})"


class Project(Base):
    """Generic Project resource for testing complex ownership patterns"""
    __tablename__ = "projects"
    
    id: int = Column(Integer, primary_key=True, index=True)
    name: str = Column(String(255), nullable=False)
    description: str = Column(Text, nullable=True)
    owner_id: int = Column(Integer, ForeignKey("users.id"), nullable=False)
    status: str = Column(String(50), default="active")  # active, completed, archived
    is_public: bool = Column(Boolean, default=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project")
    
    def __str__(self) -> str:
        return f"Project(id={self.id}, name={self.name}, owner_id={self.owner_id})"


class Task(Base):
    """Generic Task resource for testing nested ownership patterns"""
    __tablename__ = "tasks"
    
    id: int = Column(Integer, primary_key=True, index=True)
    title: str = Column(String(255), nullable=False)
    description: str = Column(Text, nullable=True)
    assignee_id: int = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id: int = Column(Integer, ForeignKey("projects.id"), nullable=True)
    status: str = Column(String(50), default="todo")  # todo, in_progress, done
    priority: str = Column(String(20), default="medium")  # low, medium, high
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    assignee = relationship("User", back_populates="tasks")
    project = relationship("Project", back_populates="tasks")
    
    def __str__(self) -> str:
        return f"Task(id={self.id}, title={self.title}, assignee_id={self.assignee_id})"