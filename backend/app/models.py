from sqlalchemy import TIMESTAMP, Boolean, Column, Date, Integer, String, DateTime, JSON, ForeignKey, Numeric, Text, func
from sqlalchemy.orm import relationship
from .database import Base
from sqlalchemy import UniqueConstraint

class ReferenceCache(Base):
    __tablename__ = "reference_cache"
    endpoint = Column(String(100), primary_key=True)
    last_updated = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    data_json = Column(JSON, nullable=False)
    version = Column(String(20), nullable=True)

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    invoiceRefNo = Column(String(100), index=True, nullable=True)
    internal_invoice_no = Column(String, nullable=False)
    fbrInvoiceNo = Column(String(100), index=True, nullable=True) 
    invoiceType = Column(String(50), nullable=False) 
    invoiceDate = Column(DateTime(timezone=True), nullable=False) 
    sellerNTNCNIC = Column(String(20), nullable=False)
    sellerSTRN = Column(String(50), nullable=True)
    sellerBusinessName = Column(String(100), nullable=False)
    sellerProvince = Column(String(50), nullable=False)
    sellerAddress = Column(String(200), nullable=False)
    buyerNTNCNIC = Column(String(20), nullable=False) 
    buyerSTRN = Column(String(50), nullable=True)
    buyerBusinessName = Column(String(100), nullable=False)
    buyerProvince = Column(String(50), nullable=False)
    buyerAddress = Column(String(200), nullable=False)
    buyerRegistrationType = Column(String(20), nullable=False) 
    scenarioId = Column(String(10), nullable=True)
    buyer_id = Column(Integer, ForeignKey("buyers.id"), nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    status = Column(String(30), default="pending")
    request_payload = Column(JSON, nullable=False)
    response_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    printed_count = Column(Integer, default=0)
    last_printed_at = Column(DateTime(timezone=True), nullable=True)
    stock_deducted = Column(Boolean, nullable=False, default=False, server_default="false")
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "internal_invoice_no",
            name="uq_client_invoice_no"
        ),
    )
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    client = relationship("Client", back_populates="invoices")
    buyer = relationship("Buyer", back_populates="invoices")

class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    hsCode = Column(String(20), nullable=False) 
    productDescription = Column(Text, nullable=False)
    uom = Column(String(50), nullable=False)
    quantity = Column(Numeric(15, 4), nullable=False)
    rate = Column(String(10), nullable=False)
    itemRate = Column(Numeric(18, 2), nullable=False, default=0)
    valueSalesExcludingST = Column(Numeric(18, 2), nullable=False) 
    salesTaxApplicable = Column(Numeric(18, 2), nullable=False) 
    totalValues = Column(Numeric(18, 2), nullable=False, default=0.0)
    fixedNotifiedValueOrRetailPrice = Column(Numeric(18, 2), nullable=True, default=0.0)
    salesTaxWithheldAtSource = Column(Numeric(18, 2), nullable=True, default=0.0)
    furtherTax = Column(Numeric(18, 2), nullable=True, default=0.0)
    extraTax = Column(Numeric(18, 2), nullable=True)
    fedPayable = Column(Numeric(18, 2), nullable=True, default=0.0)
    discount = Column(Numeric(18, 2), nullable=True, default=0.0)
    tax236HRate = Column(Numeric(5, 2), nullable=True, default=0)
    tax236H = Column(Numeric(18, 2), nullable=True, default=0)
    sroScheduleNo = Column(String(50), nullable=True)
    sroItemSerialNo = Column(String(50), nullable=True)
    saleType = Column(String(100), nullable=False) 
    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product")

class BuyerReceipt(Base):
    __tablename__ = "buyer_receipts"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    buyer_id = Column(Integer, ForeignKey("buyers.id"), nullable=False, index=True)
    received_date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(18, 2), nullable=False)
    payment_method = Column(String(50), nullable=True)
    reference_number = Column(String(150), nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    allocations = relationship(
        "BuyerReceiptAllocation",
        back_populates="receipt",
        cascade="all, delete-orphan",
    )

class BuyerReceiptAllocation(Base):
    __tablename__ = "buyer_receipt_allocations"
    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(
        Integer,
        ForeignKey("buyer_receipts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_id = Column(
        Integer,
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    amount = Column(Numeric(18, 2), nullable=False)
    receipt = relationship("BuyerReceipt", back_populates="allocations")
    invoice = relationship("Invoice")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    hs_code = Column(String(20), nullable=True)
    product_type = Column(String(30), nullable=False, default="finished_good", server_default="finished_good")
    uom = Column(String(30), nullable=False, default="unit", server_default="unit")
    opening_stock_quantity = Column(Numeric(15, 4), nullable=False, default=0)
    stock_quantity = Column(Numeric(15, 4), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    client = relationship("Client")
    __table_args__ = (
        UniqueConstraint("client_id", "name", name="uq_product_name_per_client"),
    )


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    movement_type = Column(String(40), nullable=False)
    quantity = Column(Numeric(15, 4), nullable=False)
    movement_date = Column(Date, nullable=False, server_default=func.current_date(), index=True)
    reference_type = Column(String(40), nullable=True)
    reference_id = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PurchaseReceipt(Base):
    __tablename__ = "purchase_receipts"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_name = Column(String(150), nullable=False)
    supplier_reference = Column(String(100), nullable=True)
    received_date = Column(Date, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    items = relationship("PurchaseReceiptItem", cascade="all, delete-orphan")


class PurchaseReceiptItem(Base):
    __tablename__ = "purchase_receipt_items"
    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("purchase_receipts.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Numeric(15, 4), nullable=False)
    unit_cost = Column(Numeric(18, 4), nullable=False, default=0)


class ProductBOM(Base):
    __tablename__ = "product_boms"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    finished_product_id = Column(Integer, ForeignKey("products.id"), nullable=False, unique=True, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    components = relationship("ProductBOMComponent", cascade="all, delete-orphan")


class ProductBOMComponent(Base):
    __tablename__ = "product_bom_components"
    id = Column(Integer, primary_key=True, index=True)
    bom_id = Column(Integer, ForeignKey("product_boms.id", ondelete="CASCADE"), nullable=False, index=True)
    component_product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity_per_unit = Column(Numeric(15, 4), nullable=False)
    __table_args__ = (
        UniqueConstraint("bom_id", "component_product_id", name="uq_bom_component"),
    )


class ProductionOrder(Base):
    __tablename__ = "production_orders"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    finished_product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity_produced = Column(Numeric(15, 4), nullable=False)
    produced_date = Column(Date, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    components = relationship("ProductionOrderComponent", cascade="all, delete-orphan")


class ProductionOrderComponent(Base):
    __tablename__ = "production_order_components"
    id = Column(Integer, primary_key=True, index=True)
    production_order_id = Column(Integer, ForeignKey("production_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    component_product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity_consumed = Column(Numeric(15, 4), nullable=False)
    
class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    sellerNTNCNIC = Column(String(20), nullable=False)
    sellerSTRN = Column(String(30), nullable=True)
    sellerBusinessName = Column(String(100), nullable=False)
    sellerProvince = Column(String(50), nullable=False)
    sellerAddress = Column(String(200), nullable=False)
    token = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    user_id = Column(Integer, ForeignKey("users.id"))
    invoices = relationship("Invoice", back_populates="client")
    buyers = relationship(
        "Buyer",
        back_populates="client",
        cascade="all, delete-orphan"
    )

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

class Buyer(Base):
    __tablename__ = "buyers"
    id = Column(Integer, primary_key=True, index=True)
    opening_balance = Column(
        Numeric(18, 2),
        nullable=False,
        default=0,
        server_default="0",
    )
    ntn_cnic = Column(String, index=True, nullable=False)
    strn = Column(String(30), nullable=True)
    name = Column(String)
    province = Column(String)
    address = Column(String)
    buyer_registration_type = Column(
        String(50),
        nullable=True
    )
    client = relationship(
        "Client",
        back_populates="buyers"
    )
    invoices = relationship(
        "Invoice",
        back_populates="buyer"
    )
    client_id = Column(
        Integer,
        ForeignKey("clients.id"),
        index=True,
        nullable=False
    )
    __table_args__ = (
        UniqueConstraint("ntn_cnic", "client_id", name="unique_buyer_per_client"),
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())