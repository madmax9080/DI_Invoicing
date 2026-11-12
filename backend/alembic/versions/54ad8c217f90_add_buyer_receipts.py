"""Add buyer receipts and invoice allocations.

Revision ID: 54ad8c217f90
Revises: f4c38d91a2e7
Create Date: 2026-11-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "54ad8c217f90"
down_revision: Union[str, None] = "f4c38d91a2e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "buyer_receipts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("received_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("payment_method", sa.String(length=50), nullable=True),
        sa.Column("reference_number", sa.String(length=150), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["buyer_id"], ["buyers.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_buyer_receipts_client_id", "buyer_receipts", ["client_id"])
    op.create_index("ix_buyer_receipts_buyer_id", "buyer_receipts", ["buyer_id"])
    op.create_index("ix_buyer_receipts_received_date", "buyer_receipts", ["received_date"])
    op.create_index("ix_buyer_receipts_id", "buyer_receipts", ["id"])

    op.create_table(
        "buyer_receipt_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("receipt_id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["receipt_id"],
            ["buyer_receipts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_buyer_receipt_allocations_id",
        "buyer_receipt_allocations",
        ["id"],
    )
    op.create_index(
        "ix_buyer_receipt_allocations_receipt_id",
        "buyer_receipt_allocations",
        ["receipt_id"],
    )
    op.create_index(
        "ix_buyer_receipt_allocations_invoice_id",
        "buyer_receipt_allocations",
        ["invoice_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_buyer_receipt_allocations_invoice_id",
        table_name="buyer_receipt_allocations",
    )
    op.drop_index(
        "ix_buyer_receipt_allocations_receipt_id",
        table_name="buyer_receipt_allocations",
    )
    op.drop_index(
        "ix_buyer_receipt_allocations_id",
        table_name="buyer_receipt_allocations",
    )
    op.drop_table("buyer_receipt_allocations")
    op.drop_index("ix_buyer_receipts_id", table_name="buyer_receipts")
    op.drop_index("ix_buyer_receipts_received_date", table_name="buyer_receipts")
    op.drop_index("ix_buyer_receipts_buyer_id", table_name="buyer_receipts")
    op.drop_index("ix_buyer_receipts_client_id", table_name="buyer_receipts")
    op.drop_table("buyer_receipts")
