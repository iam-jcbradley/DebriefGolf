from fastapi import FastAPI

from app.api.routes.bag import router as bag_router
from app.api.routes.health import router as health_router
from app.api.routes.rounds import router as rounds_router

app = FastAPI(title="Debrief Golf API")

app.include_router(health_router, prefix="/api")
app.include_router(rounds_router, prefix="/api")
app.include_router(bag_router, prefix="/api")
