from fastapi import APIRouter
from app.controllers.health_controller import read_health
from app.models.health import HealthStatus

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
def health():
    return read_health()