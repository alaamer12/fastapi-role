"""
Tasks router demonstrating nested resource RBAC patterns.
Shows complex authorization with multiple resource relationships.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from fastapi_role.rbac import require
from fastapi_role.core.resource import Permission, Privilege, ResourceOwnership

from ..database import get_db
from ..auth import get_current_user
from ..rbac_setup import get_rbac_service, Role
from ..models import User, Task, Project
from ..schemas import (
    TaskResponse, TaskCreate, TaskUpdate, TaskListResponse,
    MessageResponse
)

router = APIRouter()


@router.get("/", response_model=TaskListResponse)
@require(Permission("task", "read"))
async def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[str] = Query(None),
    priority_filter: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    List tasks with complex filtering.
    Demonstrates multi-criteria filtering with RBAC.
    """
    query = db.query(Task)
    
    # Apply filters
    if status_filter:
        query = query.filter(Task.status == status_filter)
    
    if priority_filter:
        query = query.filter(Task.priority == priority_filter)
    
    if project_id:
        query = query.filter(Task.project_id == project_id)
    
    # Apply visibility rules based on user role
    if current_user.role not in ["admin", "manager"]:
        # Regular users can only see their own tasks or tasks in public projects
        query = query.join(Project, Task.project_id == Project.id, isouter=True).filter(
            (Task.assignee_id == current_user.id) |  # Own tasks
            (Project.is_public == True) |  # Tasks in public projects
            (Task.project_id == None)  # Personal tasks (no project)
        )
    
    tasks = query.offset(skip).limit(limit).all()
    total = query.count()
    
    return TaskListResponse(
        tasks=[TaskResponse.from_orm(task) for task in tasks],
        total=total
    )


@router.get("/{task_id}", response_model=TaskResponse)
@require(Permission("task", "read"))
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Get specific task with nested authorization checks.
    Shows hierarchical resource access control.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )
    
    # Check access permissions
    can_access = False
    
    # Admin and manager can access all tasks
    if current_user.role in ["admin", "manager"]:
        can_access = True
    # Task assignee can access their tasks
    elif task.assignee_id == current_user.id:
        can_access = True
    # If task belongs to a project, check project access
    elif task.project_id:
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if project and (project.is_public or project.owner_id == current_user.id):
            can_access = True
    
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: insufficient privileges for this task"
        )
    
    return TaskResponse.from_orm(task)


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
@require(Permission("task", "create"))
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Create new task with project validation.
    Shows creation with nested resource validation.
    """
    # Validate project access if project_id is provided
    if task_data.project_id:
        project = db.query(Project).filter(Project.id == task_data.project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with id {task_data.project_id} not found"
            )
        
        # Check if user can create tasks in this project
        can_create_in_project = (
            project.owner_id == current_user.id or
            current_user.role in ["admin", "manager"]
        )
        
        if not can_create_in_project:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: cannot create tasks in this project"
            )
    
    # Set assignee - use provided assignee_id or default to current user
    assignee_id = task_data.assignee_id or current_user.id
    
    # Validate assignee exists
    assignee = db.query(User).filter(User.id == assignee_id).first()
    if not assignee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {assignee_id} not found"
        )
    
    new_task = Task(
        title=task_data.title,
        description=task_data.description,
        assignee_id=assignee_id,
        project_id=task_data.project_id,
        status=task_data.status,
        priority=task_data.priority
    )
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    return TaskResponse.from_orm(new_task)


@router.put("/{task_id}", response_model=TaskResponse)
@require(
    # Task assignee can update OR user with task update permission
    ResourceOwnership("task", lambda kwargs: kwargs.get("task_id")),
    Permission("task", "update")
)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Update task - requires assignee ownership OR update permission.
    Shows ownership-based authorization for nested resources.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )
    
    # Update fields if provided
    update_data = task_data.dict(exclude_unset=True)
    
    # Validate project change if provided
    if "project_id" in update_data and update_data["project_id"] != task.project_id:
        if update_data["project_id"]:
            project = db.query(Project).filter(Project.id == update_data["project_id"]).first()
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Project with id {update_data['project_id']} not found"
                )
            
            # Check if user can move task to this project
            can_move_to_project = (
                project.owner_id == current_user.id or
                current_user.role in ["admin", "manager"]
            )
            
            if not can_move_to_project:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: cannot move task to this project"
                )
    
    # Validate assignee change if provided
    if "assignee_id" in update_data and update_data["assignee_id"] != task.assignee_id:
        assignee = db.query(User).filter(User.id == update_data["assignee_id"]).first()
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {update_data['assignee_id']} not found"
            )
    
    # Apply updates
    for field, value in update_data.items():
        setattr(task, field, value)
    
    db.commit()
    db.refresh(task)
    
    return TaskResponse.from_orm(task)


@router.delete("/{task_id}", response_model=MessageResponse)
@require(
    ResourceOwnership("task", lambda kwargs: kwargs.get("task_id")),
    Permission("task", "delete")
)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Delete task - requires assignee ownership OR delete permission.
    Shows deletion authorization for nested resources.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )
    
    db.delete(task)
    db.commit()
    
    return MessageResponse(message=f"Task '{task.title}' deleted successfully")


@router.get("/my/tasks", response_model=TaskListResponse)
async def get_my_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[str] = Query(None),
    priority_filter: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's assigned tasks - no additional permissions needed.
    Users can always access their own assigned tasks.
    """
    query = db.query(Task).filter(Task.assignee_id == current_user.id)
    
    if status_filter:
        query = query.filter(Task.status == status_filter)
    
    if priority_filter:
        query = query.filter(Task.priority == priority_filter)
    
    tasks = query.offset(skip).limit(limit).all()
    total = query.count()
    
    return TaskListResponse(
        tasks=[TaskResponse.from_orm(task) for task in tasks],
        total=total
    )


@router.post("/{task_id}/complete", response_model=TaskResponse)
@require(ResourceOwnership("task", lambda kwargs: kwargs.get("task_id")))
async def complete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Mark task as complete - requires assignee ownership.
    Shows status change with ownership validation.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )
    
    if task.status == "done":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task is already completed"
        )
    
    task.status = "done"
    db.commit()
    db.refresh(task)
    
    return TaskResponse.from_orm(task)


@router.post("/{task_id}/start", response_model=TaskResponse)
@require(ResourceOwnership("task", lambda kwargs: kwargs.get("task_id")))
async def start_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Start working on task - requires assignee ownership.
    Shows status change with ownership validation.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found"
        )
    
    if task.status == "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task is already in progress"
        )
    
    task.status = "in_progress"
    db.commit()
    db.refresh(task)
    
    return TaskResponse.from_orm(task)