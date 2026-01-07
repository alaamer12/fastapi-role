"""
Users router demonstrating pure general RBAC with dynamic roles.
Shows resource-agnostic access control patterns.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from fastapi_role.rbac import require, Permission, Privilege

from ..database import get_db
from ..auth import get_current_user
from ..rbac_setup import get_rbac_service, Role
from ..models import User
from ..schemas import (
    UserResponse, UserCreate, UserUpdate, UserListResponse, 
    MessageResponse, ErrorResponse
)

router = APIRouter()


@router.get("/", response_model=UserListResponse)
@require(Permission("user", "read"))
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    List all users - requires 'user:read' permission.
    Demonstrates basic permission-based access control.
    """
    users = db.query(User).offset(skip).limit(limit).all()
    total = db.query(User).count()
    
    return UserListResponse(
        users=[UserResponse.from_orm(user) for user in users],
        total=total
    )


@router.get("/{user_id}", response_model=UserResponse)
@require(Permission("user", "read"))
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Get specific user by ID - requires 'user:read' permission.
    Shows resource-specific access with generic permission model.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    return UserResponse.from_orm(user)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@require(Permission("user", "create"))
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Create new user - requires 'user:create' permission.
    Demonstrates creation permissions with role validation.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Validate role exists in our dynamic role system
    if user_data.role not in [role.value for role in Role]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {user_data.role}. Valid roles: {[role.value for role in Role]}"
        )
    
    # Create user
    new_user = User(
        email=user_data.email,
        name=user_data.name,
        role=user_data.role,
        is_active=user_data.is_active
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return UserResponse.from_orm(new_user)


@router.put("/{user_id}", response_model=UserResponse)
@require(Permission("user", "update"))
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Update user - requires 'user:update' permission.
    Shows update permissions with data validation.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    # Update fields if provided
    update_data = user_data.dict(exclude_unset=True)
    
    # Validate role if being updated
    if "role" in update_data:
        if update_data["role"] not in [role.value for role in Role]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {update_data['role']}. Valid roles: {[role.value for role in Role]}"
            )
    
    # Check email uniqueness if being updated
    if "email" in update_data and update_data["email"] != user.email:
        existing_user = db.query(User).filter(User.email == update_data["email"]).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
    
    # Apply updates
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return UserResponse.from_orm(user)


@router.delete("/{user_id}", response_model=MessageResponse)
@require(Permission("user", "delete"))
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Delete user - requires 'user:delete' permission.
    Demonstrates deletion permissions with safety checks.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    db.delete(user)
    db.commit()
    
    return MessageResponse(message=f"User {user.email} deleted successfully")


@router.get("/me/profile", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's profile - no additional permissions required.
    Shows that authentication alone can be sufficient for some endpoints.
    """
    return UserResponse.from_orm(current_user)


@router.put("/me/profile", response_model=UserResponse)
async def update_my_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile - no additional permissions required.
    Users can always update their own basic profile information.
    """
    # Only allow updating certain fields for self-service
    allowed_fields = {"name", "email"}
    update_data = {k: v for k, v in user_data.dict(exclude_unset=True).items() 
                   if k in allowed_fields}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields provided for update"
        )
    
    # Check email uniqueness if being updated
    if "email" in update_data and update_data["email"] != current_user.email:
        existing_user = db.query(User).filter(User.email == update_data["email"]).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
    
    # Apply updates
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return UserResponse.from_orm(current_user)