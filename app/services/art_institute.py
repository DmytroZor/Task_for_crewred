import asyncio
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.exceptions import ExternalServiceError, ResourceNotFoundError

ARTWORK_FIELDS = "id,title,artist_display,image_id"


@dataclass(frozen=True, slots=True)
class Artwork:
    external_id: int
    title: str
    artist_display: str | None
    image_url: str | None


class ArtInstituteClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        cache_ttl_seconds: int,
        user_agent: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            headers={"AIC-User-Agent": user_agent, "Accept": "application/json"},
            transport=transport,
        )
        self._cache_ttl = cache_ttl_seconds
        self._cache: dict[int, tuple[float, Artwork]] = {}
        self._lock = asyncio.Lock()

    async def close(self) -> None:
        await self._client.aclose()

    async def get_artwork(self, external_id: int) -> Artwork:
        cached = await self._get_cached(external_id)
        if cached is not None:
            return cached

        payload = await self._request(
            f"/artworks/{external_id}",
            params={"fields": ARTWORK_FIELDS},
        )
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ExternalServiceError("Art Institute API returned an invalid artwork payload")
        artwork = self._parse_artwork(data, payload.get("config", {}))
        await self._store_cached(artwork)
        return artwork

    async def get_artworks(self, external_ids: list[int]) -> dict[int, Artwork]:
        artworks: dict[int, Artwork] = {}
        missing_ids: list[int] = []

        for external_id in external_ids:
            cached = await self._get_cached(external_id)
            if cached is None:
                missing_ids.append(external_id)
            else:
                artworks[external_id] = cached

        if missing_ids:
            payload = await self._request(
                "/artworks",
                params={
                    "ids": ",".join(str(external_id) for external_id in missing_ids),
                    "limit": len(missing_ids),
                    "fields": ARTWORK_FIELDS,
                },
            )
            items = payload.get("data")
            if not isinstance(items, list):
                raise ExternalServiceError("Art Institute API returned an invalid artwork list")
            for item in items:
                artwork = self._parse_artwork(item, payload.get("config", {}))
                artworks[artwork.external_id] = artwork
                await self._store_cached(artwork)

        unknown_ids = set(external_ids) - artworks.keys()
        if unknown_ids:
            ids = ", ".join(str(value) for value in sorted(unknown_ids))
            raise ResourceNotFoundError(f"Art Institute artwork(s) not found: {ids}")
        return artworks

    async def _request(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._client.get(path, params=params)
        except httpx.RequestError as exc:
            raise ExternalServiceError("Could not reach the Art Institute of Chicago API") from exc

        if response.status_code == 404:
            raise ResourceNotFoundError("Art Institute artwork not found")
        if response.is_error:
            raise ExternalServiceError(f"Art Institute API returned HTTP {response.status_code}")

        try:
            return response.json()
        except ValueError as exc:
            raise ExternalServiceError("Art Institute API returned an invalid response") from exc

    def _parse_artwork(self, data: dict[str, Any], config: dict[str, Any]) -> Artwork:
        try:
            external_id = int(data["id"])
            image_id = data.get("image_id")
            iiif_url = config.get("iiif_url")
            image_url = (
                f"{iiif_url}/{image_id}/full/843,/0/default.jpg" if image_id and iiif_url else None
            )
            return Artwork(
                external_id=external_id,
                title=data.get("title") or f"Artwork {external_id}",
                artist_display=data.get("artist_display"),
                image_url=image_url,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ExternalServiceError("Art Institute API returned malformed artwork data") from exc

    async def _get_cached(self, external_id: int) -> Artwork | None:
        if self._cache_ttl == 0:
            return None
        async with self._lock:
            cached = self._cache.get(external_id)
            if cached is None:
                return None
            expires_at, artwork = cached
            if expires_at <= time.monotonic():
                self._cache.pop(external_id, None)
                return None
            return artwork

    async def _store_cached(self, artwork: Artwork) -> None:
        if self._cache_ttl == 0:
            return
        async with self._lock:
            self._cache[artwork.external_id] = (
                time.monotonic() + self._cache_ttl,
                artwork,
            )
