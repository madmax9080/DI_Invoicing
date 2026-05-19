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
    hsCode: str = Field(..., min_length=4)
    productDescription: str
    rate: str = Field(..., description="e.g. '18%'")
    uoM: str = Field(..., description="UOM description")
    quantity: Union[int, Decimal]
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
    saleType: str
    sroItemSerialNo: str = ""

    class Config:
        extra = "forbid"    

class InvoiceItemOut(BaseModel):
    id: int
    hsCode: str
    productDescription: str
    rate: str
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
    sellerAddress: str
    buyerNTNCNIC: str
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
    invoiceRefNo: Optional[str]
    fbrInvoiceNo: Optional[str]
    invoiceType: str
    invoiceDate: datetime
    sellerNTNCNIC: str
    buyerNTNCNIC: Optional[str]
    buyerBusinessName: str
    buyerRegistrationType: str
    status: str
    created_at: datetime
    client_id: Optional[int] = None
    items: List[InvoiceItemOut] = []
    client: Optional["ClientOut"] = None 

    class Config:
        from_attributes = True
        
class ClientBase(BaseModel):
    name: str
    sellerNTNCNIC: str
    sellerBusinessName: str
    sellerProvince: str
    sellerAddress: str
    token: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class ClientUpdate(ClientBase):
    name: Optional[str] = None
    sellerNTNCNIC: Optional[str] = None
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