"""Add client products and invoice stock tracking.

Revision ID: c51e7b20d42a
Revises: cc2c7c7282a8
Create Date: 2026-11-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c51e7b20d42a"
down_revision: Union[str, None] = "cc2c7c7282a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("hs_code", sa.String(length=20), nullable=True),
        sa.Column("uom_code", sa.String(length=50), nullable=True),
        sa.Column("uom_description", sa.String(length=100), nullable=True),
        sa.Column("item_rate", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("stock_quantity", sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", "name", name="uq_product_name_per_client"),
    )
    op.create_index(op.f("ix_products_id"), "products", ["id"], unique=False)
    op.create_index(op.f("ix_products_client_id"), "products", ["client_id"], unique=False)
    op.add_column(
        "invoice_items",
        sa.Column("product_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_invoice_items_product_id",
        "invoice_items",
        "products",
        ["product_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "invoices",
        sa.Column(
            "stock_deducted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("invoices", "stock_deducted")
    op.drop_constraint(
        "fk_invoice_items_product_id",
        "invoice_items",
        type_="foreignkey",
    )
    op.drop_column("invoice_items", "product_id")
    op.drop_index(op.f("ix_products_client_id"), table_name="products")
    op.drop_index(op.f("ix_products_id"), table_name="products")
    op.drop_table("products")
