from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_art_client
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.art_institute import Artwork


class FakeArtInstituteClient:
    def __init__(self) -> None:
        self.requested_ids: list[int] = []

    async def get_artwork(self, external_id: int) -> Artwork:
        self.requested_ids.append(external_id)
        return self._artwork(external_id)

    async def get_artworks(self, external_ids: list[int]) -> dict[int, Artwork]:
        self.requested_ids.extend(external_ids)
        return {external_id: self._artwork(external_id) for external_id in external_ids}

    @staticmethod
    def _artwork(external_id: int) -> Artwork:
        return Artwork(
            external_id=external_id,
            title=f"Artwork {external_id}",
            artist_display=f"Artist {external_id}",
            image_url=f"https://images.example/{external_id}.jpg",
        )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def fake_art_client() -> FakeArtInstituteClient:
    return FakeArtInstituteClient()


@pytest.fixture
async def client(
    fake_art_client: FakeArtInstituteClient,
) -> AsyncIterator[AsyncClient]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_art_client] = lambda: fake_art_client

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        auth=("admin", "change-me"),
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    await engine.dispose()
