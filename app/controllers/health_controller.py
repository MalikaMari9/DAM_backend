from app.repositories.health_repo import get_health_status


def read_health():
    return get_health_status()