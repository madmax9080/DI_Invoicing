from pydantic import BaseModel, Field, model_validator
from datetime import date, datetime
from typing import List, Optional, Dict, Any, Union
from decimal import Decimal
from enum import Enum

class InvoiceTypeEnum(str, Enum):
    SALE_INVOICE = "Sale Invoice"
    DEBIT_NOTE = "Debit Note"

class BuyerRegistrationTypeEnum(str, Enum):
    REGISTERED = "Registered"
    UNREGISTERED = "Unregistered"

class BuyerValidationRequest(BaseModel):
    registration_no: str

class BuyerBase(BaseModel):
    ntn_cnic: str
    strn: Optional[str] = None
    name: str
    province: Optional[str] = None
    address: Optional[str] = None
    buyer_registration_type: Optional[
        BuyerRegistrationTypeEnum
    ] = None

class BuyerCreate(BuyerBase):
    pass

class BuyerUpdate(BaseModel):
    ntn_cnic: Optional[str] = None
    strn: Optional[str] = None
    name: Optional[str] = None
    province: Optional[str] = None
    address: Optional[str] = None
    buyer_registration_type: Optional[
        BuyerRegistrationTypeEnum
    ] = None

class BuyerResponse(BuyerBase):
    id: int
    client_id: int
    created_at: Optional[datetime]
    class Config:
        from_attributes = True

class BuyerPaginationResponse(BaseModel):
    items: List[BuyerResponse]
    total: int
    skip: int
    limit: int

class ReferenceCacheBase(BaseModel):
    endpoint: str
    data_json: Dict[str, Any]

class LoginSchema(BaseModel):
    email: str
    password: str

class RegisterSchema(BaseModel):
    email: str
    password: str = Field(min_length=6, max_length=72)

class Token(BaseModel):
    access_token: str
    token_type: str

class ReferenceCacheOut(ReferenceCacheBase):
    last_updated: datetime

class ChangePasswordSchema(BaseModel):
    old_password: str
    new_password: str

class InvoiceItem(BaseModel):
    productId: Optional[int] = Field(default=None, ge=1)
    hsCode: str = Field(..., min_length=4)
    productDescription: str
    rate: str = Field(..., description="e.g. '18%'")
    itemRate: Decimal = Field(..., ge=0, description="Invoice item unit rate")
    uoM: str = Field(..., description="UOM description")
    quantity: Union[int, Decimal] = Field(..., gt=0)
    totalValues: Union[int, Decimal]
    valueSalesExcludingST: Union[int, Decimal]
    fixedNotifiedValueOrRetailPrice: Union[int, Decimal]
    salesTaxApplicable: Union[int, Decimal]
    salesTaxWithheldAtSource: Union[int, Decimal]
    extraTax: Union[str, Decimal] 
    furtherTax: Union[int, Decimal]
    sroScheduleNo: str = ""
    fedPayable: Union[int, Decimal]
    discount: Union[int, Decimal]
    tax236HRate: Union[int, Decimal]
    tax236H: Union[int, Decimal]
    saleType: str
    sroItemSerialNo: str = ""

    class Config:
        extra = "forbid"    

class InvoiceItemOut(BaseModel):
    id: int
    product_id: Optional[int] = None
    hsCode: str
    productDescription: str
    rate: str
    itemRate: Decimal
    uoM: str = Field(alias="uom")
    quantity: Decimal
    totalValues: Decimal
    valueSalesExcludingST: Decimal
    fixedNotifiedValueOrRetailPrice: Decimal
    salesTaxApplicable: Decimal
    salesTaxWithheldAtSource: Decimal
    extraTax: Optional[Decimal]
    furtherTax: Decimal
    sroScheduleNo: Optional[str]
    fedPayable: Decimal
    discount: Decimal
    tax236HRate: Optional[Decimal] = Decimal("0")
    tax236H: Optional[Decimal] = Decimal("0")
    saleType: str
    sroItemSerialNo: Optional[str]

    class Config:
        from_attributes = True
        populate_by_name = True

class InvoiceCreate(BaseModel):
    internalInvoiceNo: str = Field(..., min_length=1)
    invoiceType: InvoiceTypeEnum
    invoiceDate: date
    sellerBusinessName: str
    sellerProvince: str
    sellerNTNCNIC: str
    sellerSTRN: Optional[str] = None
    sellerAddress: str
    buyerNTNCNIC: str
    buyerSTRN: Optional[str] = None
    buyerBusinessName: str
    buyerProvince: str
    buyerAddress: str
    invoiceRefNo: str = ""
    scenarioId: str = ""
    buyerRegistrationType: BuyerRegistrationTypeEnum
    items: List[InvoiceItem] = Field(..., min_items=1)
    @model_validator(mode="after")
    def validate_fbr_rules(self):
        if self.invoiceType == InvoiceTypeEnum.DEBIT_NOTE:
            if not self.invoiceRefNo:
                raise ValueError(
                    "invoiceRefNo is required when invoiceType is 'Debit Note'"
                )
        if self.buyerRegistrationType == BuyerRegistrationTypeEnum.REGISTERED:
            if not self.buyerNTNCNIC:
                raise ValueError(
                    "buyerNTNCNIC is required when buyerRegistrationType is 'Registered'"
                )
        return self

    class Config:
        extra = "forbid"

class InvoiceOut(BaseModel):
    id: int
    internalInvoiceNo: str = Field(alias="internal_invoice_no")
    invoiceRefNo: Optional[str]
    fbrInvoiceNo: Optional[str]
    invoiceType: str
    invoiceDate: datetime
    sellerNTNCNIC: str
    sellerSTRN: Optional[str] = None
    sellerBusinessName: str
    sellerProvince: str
    sellerAddress: str
    buyerNTNCNIC: Optional[str]
    buyerSTRN: Optional[str] = None
    buyerBusinessName: str
    buyerProvince: str
    buyerAddress: str
    buyerRegistrationType: str
    scenarioId: Optional[str]
    status: str
    created_at: datetime
    client_id: Optional[int] = None
    items: List[InvoiceItemOut] = []
    client: Optional["ClientOut"] = None 

    class Config:
        from_attributes = True
        populate_by_name = True
        
class ClientBase(BaseModel):
    name: str
    sellerNTNCNIC: str
    sellerSTRN: Optional[str] = None
    sellerBusinessName: str
    sellerProvince: str
    sellerAddress: str
    token: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class ClientUpdate(ClientBase):
    name: Optional[str] = None
    sellerNTNCNIC: Optional[str] = None
    sellerSTRN: Optional[str] = None
    sellerBusinessName: Optional[str] = None
    sellerProvince: Optional[str] = None
    sellerAddress: Optional[str] = None
    token: Optional[str] = None

class ClientOut(ClientBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: str = Field(..., min_length=1)
    hs_code: Optional[str] = Field(default=None, max_length=20)
    uom_code: Optional[str] = Field(default=None, max_length=50)
    uom_description: Optional[str] = Field(default=None, max_length=100)
    item_rate: Decimal = Field(default=Decimal("0"), ge=0)
    stock_quantity: Decimal = Field(default=Decimal("0"), ge=0)

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, min_length=1)
    hs_code: Optional[str] = Field(default=None, max_length=20)
    uom_code: Optional[str] = Field(default=None, max_length=50)
    uom_description: Optional[str] = Field(default=None, max_length=100)
    item_rate: Optional[Decimal] = Field(default=None, ge=0)
    stock_quantity: Optional[Decimal] = Field(default=None, ge=0)

class ProductOut(ProductCreate):
    id: int
    client_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True