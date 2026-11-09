"""Use product names as invoice descriptions.

Revision ID: 9a7d2c4e1f63
Revises: c51e7b20d42a
Create Date: 2026-11-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a7d2c4e1f63"
down_revision: Union[str, None] = "c51e7b20d42a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("products", "description")
    op.drop_column("products", "uom_code")
    op.drop_column("products", "uom_description")
    op.drop_column("products", "item_rate")


def downgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "item_rate",
            sa.Numeric(precision=18, scale=2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "products",
        sa.Column("uom_description", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("uom_code", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.alter_column("products", "item_rate", server_default=None)
    op.alter_column("products", "description", server_default=None)
