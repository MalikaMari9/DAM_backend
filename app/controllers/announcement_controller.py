from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.schemas.announcement_schema import (
    AnnouncementCreate,
    AnnouncementUpdate,
    AnnouncementResponse,
    AnnouncementListResponse
)
from app.repositories import announcement_repo
from app.models.account_model import Account


def create_announcement(
    db: Session,
    data: AnnouncementCreate,
    current_account: Account
) -> AnnouncementResponse:
    """Create a new announcement"""
    announcement = announcement_repo.create_announcement(
        db=db,
        data=data,
        created_by_account_id=current_account.account_id
    )
    return AnnouncementResponse.model_validate(announcement)


def get_announcement(
    db: Session,
    announcement_id: int
) -> AnnouncementResponse:
    """Get announcement by ID"""
    announcement = announcement_repo.get_announcement(db, announcement_id)
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found"
        )
    return AnnouncementResponse.model_validate(announcement)


def get_announcements(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    admin_view: bool = False
) -> AnnouncementListResponse:
    """Get list of announcements"""
    if admin_view:
        # Admin sees all announcements
        announcements = announcement_repo.get_all_announcements(db, skip=skip, limit=limit)
        total = announcement_repo.count_announcements(db, only_active=False)
    else:
        # Public only sees active announcements
        announcements = announcement_repo.get_announcements(db, skip=skip, limit=limit, only_active=True)
        total = announcement_repo.count_announcements(db, only_active=True)
    
    return AnnouncementListResponse(
        items=[AnnouncementResponse.model_validate(a) for a in announcements],
        total=total
    )


def update_announcement(
    db: Session,
    announcement_id: int,
    data: AnnouncementUpdate,
    current_account: Account
) -> AnnouncementResponse:
    """Update an announcement"""
    announcement = announcement_repo.get_announcement(db, announcement_id)
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found"
        )
    
    updated = announcement_repo.update_announcement(db, announcement, data)
    return AnnouncementResponse.model_validate(updated)


def delete_announcement(
    db: Session,
    announcement_id: int,
    current_account: Account
) -> Dict[str, str]:
    """Delete an announcement"""
    announcement = announcement_repo.get_announcement(db, announcement_id)
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found"
        )
    
    announcement_repo.delete_announcement(db, announcement)
    return {"status": "ok", "message": "Announcement deleted successfully"}


def get_active_announcements_for_home(db: Session, limit: int = 10) -> List[AnnouncementResponse]:
    """Get active announcements for home page"""
    announcements = announcement_repo.get_active_announcements_for_home(db, limit=limit)
    return [AnnouncementResponse.model_validate(a) for a in announcements]