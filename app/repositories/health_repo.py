from app.models.health import HealthStatus


def get_health_status() -> HealthStatus:
    return HealthStatus(status="ok")