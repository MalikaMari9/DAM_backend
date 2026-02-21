import enum
from sqlalchemy import Column, BigInteger, Text, TIMESTAMP, Boolean, Enum as SAEnum, ForeignKey
from sqlalchemy.sql import func
from app.models.base import Base
from enum import Enum as PyEnum

class AccountRole(enum.Enum):
    ADMIN = "ADMIN"
    ORG = "ORG"


class OrgStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class OrgType(enum.Enum):
    WEATHER_STATION = "WEATHER_STATION"
    HOSPITAL = "HOSPITAL"
    RESEARCH_INSTITUTION = "RESEARCH_INSTITUTION"
    GOVERNMENT = "GOVERNMENT"
    OTHER = "OTHER"


class DataDomain(enum.Enum):
    HEALTH = "HEALTH"
    POLLUTION = "POLLUTION"


class ApplicationStatus(enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class UploadStatus(enum.Enum):
    RECEIVED = "RECEIVED"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"

class AnnouncementType(str, PyEnum):
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"