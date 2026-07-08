"""add interview invitations and slots

Revision ID: 003_add_interview_tables
Revises: 002_add_google_oauth
Create Date: 2026-05-16 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "003_add_interview_tables"
down_revision = "002_add_google_oauth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    invitation_status = postgresql.ENUM(
        "PENDING", "CONFIRMED", "EXPIRED", "CANCELLED",
        name="invitation_status",
        create_type=True,
    )
    invitation_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "interview_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "CONFIRMED", "EXPIRED", "CANCELLED",
                                     name="invitation_status"),
                  nullable=False, server_default="PENDING"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_slot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("token", name="uq_invitations_token"),
    )
    op.create_index("ix_interview_invitations_token", "interview_invitations", ["token"])
    op.create_index("ix_interview_invitations_status", "interview_invitations", ["status"])
    op.create_index("ix_invitations_app_status", "interview_invitations",
                    ["application_id", "status"])

    op.create_table(
        "interview_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("invitation_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("interview_invitations.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_selected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_slots_invitation", "interview_slots", ["invitation_id"])
    op.create_index("ix_slots_start_selected", "interview_slots", ["start_at", "is_selected"])
    op.create_index("ix_interview_slots_start_at", "interview_slots", ["start_at"])
    op.create_index("ix_interview_slots_is_selected", "interview_slots", ["is_selected"])

    # Now the FK from invitations to slots (deferred)
    op.create_foreign_key(
        "fk_invitations_confirmed_slot",
        "interview_invitations",
        "interview_slots",
        ["confirmed_slot_id"],
        ["id"],
        ondelete="SET NULL",
        use_alter=True,
    )


def downgrade() -> None:
    op.drop_constraint("fk_invitations_confirmed_slot", "interview_invitations", type_="foreignkey")
    op.drop_index("ix_interview_slots_is_selected", table_name="interview_slots")
    op.drop_index("ix_interview_slots_start_at", table_name="interview_slots")
    op.drop_index("ix_slots_start_selected", table_name="interview_slots")
    op.drop_index("ix_slots_invitation", table_name="interview_slots")
    op.drop_table("interview_slots")

    op.drop_index("ix_invitations_app_status", table_name="interview_invitations")
    op.drop_index("ix_interview_invitations_status", table_name="interview_invitations")
    op.drop_index("ix_interview_invitations_token", table_name="interview_invitations")
    op.drop_table("interview_invitations")

    invitation_status = postgresql.ENUM(name="invitation_status")
    invitation_status.drop(op.get_bind(), checkfirst=True)
