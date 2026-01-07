"""
Documents router demonstrating ownership-based RBAC patterns.
Shows resource-agnostic access control with ownership validation.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from fastapi_role.rbac import require, Permission, Privilege, ResourceOwnership

from ..database import get_db
from ..auth import get_current_user
from ..rbac_setup import get_rbac_service, Role
from ..models import User, Document
from ..schemas import (
    DocumentResponse, DocumentCreate, DocumentUpdate, DocumentListResponse,
    MessageResponse
)

router = APIRouter()


@router.get("/", response_model=DocumentListResponse)
@require(Permission("document", "read"))
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_private: bool = Query(False),
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    List documents with visibility filtering.
    Shows how to combine permissions with business logic.
    """
    query = db.query(Document)
    
    # Filter based on user role and include_private flag
    if not include_private or current_user.role not in ["admin", "manager"]:
        # Non-privileged users or when not requesting private docs
        query = query.filter(
            (Document.is_public == True) | (Document.owner_id == current_user.id)
        )
    
    documents = query.offset(skip).limit(limit).all()
    total = query.count()
    
    return DocumentListResponse(
        documents=[DocumentResponse.from_orm(doc) for doc in documents],
        total=total
    )


@router.get("/{document_id}", response_model=DocumentResponse)
@require(Permission("document", "read"))
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Get specific document with ownership/visibility checks.
    Demonstrates resource-specific access control.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {document_id} not found"
        )
    
    # Check if user can access this document
    can_access = (
        document.is_public or  # Public documents
        document.owner_id == current_user.id or  # Owner access
        current_user.role in ["admin", "manager"]  # Privileged roles
    )
    
    if not can_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: insufficient privileges for this document"
        )
    
    return DocumentResponse.from_orm(document)


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
@require(Permission("document", "create"))
async def create_document(
    document_data: DocumentCreate,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Create new document - user becomes owner.
    Shows creation with automatic ownership assignment.
    """
    new_document = Document(
        title=document_data.title,
        content=document_data.content,
        is_public=document_data.is_public,
        owner_id=current_user.id
    )
    
    db.add(new_document)
    db.commit()
    db.refresh(new_document)
    
    return DocumentResponse.from_orm(new_document)


@router.put("/{document_id}", response_model=DocumentResponse)
@require(
    # Multiple authorization patterns - OR logic between decorators
    ResourceOwnership("document", lambda kwargs: kwargs.get("document_id")),
    Permission("document", "update")  # Admin/manager can update any document
)
async def update_document(
    document_id: int,
    document_data: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Update document - requires ownership OR update permission.
    Demonstrates multiple authorization patterns with OR logic.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {document_id} not found"
        )
    
    # Update fields if provided
    update_data = document_data.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(document, field, value)
    
    db.commit()
    db.refresh(document)
    
    return DocumentResponse.from_orm(document)


@router.delete("/{document_id}", response_model=MessageResponse)
@require(
    # Owner can delete their documents OR admin/manager can delete any
    ResourceOwnership("document", lambda kwargs: kwargs.get("document_id")),
    Permission("document", "delete")
)
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Delete document - requires ownership OR delete permission.
    Shows deletion with ownership validation.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {document_id} not found"
        )
    
    db.delete(document)
    db.commit()
    
    return MessageResponse(message=f"Document '{document.title}' deleted successfully")


@router.get("/my/documents", response_model=DocumentListResponse)
async def get_my_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's documents - no additional permissions needed.
    Users can always access their own resources.
    """
    documents = (
        db.query(Document)
        .filter(Document.owner_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    total = db.query(Document).filter(Document.owner_id == current_user.id).count()
    
    return DocumentListResponse(
        documents=[DocumentResponse.from_orm(doc) for doc in documents],
        total=total
    )


@router.post("/{document_id}/make-public", response_model=DocumentResponse)
@require(ResourceOwnership("document", lambda kwargs: kwargs.get("document_id")))
async def make_document_public(
    document_id: int,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Make document public - requires ownership.
    Shows ownership-only authorization pattern.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {document_id} not found"
        )
    
    document.is_public = True
    db.commit()
    db.refresh(document)
    
    return DocumentResponse.from_orm(document)


@router.post("/{document_id}/make-private", response_model=DocumentResponse)
@require(ResourceOwnership("document", lambda kwargs: kwargs.get("document_id")))
async def make_document_private(
    document_id: int,
    current_user: User = Depends(get_current_user),
    rbac = Depends(get_rbac_service),
    db: Session = Depends(get_db)
):
    """
    Make document private - requires ownership.
    Shows ownership-only authorization pattern.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {document_id} not found"
        )
    
    document.is_public = False
    db.commit()
    db.refresh(document)
    
    return DocumentResponse.from_orm(document)