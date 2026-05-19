import pandas as pd

def build_invoice_payloads_from_excel(df):
    invoices = []
    df = df.fillna({
        "fixedNotifiedValueOrRetailPrice": 0,
        "salesTaxWithheldAtSource": 0,
        "discount": 0,
        "furtherTax": 0,
        "fedPayable": 0
    })
    grouped = df.groupby("excelInvoiceId")
    for excel_id, rows in grouped:
        rows = rows.sort_index()
        if rows["buyerNTNCNIC"].nunique() > 1:
            raise ValueError(
                f"Inconsistent buyerNTNCNIC in invoice {excel_id}"
            )
        first = rows.iloc[0]
        items = []
        for r in rows.itertuples(index=False):
            rate_val = r.rate
            if isinstance(rate_val, (int, float)):
                rate_val = f"{int(rate_val * 100)}%"
            else:
                rate_val = str(rate_val)
            items.append({
                "hsCode": safe_str(r.hsCode).split("-")[0].strip().replace("\xa0", ""),
                "productDescription": safe_str(r.productDescription),
                "rate": format_rate(r.rate),
                "uoM": safe_str(r.uoM),
                "quantity": safe_float(r.quantity),
                "valueSalesExcludingST": safe_float(r.valueSalesExcludingST),
                "salesTaxApplicable": round(safe_float(r.salesTaxApplicable), 2),
                "totalValues": safe_float(r.totalValues),
                "fixedNotifiedValueOrRetailPrice": safe_float(r.fixedNotifiedValueOrRetailPrice),
                "salesTaxWithheldAtSource": safe_float(r.salesTaxWithheldAtSource),
                "furtherTax": safe_float(r.furtherTax),
                "extraTax": "" if pd.isna(r.extraTax) else float(r.extraTax),
                "fedPayable": safe_float(r.fedPayable),
                "discount": safe_float(r.discount),
                "saleType": safe_str(r.saleType),
                "sroScheduleNo": safe_str(r.sroScheduleNo),
                "sroItemSerialNo": safe_str(r.sroItemSerialNo),
            })
        payload = {
            "excelInvoiceId": safe_str(excel_id),
            "internalInvoiceNo": safe_str(first.internalInvoiceNo),
            "invoiceType": safe_str(first.invoiceType),
            "invoiceDate": safe_str(first.invoiceDate).split(" ")[0],
            "invoiceRefNo": safe_str(first.invoiceRefNo),
            "sellerNTNCNIC": safe_str(first.sellerNTNCNIC),
            "sellerBusinessName": safe_str(first.sellerBusinessName),
            "sellerProvince": safe_str(first.sellerProvince),
            "sellerAddress": safe_str(first.sellerAddress),
            "buyerNTNCNIC": safe_str(first.buyerNTNCNIC),
            "buyerBusinessName": safe_str(first.buyerBusinessName),
            "buyerProvince": safe_str(first.buyerProvince),
            "buyerAddress": safe_str(first.buyerAddress),
            "buyerRegistrationType": safe_str(first.buyerRegistrationType),
            "items": items
        }
        invoices.append(payload)
    return invoices

def format_rate(val):
    if val is None or pd.isna(val):
        return ""
    if isinstance(val, (int, float)):
        percent = val * 100
        return f"{percent:.2f}".rstrip("0").rstrip(".") + "%"
    return str(val).strip()

def safe_float(val, default=0.0):
    if val is None or pd.isna(val):
        return default
    return float(val)

def safe_str(val):
    if val is None or pd.isna(val):
        return ""
    return str(val).strip()