from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import PaginationMeta, TimestampedRead
from app.schemas.place import PlaceCreate, PlaceRead


class ProjectFields(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=5000)
    start_date: date | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name must not be blank")
        return normalized


class ProjectCreate(ProjectFields):
    places: list[PlaceCreate] = Field(min_length=1, max_length=10)

    @field_validator("places")
    @classmethod
    def reject_duplicate_places(cls, places: list[PlaceCreate]) -> list[PlaceCreate]:
        external_ids = [place.external_id for place in places]
        if len(external_ids) != len(set(external_ids)):
            raise ValueError("A project cannot contain duplicate external place IDs")
        return places


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=5000)
    start_date: date | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name must not be blank")
        return normalized

    @model_validator(mode="after")
    def reject_null_name(self) -> "ProjectUpdate":
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Name must not be null")
        return self


class ProjectSummary(TimestampedRead):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    start_date: date | None
    completed: bool


class ProjectRead(ProjectSummary):
    places: list[PlaceRead]


class ProjectListResponse(BaseModel):
    items: list[ProjectSummary]
    pagination: PaginationMeta
