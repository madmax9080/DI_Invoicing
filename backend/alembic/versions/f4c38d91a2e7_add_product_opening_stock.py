"""Add opening stock balance to products.

Revision ID: f4c38d91a2e7
Revises: 9a7d2c4e1f63
Create Date: 2026-11-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4c38d91a2e7"
down_revision: Union[str, None] = "9a7d2c4e1f63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "opening_stock_quantity",
            sa.Numeric(precision=15, scale=4),
            nullable=True,
        ),
    )
    op.execute(
        "UPDATE products SET opening_stock_quantity = stock_quantity"
    )
    op.alter_column(
        "products",
        "opening_stock_quantity",
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("products", "opening_stock_quantity")
