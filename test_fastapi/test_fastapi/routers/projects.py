"""
Projects router demonstrating complex RBAC patterns.
Shows hierarchical resources and advanced authorization patterns.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from fastapi_role.rbac import require, Permission, Privilege, ResourceOwnership

from ..database import get_db
from ..auth import get_current_user
from ..rbac_setup import get_rbac_service, Role
from ..models import User, Project, Task
from ..schemas import (
    ProjectResponse, ProjectCreate, ProjectUpdate, ProjectListResponse,
    TaskResponse, MessageResponse
)

router = APIRouter()


@router.get("/", response_model=ProjectListResponse)
@require(Permission("project", "read"))
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[str] = Query(None),
    include_private: bool = Query(False),
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    List projects with filtering and visibility controls.
    Demonstrates complex query filtering with RBAC.
    """
    query = db.query(Project)
    
    # Apply status filter if provided
    if status_filter:
        query = query.filter(Project.status == status_filter)
    
    # Apply visibility filter based on user role and request
    if not include_private or current_user.role not in ["admin", "manager"]:
        query = query.filter(
            (Project.is_public == True) | (Project.owner_id == current_user.id)
        )
    
    projects = query.offset(skip).limit(limit).all()
    total = query.count()
    
    return ProjectListResponse(
        projects=[ProjectResponse.from_orm(project) for project in projects],
        total=total
    )


@router.get("/{project_id}", response_model=ProjectResponse)
@require(Permission("project", "read"))
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Get specific project with access control.
    Shows resource-specific authorization.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    
    # Check access permissions
    can_access = (
        project.is_public or
        project.owner_id == current_user.id or
        current_user.role in ["admin", "manager"]
    )
    
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: insufficient privileges for this project"
        )
    
    return ProjectResponse.from_orm(project)


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
@require(Permission("project", "create"))
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Create new project - user becomes owner.
    Shows creation with ownership assignment.
    """
    new_project = Project(
        name=project_data.name,
        description=project_data.description,
        status=project_data.status,
        is_public=project_data.is_public,
        owner_id=current_user.id
    )
    
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    
    return ProjectResponse.from_orm(new_project)


@router.put("/{project_id}", response_model=ProjectResponse)
@require(
    # Project owner can update OR user with project update permission
    ResourceOwnership("project", lambda kwargs: kwargs.get("project_id")),
    Permission("project", "update")
)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Update project - requires ownership OR update permission.
    Demonstrates OR logic between authorization requirements.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    
    # Update fields if provided
    update_data = project_data.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(project, field, value)
    
    db.commit()
    db.refresh(project)
    
    return ProjectResponse.from_orm(project)


@router.delete("/{project_id}", response_model=MessageResponse)
@require(
    ResourceOwnership("project", lambda kwargs: kwargs.get("project_id")),
    Permission("project", "delete")
)
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Delete project - requires ownership OR delete permission.
    Shows cascading deletion with authorization.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    
    # Check if project has tasks
    task_count = db.query(Task).filter(Task.project_id == project_id).count()
    if task_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete project with {task_count} tasks. Delete tasks first."
        )
    
    db.delete(project)
    db.commit()
    
    return MessageResponse(message=f"Project '{project.name}' deleted successfully")


@router.get("/{project_id}/tasks", response_model=List[TaskResponse])
@require(Permission("project", "read"))
async def get_project_tasks(
    project_id: int,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Get all tasks for a project.
    Shows hierarchical resource access.
    """
    # First check if user can access the project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    
    # Check project access
    can_access = (
        project.is_public or
        project.owner_id == current_user.id or
        current_user.role in ["admin", "manager"]
    )
    
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: insufficient privileges for this project"
        )
    
    # Get tasks for the project
    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    
    return [TaskResponse.from_orm(task) for task in tasks]


@router.get("/my/projects", response_model=ProjectListResponse)
async def get_my_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's projects - no additional permissions needed.
    Users can always access their own resources.
    """
    query = db.query(Project).filter(Project.owner_id == current_user.id)
    
    if status_filter:
        query = query.filter(Project.status == status_filter)
    
    projects = query.offset(skip).limit(limit).all()
    total = query.count()
    
    return ProjectListResponse(
        projects=[ProjectResponse.from_orm(project) for project in projects],
        total=total
    )


@router.post("/{project_id}/archive", response_model=ProjectResponse)
@require(
    ResourceOwnership("project", lambda kwargs: kwargs.get("project_id")),
    Permission("project", "update")
)
async def archive_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Archive project - requires ownership OR update permission.
    Shows status change operations with authorization.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    
    if project.status == "archived":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project is already archived"
        )
    
    project.status = "archived"
    db.commit()
    db.refresh(project)
    
    return ProjectResponse.from_orm(project)


@router.post("/{project_id}/activate", response_model=ProjectResponse)
@require(
    ResourceOwnership("project", lambda kwargs: kwargs.get("project_id")),
    Permission("project", "update")
)
async def activate_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Activate project - requires ownership OR update permission.
    Shows status change operations with authorization.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id {project_id} not found"
        )
    
    project.status = "active"
    db.commit()
    db.refresh(project)
    
    return ProjectResponse.from_orm(project)