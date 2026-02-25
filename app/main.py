from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.health import router as health_router
from app.routes.auth import router as auth_router
from app.routes.orgs import router as orgs_router
from app.routes.org_applications import router as org_applications_router
from app.routes.files import router as files_router
from app.routes.uploads import router as uploads_router
from app.routes.admin import router as admin_router
from app.routes.health_imhe import router as health_imhe_router
from app.routes.pollution_openaq import router as pollution_openaq_router
from app.routes.pollution_who import router as pollution_who_router
from app.routes.pollution_acag import router as pollution_acag_router
from app.routes.announcements import router as announcements_router
from app.routes.ai_proxy import router as ai_proxy_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(orgs_router)
app.include_router(org_applications_router)
app.include_router(files_router)
app.include_router(uploads_router)
app.include_router(admin_router)
app.include_router(health_imhe_router)
app.include_router(pollution_openaq_router)
app.include_router(pollution_who_router)
app.include_router(pollution_acag_router)
app.include_router(announcements_router)
app.include_router(ai_proxy_router)



