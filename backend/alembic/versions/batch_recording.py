"""Add recorded batch summaries to predictions.

Revision ID: batch_recording
Revises: 8e1f2a3b4c5d
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "batch_recording"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "predictions",
        sa.Column("batch_recorded", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("predictions", sa.Column("batch_recorded_at", sa.DateTime()))
    for name in (
        "okay_count",
        "stained_count",
        "batch_damaged_count",
        "batch_review_count",
    ):
        op.add_column(
            "predictions",
            sa.Column(name, sa.Integer(), nullable=False, server_default="0"),
        )
    op.create_index(
        "ix_predictions_batch_recorded", "predictions", ["batch_recorded"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_predictions_batch_recorded", table_name="predictions")
    for name in (
        "batch_review_count",
        "batch_damaged_count",
        "stained_count",
        "okay_count",
        "batch_recorded_at",
        "batch_recorded",
    ):
        op.drop_column("predictions", name)
