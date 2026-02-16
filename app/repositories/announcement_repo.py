from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime
from typing import Optional, List
from app.models.announcement import Announcement
from app.schemas.announcement_schema import AnnouncementCreate, AnnouncementUpdate


def create_announcement(db: Session, data: AnnouncementCreate, created_by_account_id: int) -> Announcement:
    """Create a new announcement"""
    announcement_data = data.model_dump()
    
    # Set default publish_at if not provided
    if announcement_data.get("publish_at") is None:
        announcement_data["publish_at"] = datetime.utcnow()
    
    db_announcement = Announcement(
        **announcement_data,
        created_by_account_id=created_by_account_id
    )
    db.add(db_announcement)
    db.commit()
    db.refresh(db_announcement)
    return db_announcement


def get_announcement(db: Session, announcement_id: int) -> Optional[Announcement]:
    """Get announcement by ID"""
    return db.query(Announcement).filter(Announcement.announcement_id == announcement_id).first()


def get_announcements(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = False,
    only_active: bool = True
) -> List[Announcement]:
    """Get list of announcements with filtering"""
    query = db.query(Announcement)
    
    if only_active:
        now = datetime.utcnow()
        query = query.filter(
            Announcement.is_active == True,
            Announcement.publish_at <= now,
            or_(Announcement.expires_at.is_(None), Announcement.expires_at > now)
        )
    elif not include_inactive:
        query = query.filter(Announcement.is_active == True)
    
    return query.order_by(Announcement.publish_at.desc()).offset(skip).limit(limit).all()


def get_all_announcements(
    db: Session,
    skip: int = 0,
    limit: int = 100
) -> List[Announcement]:
    """Get all announcements for admin view"""
    return db.query(Announcement).order_by(Announcement.created_at.desc()).offset(skip).limit(limit).all()


def count_announcements(db: Session, only_active: bool = True) -> int:
    """Count announcements"""
    query = db.query(Announcement)
    
    if only_active:
        now = datetime.utcnow()
        query = query.filter(
            Announcement.is_active == True,
            Announcement.publish_at <= now,
            or_(Announcement.expires_at.is_(None), Announcement.expires_at > now)
        )
    
    return query.count()


def update_announcement(
    db: Session,
    announcement: Announcement,
    data: AnnouncementUpdate
) -> Announcement:
    """Update an announcement"""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(announcement, field, value)
    
    db.commit()
    db.refresh(announcement)
    return announcement


def delete_announcement(db: Session, announcement: Announcement) -> None:
    """Delete an announcement"""
    db.delete(announcement)
    db.commit()


def get_active_announcements_for_home(db: Session, limit: int = 10) -> List[Announcement]:
    """Get active announcements for home page display"""
    now = datetime.utcnow()
    return db.query(Announcement).filter(
        Announcement.is_active == True,
        Announcement.publish_at <= now,
        or_(Announcement.expires_at.is_(None), Announcement.expires_at > now)
    ).order_by(Announcement.publish_at.desc()).limit(limit).all()