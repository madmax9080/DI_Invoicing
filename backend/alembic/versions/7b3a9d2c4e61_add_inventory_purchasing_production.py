"""Add inventory purchasing and production records.

Revision ID: 7b3a9d2c4e61
Revises: 54ad8c217f90
Create Date: 2026-11-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7b3a9d2c4e61"
down_revision: Union[str, None] = "a8210c9d4f67"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "product_type",
            sa.String(length=30),
            server_default="finished_good",
            nullable=False,
        ),
    )
    op.add_column(
        "products",
        sa.Column(
            "uom",
            sa.String(length=30),
            server_default="unit",
            nullable=False,
        ),
    )

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("movement_type", sa.String(length=40), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column(
            "movement_date",
            sa.Date(),
            server_default=sa.text("CURRENT_DATE"),
            nullable=False,
        ),
        sa.Column("reference_type", sa.String(length=40), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_movements_id", "inventory_movements", ["id"])
    op.create_index(
        "ix_inventory_movements_client_id",
        "inventory_movements",
        ["client_id"],
    )
    op.create_index(
        "ix_inventory_movements_product_id",
        "inventory_movements",
        ["product_id"],
    )
    op.create_index(
        "ix_inventory_movements_movement_date",
        "inventory_movements",
        ["movement_date"],
    )
    op.execute(
        """
        INSERT INTO inventory_movements
            (client_id, product_id, movement_type, quantity, movement_date, notes)
        SELECT client_id, id, 'opening_balance', stock_quantity, CURRENT_DATE,
               'Balance carried forward when inventory tracking was enabled'
        FROM products
        WHERE stock_quantity <> 0
        """
    )

    op.create_table(
        "purchase_receipts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("supplier_name", sa.String(length=150), nullable=False),
        sa.Column("supplier_reference", sa.String(length=100), nullable=True),
        sa.Column("received_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_receipts_id", "purchase_receipts", ["id"])
    op.create_index(
        "ix_purchase_receipts_client_id",
        "purchase_receipts",
        ["client_id"],
    )
    op.create_index(
        "ix_purchase_receipts_received_date",
        "purchase_receipts",
        ["received_date"],
    )

    op.create_table(
        "purchase_receipt_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("receipt_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column(
            "unit_cost",
            sa.Numeric(precision=18, scale=4),
            server_default="0",
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["purchase_receipts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_purchase_receipt_items_id",
        "purchase_receipt_items",
        ["id"],
    )
    op.create_index(
        "ix_purchase_receipt_items_receipt_id",
        "purchase_receipt_items",
        ["receipt_id"],
    )
    op.create_index(
        "ix_purchase_receipt_items_product_id",
        "purchase_receipt_items",
        ["product_id"],
    )

    op.create_table(
        "product_boms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("finished_product_id", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["finished_product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("finished_product_id"),
    )
    op.create_index("ix_product_boms_id", "product_boms", ["id"])
    op.create_index("ix_product_boms_client_id", "product_boms", ["client_id"])
    op.create_index(
        "ix_product_boms_finished_product_id",
        "product_boms",
        ["finished_product_id"],
    )

    op.create_table(
        "product_bom_components",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bom_id", sa.Integer(), nullable=False),
        sa.Column("component_product_id", sa.Integer(), nullable=False),
        sa.Column(
            "quantity_per_unit",
            sa.Numeric(precision=15, scale=4),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["bom_id"],
            ["product_boms.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["component_product_id"],
            ["products.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bom_id", "component_product_id", name="uq_bom_component"),
    )
    op.create_index(
        "ix_product_bom_components_id",
        "product_bom_components",
        ["id"],
    )
    op.create_index(
        "ix_product_bom_components_bom_id",
        "product_bom_components",
        ["bom_id"],
    )
    op.create_index(
        "ix_product_bom_components_component_product_id",
        "product_bom_components",
        ["component_product_id"],
    )

    op.create_table(
        "production_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("finished_product_id", sa.Integer(), nullable=False),
        sa.Column(
            "quantity_produced",
            sa.Numeric(precision=15, scale=4),
            nullable=False,
        ),
        sa.Column("produced_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["finished_product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_production_orders_id", "production_orders", ["id"])
    op.create_index(
        "ix_production_orders_client_id",
        "production_orders",
        ["client_id"],
    )
    op.create_index(
        "ix_production_orders_finished_product_id",
        "production_orders",
        ["finished_product_id"],
    )
    op.create_index(
        "ix_production_orders_produced_date",
        "production_orders",
        ["produced_date"],
    )

    op.create_table(
        "production_order_components",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("production_order_id", sa.Integer(), nullable=False),
        sa.Column("component_product_id", sa.Integer(), nullable=False),
        sa.Column(
            "quantity_consumed",
            sa.Numeric(precision=15, scale=4),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["component_product_id"],
            ["products.id"],
        ),
        sa.ForeignKeyConstraint(
            ["production_order_id"],
            ["production_orders.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_production_order_components_id",
        "production_order_components",
        ["id"],
    )
    op.create_index(
        "ix_production_order_components_production_order_id",
        "production_order_components",
        ["production_order_id"],
    )
    op.create_index(
        "ix_production_order_components_component_product_id",
        "production_order_components",
        ["component_product_id"],
    )


def downgrade() -> None:
    op.drop_table("production_order_components")
    op.drop_table("production_orders")
    op.drop_table("product_bom_components")
    op.drop_table("product_boms")
    op.drop_table("purchase_receipt_items")
    op.drop_table("purchase_receipts")
    op.drop_table("inventory_movements")
    op.drop_column("products", "uom")
    op.drop_column("products", "product_type")
