from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import ArtClient
from app.core.auth import require_basic_auth
from app.db.session import get_db
from app.schemas.place import PlaceCreate, PlaceListResponse, PlaceRead, PlaceUpdate
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectRead,
    ProjectUpdate,
)
from app.services import projects as project_service

router = APIRouter(
    prefix="/projects",
    tags=["Travel projects"],
    dependencies=[Depends(require_basic_auth)],
)
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    session: DbSession,
    art_client: ArtClient,
) -> ProjectRead:
    project = await project_service.create_project(session, payload, art_client)
    return ProjectRead.model_validate(project)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    session: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    name: Annotated[str | None, Query(max_length=120)] = None,
    completed: bool | None = None,
) -> ProjectListResponse:
    return await project_service.list_projects(session, page, page_size, name, completed)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: int, session: DbSession) -> ProjectRead:
    project = await project_service.get_project(session, project_id)
    return ProjectRead.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    session: DbSession,
) -> ProjectRead:
    project = await project_service.update_project(session, project_id, payload)
    return ProjectRead.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, session: DbSession) -> Response:
    await project_service.delete_project(session, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{project_id}/places",
    response_model=PlaceRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_place(
    project_id: int,
    payload: PlaceCreate,
    session: DbSession,
    art_client: ArtClient,
) -> PlaceRead:
    place = await project_service.add_place(session, project_id, payload, art_client)
    return PlaceRead.model_validate(place)


@router.get("/{project_id}/places", response_model=PlaceListResponse)
async def list_places(
    project_id: int,
    session: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    visited: bool | None = None,
) -> PlaceListResponse:
    return await project_service.list_places(session, project_id, page, page_size, visited)


@router.get("/{project_id}/places/{place_id}", response_model=PlaceRead)
async def get_place(project_id: int, place_id: int, session: DbSession) -> PlaceRead:
    place = await project_service.get_place(session, project_id, place_id)
    return PlaceRead.model_validate(place)


@router.patch("/{project_id}/places/{place_id}", response_model=PlaceRead)
async def update_place(
    project_id: int,
    place_id: int,
    payload: PlaceUpdate,
    session: DbSession,
) -> PlaceRead:
    place = await project_service.update_place(session, project_id, place_id, payload)
    return PlaceRead.model_validate(place)
