from io import BytesIO
from fastapi import HTTPException
import pandas as pd

def parse_excel(contents: bytes):
    df = pd.read_excel(
        BytesIO(contents), 
        dtype={
            "hsCode": str, 
            "internalInvoiceNo": str, 
            "sellerNTNCNIC": str,
            "sellerSTRN": str,
            "buyerNTNCNIC": str,
            "buyerSTRN": str,})
    required_columns = [
        "excelInvoiceId",
        "internalInvoiceNo",
        "invoiceType",
        "invoiceDate",
        "invoiceRefNo",
        "sellerNTNCNIC",
        "sellerBusinessName",
        "sellerProvince",
        "sellerAddress",
        "buyerNTNCNIC",
        "buyerBusinessName",
        "buyerProvince",
        "buyerAddress",
        "buyerRegistrationType",
        "hsCode",
        "productDescription",
        "rate",
        "itemRate",
        "uoM",
        "quantity",
        "valueSalesExcludingST",
        "salesTaxApplicable",
        "totalValues",
        "fixedNotifiedValueOrRetailPrice",
        "salesTaxWithheldAtSource",
        "furtherTax",
        "extraTax",
        "fedPayable",
        "discount",
        "tax236HRate",
        "tax236H",
        "saleType",
        "sroScheduleNo",
        "sroItemSerialNo",
    ]
    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing columns: {missing}"
        )
    if df["internalInvoiceNo"].isna().any() or (df["internalInvoiceNo"].astype(str).str.strip() == "").any():
        raise HTTPException(
            status_code=400,
            detail="internalInvoiceNo cannot be empty"
        )
    return df