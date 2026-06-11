# Travel Planner API

REST API for managing travel projects and the places travellers want to visit.
For this assessment, a "place" is represented by an artwork imported from the
[Art Institute of Chicago API](https://api.artic.edu/docs/#collections).

## Features

- Create, read, update, filter, paginate, and delete travel projects.
- Create a project with 1-10 Art Institute artworks in one request.
- Validate every external artwork before storing it.
- Add places while preventing duplicates and enforcing the 10-place limit.
- Update notes and visited state for each place.
- Mark a project completed automatically when all its places are visited.
- Prevent deletion when at least one place has been visited.
- Cache Art Institute responses in memory with a configurable TTL.
- Protect application endpoints with HTTP Basic authentication.
- Persist data asynchronously with SQLAlchemy 2 and SQLite.
- Manage schema changes with Alembic.
- Test business rules without making real third-party HTTP calls.

## Tech Stack

- Python 3.11+
- FastAPI
- SQLAlchemy 2 (async)
- SQLite / aiosqlite
- Alembic
- HTTPX
- Pydantic 2
- Pytest

## Project Structure

```text
app/
  api/          # FastAPI dependencies and route handlers
  core/         # Settings, authentication, application errors
  db/           # SQLAlchemy base, engine, and sessions
  models/       # ORM entities
  schemas/      # Request and response models
  services/     # Business logic and Art Institute client
alembic/        # Database migration environment and revisions
tests/          # API and business-rule tests
```

## Local Setup

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

The development default `AUTO_CREATE_TABLES=true` creates missing tables on
startup. Alembic remains the recommended schema-management path; set
`AUTO_CREATE_TABLES=false` in deployment after running `alembic upgrade head`.

## Docker

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

## Configuration

Copy `.env.example` to `.env` and adjust:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./travel_planner.db` | Async SQLAlchemy URL |
| `API_USERNAME` | `admin` | HTTP Basic username |
| `API_PASSWORD` | `change-me` | HTTP Basic password |
| `ART_INSTITUTE_BASE_URL` | `https://api.artic.edu/api/v1` | Third-party API URL |
| `ART_INSTITUTE_TIMEOUT_SECONDS` | `10` | Third-party request timeout |
| `ART_INSTITUTE_CACHE_TTL_SECONDS` | `300` | In-memory cache lifetime |
| `ART_INSTITUTE_USER_AGENT` | example value | Courtesy identification header |
| `AUTO_CREATE_TABLES` | `true` | Create missing tables at startup |

Change the default credentials outside local development.

## API Documentation

FastAPI generates the complete OpenAPI specification and interactive clients:

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- OpenAPI JSON: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

Use the **Authorize** button in Swagger UI and enter the configured Basic Auth
credentials.

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check (public) |
| `POST` | `/api/v1/projects` | Create a project with places |
| `GET` | `/api/v1/projects` | List/filter/paginate projects |
| `GET` | `/api/v1/projects/{project_id}` | Get a project and its places |
| `PATCH` | `/api/v1/projects/{project_id}` | Update project information |
| `DELETE` | `/api/v1/projects/{project_id}` | Delete an eligible project |
| `POST` | `/api/v1/projects/{project_id}/places` | Validate and add a place |
| `GET` | `/api/v1/projects/{project_id}/places` | List/filter/paginate places |
| `GET` | `/api/v1/projects/{project_id}/places/{place_id}` | Get one place |
| `PATCH` | `/api/v1/projects/{project_id}/places/{place_id}` | Update notes/visited |

Project list filters: `name`, `completed`, `page`, `page_size`.

Place list filters: `visited`, `page`, `page_size`.

## Example Requests

Create a project:

```bash
curl -u admin:change-me \
  -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Chicago museum weekend",
    "description": "Works to see on Saturday",
    "start_date": "2026-07-10",
    "places": [
      {"external_id": 27992, "notes": "Start here"},
      {"external_id": 28560}
    ]
  }'
```

Add a place:

```bash
curl -u admin:change-me \
  -X POST http://localhost:8000/api/v1/projects/1/places \
  -H "Content-Type: application/json" \
  -d '{"external_id": 129884, "notes": "See before lunch"}'
```

Mark a place visited:

```bash
curl -u admin:change-me \
  -X PATCH http://localhost:8000/api/v1/projects/1/places/1 \
  -H "Content-Type: application/json" \
  -d '{"visited": true, "notes": "Visited on July 10"}'
```

Filter completed projects:

```bash
curl -u admin:change-me \
  "http://localhost:8000/api/v1/projects?completed=true&page=1&page_size=20"
```

## Error Semantics

- `401 Unauthorized`: missing or invalid Basic Auth credentials.
- `404 Not Found`: local resource or Art Institute artwork does not exist.
- `409 Conflict`: duplicate place or deletion of a project with visited places.
- `422 Unprocessable Entity`: malformed input or a business limit violation.
- `503 Service Unavailable`: Art Institute API timeout or upstream failure.

## Tests and Quality Checks

```bash
pytest
ruff check .
ruff format --check .
```

Tests use an in-memory SQLite database and a fake Art Institute client, making
them deterministic and safe to run offline.

## Design Notes

- Third-party metadata is snapshotted when a place is added, so project reads do
  not depend on Art Institute availability.
- Project creation uses the Art Institute multi-ID endpoint to validate up to 10
  artworks in one HTTP request.
- Cache scope is process-local, which is sufficient for this assessment. A
  shared Redis cache would be appropriate for a multi-instance deployment.
- HTTP Basic satisfies the assessment requirement. Production systems should
  use TLS and preferably short-lived token-based authentication.
