from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes.projects import router as projects_router
from app.core.config import get_settings
from app.core.exceptions import ApplicationError
from app.db.session import close_db, init_db
from app.services.art_institute import ArtInstituteClient

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if settings.auto_create_tables:
        await init_db()
    app.state.art_client = ArtInstituteClient(
        base_url=settings.art_institute_base_url,
        timeout_seconds=settings.art_institute_timeout_seconds,
        cache_ttl_seconds=settings.art_institute_cache_ttl_seconds,
        user_agent=settings.art_institute_user_agent,
    )
    yield
    await app.state.art_client.close()
    await close_db()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Manage travel projects and artwork-based places imported from the "
        "Art Institute of Chicago."
    ),
    lifespan=lifespan,
)
app.include_router(projects_router, prefix="/api/v1")


@app.exception_handler(ApplicationError)
async def handle_application_error(request: Request, exc: ApplicationError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.get("/health", tags=["System"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
