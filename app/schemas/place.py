from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import PaginationMeta, TimestampedRead


class PlaceCreate(BaseModel):
    external_id: int = Field(gt=0, description="Art Institute artwork ID")
    notes: str | None = Field(default=None, max_length=5000)


class PlaceUpdate(BaseModel):
    notes: str | None = Field(default=None, max_length=5000)
    visited: bool | None = None

    @model_validator(mode="after")
    def reject_null_visited(self) -> "PlaceUpdate":
        if "visited" in self.model_fields_set and self.visited is None:
            raise ValueError("Visited must be true or false")
        return self


class PlaceRead(TimestampedRead):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    external_id: int
    title: str
    artist_display: str | None
    image_url: str | None
    notes: str | None
    visited: bool


class PlaceListResponse(BaseModel):
    items: list[PlaceRead]
    pagination: PaginationMeta
