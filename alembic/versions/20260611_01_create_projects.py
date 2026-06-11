"""Create projects and project places.

Revision ID: 20260611_01
Revises:
Create Date: 2026-06-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260611_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
    )
    op.create_index(op.f("ix_projects_completed"), "projects", ["completed"])
    op.create_index(op.f("ix_projects_name"), "projects", ["name"])

    op.create_table(
        "project_places",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("artist_display", sa.String(length=1000), nullable=True),
        sa.Column("image_url", sa.String(length=2000), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("visited", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(notes) <= 5000",
            name=op.f("ck_project_places_notes_max_length"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_places_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_places")),
        sa.UniqueConstraint(
            "project_id",
            "external_id",
            name=op.f("uq_project_places_project_id"),
        ),
    )
    op.create_index(op.f("ix_project_places_project_id"), "project_places", ["project_id"])
    op.create_index(op.f("ix_project_places_visited"), "project_places", ["visited"])


def downgrade() -> None:
    op.drop_index(op.f("ix_project_places_visited"), table_name="project_places")
    op.drop_index(op.f("ix_project_places_project_id"), table_name="project_places")
    op.drop_table("project_places")
    op.drop_index(op.f("ix_projects_name"), table_name="projects")
    op.drop_index(op.f("ix_projects_completed"), table_name="projects")
    op.drop_table("projects")
