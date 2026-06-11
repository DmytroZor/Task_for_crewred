import httpx
import pytest

from app.services.art_institute import ArtInstituteClient


@pytest.mark.anyio
async def test_artwork_responses_are_cached() -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            200,
            json={
                "data": {
                    "id": 27992,
                    "title": "A Sunday on La Grande Jatte - 1884",
                    "artist_display": "Georges Seurat",
                    "image_id": "image-identifier",
                },
                "config": {"iiif_url": "https://www.artic.edu/iiif/2"},
            },
        )

    client = ArtInstituteClient(
        base_url="https://api.artic.edu/api/v1",
        timeout_seconds=1,
        cache_ttl_seconds=300,
        user_agent="test-suite",
        transport=httpx.MockTransport(handler),
    )

    try:
        first = await client.get_artwork(27992)
        second = await client.get_artwork(27992)
    finally:
        await client.close()

    assert first == second
    assert request_count == 1
    assert first.image_url == (
        "https://www.artic.edu/iiif/2/image-identifier/full/843,/0/default.jpg"
    )
