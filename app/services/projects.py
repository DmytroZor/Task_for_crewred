from math import ceil

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BusinessRuleError, ConflictError, ResourceNotFoundError
from app.models import Project, ProjectPlace
from app.schemas.common import PaginationMeta
from app.schemas.place import PlaceCreate, PlaceListResponse, PlaceRead, PlaceUpdate
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectSummary,
    ProjectUpdate,
)
from app.services.art_institute import ArtInstituteClient, Artwork

MAX_PLACES_PER_PROJECT = 10


async def create_project(
    session: AsyncSession,
    payload: ProjectCreate,
    art_client: ArtInstituteClient,
) -> Project:
    external_ids = [place.external_id for place in payload.places]
    artworks = await art_client.get_artworks(external_ids)

    project = Project(
        name=payload.name,
        description=payload.description,
        start_date=payload.start_date,
        places=[_build_place(place, artworks[place.external_id]) for place in payload.places],
    )
    session.add(project)
    await session.commit()
    return await get_project(session, project.id)


async def list_projects(
    session: AsyncSession,
    page: int,
    page_size: int,
    name: str | None,
    completed: bool | None,
) -> ProjectListResponse:
    filters = []
    if name:
        filters.append(Project.name.ilike(f"%{name}%"))
    if completed is not None:
        filters.append(Project.completed.is_(completed))

    total = await session.scalar(select(func.count(Project.id)).where(*filters)) or 0
    result = await session.scalars(
        select(Project)
        .where(*filters)
        .order_by(Project.created_at.desc(), Project.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return ProjectListResponse(
        items=[ProjectSummary.model_validate(project) for project in result],
        pagination=_pagination(page, page_size, total),
    )


async def get_project(session: AsyncSession, project_id: int) -> Project:
    project = await session.scalar(
        select(Project).options(selectinload(Project.places)).where(Project.id == project_id)
    )
    if project is None:
        raise ResourceNotFoundError("Travel project not found")
    return project


async def update_project(session: AsyncSession, project_id: int, payload: ProjectUpdate) -> Project:
    project = await get_project(session, project_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await session.commit()
    return await get_project(session, project_id)


async def delete_project(session: AsyncSession, project_id: int) -> None:
    project = await get_project(session, project_id)
    if any(place.visited for place in project.places):
        raise ConflictError("A project containing visited places cannot be deleted")
    await session.delete(project)
    await session.commit()


async def add_place(
    session: AsyncSession,
    project_id: int,
    payload: PlaceCreate,
    art_client: ArtInstituteClient,
) -> ProjectPlace:
    project = await get_project(session, project_id)
    if len(project.places) >= MAX_PLACES_PER_PROJECT:
        raise BusinessRuleError(
            f"A project cannot contain more than {MAX_PLACES_PER_PROJECT} places"
        )
    if any(place.external_id == payload.external_id for place in project.places):
        raise ConflictError("This place is already included in the project")

    artwork = await art_client.get_artwork(payload.external_id)
    place = _build_place(payload, artwork)
    project.places.append(place)
    project.completed = False
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("This place is already included in the project") from exc
    await session.refresh(place)
    return place


async def list_places(
    session: AsyncSession,
    project_id: int,
    page: int,
    page_size: int,
    visited: bool | None,
) -> PlaceListResponse:
    await _ensure_project_exists(session, project_id)
    filters = [ProjectPlace.project_id == project_id]
    if visited is not None:
        filters.append(ProjectPlace.visited.is_(visited))

    total = await session.scalar(select(func.count(ProjectPlace.id)).where(*filters)) or 0
    result = await session.scalars(
        select(ProjectPlace)
        .where(*filters)
        .order_by(ProjectPlace.created_at.desc(), ProjectPlace.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return PlaceListResponse(
        items=[PlaceRead.model_validate(place) for place in result],
        pagination=_pagination(page, page_size, total),
    )


async def get_place(session: AsyncSession, project_id: int, place_id: int) -> ProjectPlace:
    place = await session.scalar(
        select(ProjectPlace).where(
            ProjectPlace.id == place_id,
            ProjectPlace.project_id == project_id,
        )
    )
    if place is None:
        raise ResourceNotFoundError("Place not found in this project")
    return place


async def update_place(
    session: AsyncSession,
    project_id: int,
    place_id: int,
    payload: PlaceUpdate,
) -> ProjectPlace:
    place = await get_place(session, project_id, place_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(place, field, value)

    if "visited" in updates:
        project = await get_project(session, project_id)
        project.completed = all(item.visited for item in project.places)

    await session.commit()
    return await get_place(session, project_id, place_id)


async def _ensure_project_exists(session: AsyncSession, project_id: int) -> None:
    exists = await session.scalar(select(Project.id).where(Project.id == project_id))
    if exists is None:
        raise ResourceNotFoundError("Travel project not found")


def _build_place(payload: PlaceCreate, artwork: Artwork) -> ProjectPlace:
    return ProjectPlace(
        external_id=artwork.external_id,
        title=artwork.title,
        artist_display=artwork.artist_display,
        image_url=artwork.image_url,
        notes=payload.notes,
    )


def _pagination(page: int, page_size: int, total: int) -> PaginationMeta:
    return PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        pages=ceil(total / page_size) if total else 0,
    )
