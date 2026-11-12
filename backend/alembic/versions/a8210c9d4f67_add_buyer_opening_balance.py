"""Add buyer opening balances.

Revision ID: a8210c9d4f67
Revises: 54ad8c217f90
Create Date: 2026-11-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8210c9d4f67"
down_revision: Union[str, None] = "54ad8c217f90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "buyers",
        sa.Column(
            "opening_balance",
            sa.Numeric(precision=18, scale=2),
            server_default="0",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("buyers", "opening_balance")
