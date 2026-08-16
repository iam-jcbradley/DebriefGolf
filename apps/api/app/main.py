from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.bag import router as bag_router
from app.api.routes.courses import router as courses_router
from app.api.routes.garmin_auth import router as garmin_auth_router
from app.api.routes.health import router as health_router
from app.api.routes.practice import router as practice_router
from app.api.routes.privacy import router as privacy_router
from app.api.routes.rounds import router as rounds_router
from app.api.routes.virtual_rounds import router as virtual_rounds_router
from app.api.uploads import RequestSizeLimitMiddleware
from app.core.config import settings

app = FastAPI(title="Debrief Golf API")

# Outermost: rejects an oversized request before routing or body parsing,
# so an upload that's far too large never gets spooled. See app/api/uploads.py.
app.add_middleware(RequestSizeLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # Required for the session cookie to be sent on the web app's fetches.
    # It also forbids `allow_origins=["*"]` — the browser rejects a wildcard
    # on a credentialed request — which is why the origin list is explicit.
    allow_credentials=True,
    # Was `["*"]` for both before Phase 10. Now that requests carry
    # credentials, the wildcard is worth spending the ten seconds to narrow:
    # these are the methods and headers the frontend actually sends.
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(rounds_router, prefix="/api")
app.include_router(bag_router, prefix="/api")
app.include_router(courses_router, prefix="/api")
app.include_router(garmin_auth_router, prefix="/api")
app.include_router(practice_router, prefix="/api")
app.include_router(virtual_rounds_router, prefix="/api")
app.include_router(privacy_router, prefix="/api")
