from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from app.core.db import get_db
from app.core.auth import get_current_account, require_admin
from app.schemas.announcement_schema import (
    AnnouncementCreate,
    AnnouncementUpdate,
    AnnouncementResponse,
    AnnouncementListResponse
)
from app.controllers import announcement_controller

router = APIRouter(prefix="/announcements", tags=["announcements"])


# Public endpoints
@router.get("/public", response_model=AnnouncementListResponse)
def get_public_announcements(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get active announcements for public view"""
    return announcement_controller.get_announcements(db, skip=skip, limit=limit, admin_view=False)


@router.get("/public/home", response_model=list[AnnouncementResponse])
def get_home_announcements(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """Get active announcements for home page display"""
    return announcement_controller.get_active_announcements_for_home(db, limit=limit)


# Admin endpoints
@router.post("/admin", response_model=AnnouncementResponse)
def create_announcement(
    data: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_account = Depends(require_admin)
):
    """Create a new announcement (admin only)"""
    return announcement_controller.create_announcement(db, data, current_account)


@router.get("/admin", response_model=AnnouncementListResponse)
def get_all_announcements(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_account = Depends(require_admin)
):
    """Get all announcements for admin view"""
    return announcement_controller.get_announcements(db, skip=skip, limit=limit, admin_view=True)


@router.get("/admin/{announcement_id}", response_model=AnnouncementResponse)
def get_announcement_by_id(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_account = Depends(require_admin)
):
    """Get announcement by ID (admin only)"""
    return announcement_controller.get_announcement(db, announcement_id)


@router.put("/admin/{announcement_id}", response_model=AnnouncementResponse)
def update_announcement(
    announcement_id: int,
    data: AnnouncementUpdate,
    db: Session = Depends(get_db),
    current_account = Depends(require_admin)
):
    """Update an announcement (admin only)"""
    return announcement_controller.update_announcement(db, announcement_id, data, current_account)


@router.delete("/admin/{announcement_id}")
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_account = Depends(require_admin)
):
    """Delete an announcement (admin only)"""
    return announcement_controller.delete_announcement(db, announcement_id, current_account)