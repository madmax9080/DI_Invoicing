from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, case
from ..database import get_db
from ..models import Invoice, InvoiceItem
from ..dependencies.fbr import get_fbr_client_secure
from app.services.cache import get_cache, set_cache

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)

def get_fiscal_range(fy: str | None):
    today = date.today()
    if fy:
        start_year = int(fy.split("-")[0])
    else:
        start_year = today.year if today.month >= 7 else today.year - 1
    fiscal_start = date(start_year, 7, 1)
    fiscal_end = date(start_year + 1, 6, 30)
    fiscal_label = f"FY {start_year}-{str(start_year+1)[-2:]}"
    return fiscal_start, fiscal_end, fiscal_label

# @router.get("/kpis")
# def get_kpis(
#     fy: str | None = None,
#     db: Session = Depends(get_db),
#     fbr = Depends(get_fbr_client_secure)
# ):
#     client_id = fbr.client_id
#     today = date.today()
#     if fy:
#         start_year = int(fy.split("-")[0])
#         fiscal_start = date(start_year, 7, 1)
#         fiscal_end = date(start_year + 1, 6, 30)
#         fiscal_label = f"FY {start_year}-{str(start_year+1)[-2:]}"
#     else:
#         if today.month >= 7:
#             start_year = today.year
#         else:
#             start_year = today.year - 1

#         fiscal_start = date(start_year, 7, 1)
#         fiscal_end = date(start_year + 1, 6, 30)
#         fiscal_label = f"FY {start_year}-{str(start_year+1)[-2:]}"
#     result = db.query(
#         func.count(Invoice.id).label("total_invoices"),
#         func.coalesce(
#             func.sum(InvoiceItem.valueSalesExcludingST),
#             0
#         ).label("total_sales"),
#         func.sum(
#             case(
#                 (func.lower(Invoice.invoiceType) == "sale invoice", 1),
#                 else_=0
#             )
#         ).label("total_sale_invoices"),
#         func.sum(
#             case(
#                 (func.lower(Invoice.invoiceType) == "debit note", 1),
#                 else_=0
#             )
#         ).label("total_debit_invoices")
#     )\
#     .outerjoin(
#         InvoiceItem,
#         Invoice.id == InvoiceItem.invoice_id
#     )\
#     .filter(
#         Invoice.client_id == client_id,
#         Invoice.status == "posted",
#         Invoice.invoiceDate >= fiscal_start, 
#         Invoice.invoiceDate <= fiscal_end    
#     )\
#     .one()

#     return {
#         "fiscal_year": fiscal_label,
#         "total_invoices": int(result.total_invoices or 0),
#         "total_sales": float(result.total_sales or 0),
#         "total_sale_invoices": int(result.total_sale_invoices or 0),
#         "total_debit_invoices": int(result.total_debit_invoices or 0),
#     }

@router.get("/kpis")
def get_kpis(
    fy: str | None = None,
    db: Session = Depends(get_db),
    fbr = Depends(get_fbr_client_secure)
):
    client_id = fbr.client_id
    cache_key = f"dashboard:{client_id}:kpis:{fy or 'current'}"
    cached = get_cache(cache_key)
    if cached:
        return cached
    fiscal_start, fiscal_end, fiscal_label = get_fiscal_range(fy)
    result = db.query(
        func.count(func.distinct(Invoice.id)).label("total_invoices"),
        func.coalesce(
            func.sum(InvoiceItem.valueSalesExcludingST),
            0
        ).label("total_sales"),
        func.sum(
            case(
                (func.lower(Invoice.invoiceType) == "sale invoice", 1),
                else_=0
            )
        ).label("total_sale_invoices"),
        func.sum(
            case(
                (func.lower(Invoice.invoiceType) == "debit note", 1),
                else_=0
            )
        ).label("total_debit_invoices")
    ).outerjoin(
        InvoiceItem,
        Invoice.id == InvoiceItem.invoice_id
    ).filter(
        Invoice.client_id == client_id,
        Invoice.status == "posted",
        Invoice.invoiceDate >= fiscal_start,
        Invoice.invoiceDate <= fiscal_end
    ).one()
    response = {
        "fiscal_year": fiscal_label,
        "total_invoices": int(result.total_invoices or 0),
        "total_sales": float(result.total_sales or 0),
        "total_sale_invoices": int(result.total_sale_invoices or 0),
        "total_debit_invoices": int(result.total_debit_invoices or 0),
    }
    set_cache(cache_key, response)
    return response

# @router.get("/monthly-sales")
# def get_monthly_sales(
#     fy: str | None = None,
#     db: Session = Depends(get_db),
#     fbr = Depends(get_fbr_client_secure)
# ):
#     client_id = fbr.client_id
#     today = date.today()
#     if fy:
#         start_year = int(fy.split("-")[0])
#         fiscal_start = date(start_year, 7, 1)
#         fiscal_end = date(start_year + 1, 6, 30)
#         fiscal_label = f"FY {start_year}-{str(start_year+1)[-2:]}"
#     else:
#         if today.month >= 7:
#             start_year = today.year
#         else:
#             start_year = today.year - 1
#         fiscal_start = date(start_year, 7, 1)
#         fiscal_end = date(start_year + 1, 6, 30)
#         fiscal_label = f"FY {start_year}-{str(start_year+1)[-2:]}"
#     results = (
#         db.query(
#             extract("year", Invoice.invoiceDate).label("year"),
#             extract("month", Invoice.invoiceDate).label("month"),
#             func.coalesce(
#                 func.sum(InvoiceItem.valueSalesExcludingST),
#                 0
#             ).label("total_sales")
#         )
#         .join(
#             InvoiceItem,
#             Invoice.id == InvoiceItem.invoice_id
#         )
#         .filter(
#             Invoice.client_id == client_id,
#             Invoice.status == "posted",
#             Invoice.invoiceDate >= fiscal_start,
#             Invoice.invoiceDate <= fiscal_end
#         )
#         .group_by("year", "month")
#         .order_by("year", "month")
#         .all()
#     )
#     return {
#         "fiscal_year": fiscal_label,
#         "data": [
#             {
#                 "year": int(r.year),
#                 "month": int(r.month),
#                 "total_sales": float(r.total_sales)
#             }
#             for r in results
#         ]
#     }

@router.get("/monthly-sales")
def get_monthly_sales(
    fy: str | None = None,
    db: Session = Depends(get_db),
    fbr = Depends(get_fbr_client_secure)
):
    client_id = fbr.client_id
    cache_key = f"dashboard:{client_id}:monthly:{fy or 'current'}"
    cached = get_cache(cache_key)
    if cached:
        return cached
    fiscal_start, fiscal_end, fiscal_label = get_fiscal_range(fy)
    year_col = extract("year", Invoice.invoiceDate)
    month_col = extract("month", Invoice.invoiceDate)
    results = (
        db.query(
            year_col.label("year"),
            month_col.label("month"),
            func.coalesce(
                func.sum(InvoiceItem.valueSalesExcludingST),
                0
            ).label("total_sales")
        )
        .outerjoin(  # safer than join
            InvoiceItem,
            Invoice.id == InvoiceItem.invoice_id
        )
        .filter(
            Invoice.client_id == client_id,
            Invoice.status == "posted",
            Invoice.invoiceDate >= fiscal_start,
            Invoice.invoiceDate <= fiscal_end
        )
        .group_by(year_col, month_col)
        .order_by(year_col, month_col)
        .all()
    )
    response = {
        "fiscal_year": fiscal_label,
        "data": [
            {
                "year": int(r.year),
                "month": int(r.month),
                "total_sales": float(r.total_sales)
            }
            for r in results
        ]
    }
    set_cache(cache_key, response)
    return response

# @router.get("/quarterly-sales")
# def get_quarterly_sales(
#     fy: str | None = None,
#     db: Session = Depends(get_db),
#     fbr = Depends(get_fbr_client_secure)
# ):
#     client_id = fbr.client_id
#     today = date.today()
#     if fy:
#         start_year = int(fy.split("-")[0])
#         fiscal_start = date(start_year, 7, 1)
#         fiscal_end = date(start_year + 1, 6, 30)
#         fiscal_label = f"FY {start_year}-{str(start_year+1)[-2:]}"
#     else:
#         if today.month >= 7:
#             fiscal_start = date(today.year, 7, 1)
#             fiscal_end = date(today.year + 1, 6, 30)
#             fiscal_label = f"FY {today.year}-{str(today.year+1)[-2:]}"
#         else:
#             fiscal_start = date(today.year - 1, 7, 1)
#             fiscal_end = date(today.year, 6, 30)
#             fiscal_label = f"FY {today.year-1}-{str(today.year)[-2:]}"
#     q1_start = fiscal_start
#     q2_start = date(fiscal_start.year, 10, 1)
#     q3_start = date(fiscal_start.year + 1, 1, 1)
#     q4_start = date(fiscal_start.year + 1, 4, 1)
#     quarters = [
#         ("Q1", q1_start, q2_start - timedelta(days=1)),
#         ("Q2", q2_start, q3_start - timedelta(days=1)),
#         ("Q3", q3_start, q4_start - timedelta(days=1)),
#         ("Q4", q4_start, fiscal_end),
#     ]
#     results = []
#     for label,start, end in quarters:
#         total = (
#             db.query(
#                 func.coalesce(
#                     func.sum(InvoiceItem.valueSalesExcludingST),
#                     0
#                 )
#             )
#             .join(Invoice)
#             .filter(
#                 Invoice.client_id == client_id,
#                 Invoice.status == "posted",
#                 Invoice.invoiceDate >= start,
#                 Invoice.invoiceDate <= end
#             )
#             .scalar()
#         )
#         results.append(float(total))
#     return {
#         "fiscal_year": fiscal_label,
#         "labels": ["Q1", "Q2", "Q3", "Q4"],
#         "series": results
#     }

@router.get("/quarterly-sales")
def get_quarterly_sales(
    fy: str | None = None,
    db: Session = Depends(get_db),
    fbr = Depends(get_fbr_client_secure)
):
    client_id = fbr.client_id
    cache_key = f"dashboard:{client_id}:quarterly:{fy or 'current'}"
    cached = get_cache(cache_key)
    if cached:
        return cached
    fiscal_start, fiscal_end, fiscal_label = get_fiscal_range(fy)
    month_col = extract("month", Invoice.invoiceDate)
    quarter_case = case(
        (month_col.in_([7, 8, 9]), "Q1"),
        (month_col.in_([10, 11, 12]), "Q2"),
        (month_col.in_([1, 2, 3]), "Q3"),
        else_="Q4"
    )
    results = (
        db.query(
            quarter_case.label("quarter"),
            func.coalesce(
                func.sum(InvoiceItem.valueSalesExcludingST),
                0
            ).label("total_sales")
        )
        .outerjoin(  # FIXED
            InvoiceItem,
            Invoice.id == InvoiceItem.invoice_id
        )
        .filter(
            Invoice.client_id == client_id,
            Invoice.status == "posted",
            Invoice.invoiceDate >= fiscal_start,
            Invoice.invoiceDate <= fiscal_end
        )
        .group_by(quarter_case)  # FIXED (not string)
        .all()
    )
    data_map = {r.quarter: float(r.total_sales) for r in results}
    response = {
        "fiscal_year": fiscal_label,
        "labels": ["Q1", "Q2", "Q3", "Q4"],
        "series": [
            data_map.get("Q1", 0),
            data_map.get("Q2", 0),
            data_map.get("Q3", 0),
            data_map.get("Q4", 0),
        ]
    }
    set_cache(cache_key, response)
    return response

# @router.get("/invoice-count-monthly")
# def invoice_count_monthly(
#     fy: str | None = None,
#     db: Session = Depends(get_db),
#     fbr = Depends(get_fbr_client_secure)
# ):
#     client_id = fbr.client_id
#     today = date.today()
#     if fy:
#         start_year = int(fy.split("-")[0])
#     else:
#         start_year = today.year if today.month >= 7 else today.year - 1
#     fiscal_start = date(start_year, 7, 1)
#     fiscal_end = date(start_year + 1, 6, 30)
#     fiscal_label = f"FY {start_year}-{str(start_year+1)[-2:]}"
#     results = (
#         db.query(
#             extract("year", Invoice.invoiceDate).label("year"),
#             extract("month", Invoice.invoiceDate).label("month"),
#             func.count(Invoice.id).label("count")
#         )
#         .filter(
#             Invoice.client_id == client_id,
#             Invoice.status == "posted",
#             Invoice.invoiceDate >= fiscal_start,
#             Invoice.invoiceDate <= fiscal_end
#         )
#         .group_by("year", "month")
#         .order_by("year", "month")
#         .all()
#     )
#     return {
#         "fiscal_year": fiscal_label,
#         "data": [
#             {
#                 "year": int(r.year),
#                 "month": int(r.month),
#                 "count": int(r.count)
#             }
#             for r in results
#         ]
#     }

@router.get("/invoice-count-monthly")
def invoice_count_monthly(
    fy: str | None = None,
    db: Session = Depends(get_db),
    fbr = Depends(get_fbr_client_secure)
):
    client_id = fbr.client_id
    cache_key = f"dashboard:{client_id}:invoice_count:{fy or 'current'}"
    cached = get_cache(cache_key)
    if cached:
        return cached
    fiscal_start, fiscal_end, fiscal_label = get_fiscal_range(fy)
    year_col = extract("year", Invoice.invoiceDate)
    month_col = extract("month", Invoice.invoiceDate)
    results = (
        db.query(
            year_col.label("year"),
            month_col.label("month"),
            func.count(Invoice.id).label("count")
        )
        .filter(
            Invoice.client_id == client_id,
            Invoice.status == "posted",
            Invoice.invoiceDate >= fiscal_start,
            Invoice.invoiceDate <= fiscal_end
        )
        .group_by(year_col, month_col)
        .order_by(year_col, month_col)
        .all()
    )
    response = {
        "fiscal_year": fiscal_label,
        "data": [
            {
                "year": int(r.year),
                "month": int(r.month),
                "count": int(r.count)
            }
            for r in results
        ]
    }
    set_cache(cache_key, response)
    return response