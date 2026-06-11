import pytest
from httpx import AsyncClient

from tests.conftest import FakeArtInstituteClient


def project_payload(*external_ids: int) -> dict:
    return {
        "name": "Chicago art trip",
        "description": "A weekend at the museum",
        "start_date": "2026-07-10",
        "places": [
            {"external_id": external_id, "notes": f"See {external_id}"}
            for external_id in external_ids
        ],
    }


@pytest.mark.anyio
async def test_authentication_is_required(client: AsyncClient) -> None:
    response = await client.get("/api/v1/projects", auth=None)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Basic"


@pytest.mark.anyio
async def test_create_and_get_project_with_places(
    client: AsyncClient,
    fake_art_client: FakeArtInstituteClient,
) -> None:
    created = await client.post("/api/v1/projects", json=project_payload(27992, 28560))

    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Chicago art trip"
    assert body["completed"] is False
    assert [place["external_id"] for place in body["places"]] == [27992, 28560]
    assert fake_art_client.requested_ids == [27992, 28560]

    fetched = await client.get(f"/api/v1/projects/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


@pytest.mark.anyio
async def test_project_requires_one_to_ten_unique_places(
    client: AsyncClient,
) -> None:
    no_places = await client.post(
        "/api/v1/projects",
        json={**project_payload(1), "places": []},
    )
    duplicates = await client.post(
        "/api/v1/projects",
        json=project_payload(1, 1),
    )
    too_many = await client.post(
        "/api/v1/projects",
        json=project_payload(*range(1, 12)),
    )

    assert no_places.status_code == 422
    assert duplicates.status_code == 422
    assert too_many.status_code == 422


@pytest.mark.anyio
async def test_place_limit_and_duplicates_are_enforced(
    client: AsyncClient,
    fake_art_client: FakeArtInstituteClient,
) -> None:
    response = await client.post(
        "/api/v1/projects",
        json=project_payload(*range(1, 11)),
    )
    project_id = response.json()["id"]

    duplicate = await client.post(
        f"/api/v1/projects/{project_id}/places",
        json={"external_id": 1},
    )
    over_limit = await client.post(
        f"/api/v1/projects/{project_id}/places",
        json={"external_id": 11},
    )

    assert duplicate.status_code == 422
    assert over_limit.status_code == 422
    assert 11 not in fake_art_client.requested_ids


@pytest.mark.anyio
async def test_project_completes_when_all_places_are_visited_and_cannot_be_deleted(
    client: AsyncClient,
) -> None:
    response = await client.post("/api/v1/projects", json=project_payload(10, 20))
    project = response.json()
    first, second = project["places"]

    first_update = await client.patch(
        f"/api/v1/projects/{project['id']}/places/{first['id']}",
        json={"visited": True, "notes": "Visited in the morning"},
    )
    assert first_update.status_code == 200
    assert first_update.json()["notes"] == "Visited in the morning"

    in_progress = await client.get(f"/api/v1/projects/{project['id']}")
    assert in_progress.json()["completed"] is False

    await client.patch(
        f"/api/v1/projects/{project['id']}/places/{second['id']}",
        json={"visited": True},
    )
    completed = await client.get(f"/api/v1/projects/{project['id']}")
    assert completed.json()["completed"] is True

    deletion = await client.delete(f"/api/v1/projects/{project['id']}")
    assert deletion.status_code == 409


@pytest.mark.anyio
async def test_unvisited_project_can_be_updated_and_deleted(
    client: AsyncClient,
) -> None:
    response = await client.post("/api/v1/projects", json=project_payload(42))
    project_id = response.json()["id"]

    updated = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Updated trip", "description": None},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated trip"
    assert updated.json()["description"] is None

    deleted = await client.delete(f"/api/v1/projects/{project_id}")
    assert deleted.status_code == 204
    assert (await client.get(f"/api/v1/projects/{project_id}")).status_code == 404


@pytest.mark.anyio
async def test_non_nullable_updates_reject_explicit_null(
    client: AsyncClient,
) -> None:
    response = await client.post("/api/v1/projects", json=project_payload(42))
    project = response.json()

    project_update = await client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"name": None},
    )
    place_update = await client.patch(
        f"/api/v1/projects/{project['id']}/places/{project['places'][0]['id']}",
        json={"visited": None},
    )

    assert project_update.status_code == 422
    assert place_update.status_code == 422


@pytest.mark.anyio
async def test_project_and_place_lists_support_filters_and_pagination(
    client: AsyncClient,
) -> None:
    await client.post("/api/v1/projects", json=project_payload(1))
    second = await client.post(
        "/api/v1/projects",
        json={**project_payload(2), "name": "Paris sketches"},
    )
    second_body = second.json()
    place_id = second_body["places"][0]["id"]
    await client.patch(
        f"/api/v1/projects/{second_body['id']}/places/{place_id}",
        json={"visited": True},
    )

    projects = await client.get(
        "/api/v1/projects",
        params={"completed": True, "name": "Paris", "page_size": 1},
    )
    assert projects.status_code == 200
    assert projects.json()["pagination"] == {
        "page": 1,
        "page_size": 1,
        "total": 1,
        "pages": 1,
    }
    assert projects.json()["items"][0]["name"] == "Paris sketches"

    places = await client.get(
        f"/api/v1/projects/{second_body['id']}/places",
        params={"visited": True},
    )
    assert places.status_code == 200
    assert places.json()["pagination"]["total"] == 1
