from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.bag import router as bag_router
from app.api.routes.courses import router as courses_router
from app.api.routes.garmin_auth import router as garmin_auth_router
from app.api.routes.health import router as health_router
from app.api.routes.practice import router as practice_router
from app.api.routes.privacy import router as privacy_router
from app.api.routes.rounds import router as rounds_router
from app.api.routes.virtual_rounds import router as virtual_rounds_router
from app.core.config import settings

app = FastAPI(title="Debrief Golf API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(rounds_router, prefix="/api")
app.include_router(bag_router, prefix="/api")
app.include_router(courses_router, prefix="/api")
app.include_router(garmin_auth_router, prefix="/api")
app.include_router(practice_router, prefix="/api")
app.include_router(virtual_rounds_router, prefix="/api")
app.include_router(privacy_router, prefix="/api")
