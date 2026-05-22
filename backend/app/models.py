from sqlalchemy import TIMESTAMP, Column, Integer, String, DateTime, JSON, ForeignKey, Numeric, Text, func
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
    sellerBusinessName = Column(String(100), nullable=False)
    sellerProvince = Column(String(50), nullable=False)
    sellerAddress = Column(String(200), nullable=False)
    buyerNTNCNIC = Column(String(20), nullable=False) 
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
    hsCode = Column(String(20), nullable=False) 
    productDescription = Column(Text, nullable=False)
    uom = Column(String(50), nullable=False)
    quantity = Column(Numeric(15, 4), nullable=False)
    rate = Column(String(10), nullable=False)
    valueSalesExcludingST = Column(Numeric(18, 2), nullable=False) 
    salesTaxApplicable = Column(Numeric(18, 2), nullable=False) 
    totalValues = Column(Numeric(18, 2), nullable=False, default=0.0)
    fixedNotifiedValueOrRetailPrice = Column(Numeric(18, 2), nullable=True, default=0.0)
    salesTaxWithheldAtSource = Column(Numeric(18, 2), nullable=True, default=0.0)
    furtherTax = Column(Numeric(18, 2), nullable=True, default=0.0)
    extraTax = Column(Numeric(18, 2), nullable=True)
    fedPayable = Column(Numeric(18, 2), nullable=True, default=0.0)
    discount = Column(Numeric(18, 2), nullable=True, default=0.0)
    sroScheduleNo = Column(String(50), nullable=True)
    sroItemSerialNo = Column(String(50), nullable=True)
    saleType = Column(String(100), nullable=False) 
    invoice = relationship("Invoice", back_populates="items")
    
class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    sellerNTNCNIC = Column(String(20), nullable=False)
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
    ntn_cnic = Column(String, index=True, nullable=False)
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