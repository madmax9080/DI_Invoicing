from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from ..fbr_client import FBRClient
from ..dependencies.fbr import get_fbr_client_secure
from ..schemas import BuyerValidationRequest

router = APIRouter(prefix="/dynamic", tags=["dynamic-reference"])

@router.get("/sale_type_rates")
async def get_sale_type_rates(
    date: str = Query(...),
    trans_type_id: int = Query(..., ge=1),
    origination_supplier: int = Query(..., ge=1),
    fbr: FBRClient = Depends(get_fbr_client_secure),
):
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        try:
            parsed_date = datetime.strptime(date, "%d-%b-%Y")
        except ValueError:
            raise HTTPException(422, "Invalid date format")
    fbr_date = parsed_date.strftime("%d-%b-%Y")
    data = await fbr.get_sale_type_rates(
        date=fbr_date,
        transTypeId=trans_type_id,
        originationSupplier=origination_supplier,
    )
    return data
    
@router.get("/hs_uoms")
async def get_hs_uoms(
    hs_code: str,
    annexure_id: int,
    fbr: FBRClient = Depends(get_fbr_client_secure),
):
    data = await fbr.get_hs_uoms(hs_code, annexure_id)
    return data

@router.get("/sro_schedules")
async def get_sro_schedules(
    rate_id: int = Query(...),
    date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    origination_supplier_csv: int = Query(..., ge=0),
    fbr: FBRClient = Depends(get_fbr_client_secure),
):
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        try:
            parsed_date = datetime.strptime(date, "%d-%b-%Y")
        except ValueError:
            raise HTTPException(422, "Invalid date format")
    fbr_date = parsed_date.strftime("%d-%b-%Y")
    data = await fbr.get_sro_schedules(rate_id, fbr_date, origination_supplier_csv)
    return data
        
@router.get("/sro_items")
async def get_sro_items(
    date: str = Query(...),
    sro_id: int = Query(...),
    fbr: FBRClient = Depends(get_fbr_client_secure),
):
    data = await fbr.get_sro_items(date, sro_id)
    return data

@router.post("/validate_buyer")
async def validate_buyer(
    payload: BuyerValidationRequest,
    fbr: FBRClient = Depends(get_fbr_client_secure),
):
    registration_no = payload.registration_no.strip()
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        statl_response = await fbr.get_statl(registration_no, today)
        statl_code = statl_response.get("status code") or statl_response.get("statuscode")
        if statl_code != "01":
             status_value = "inactive"
        else:
             status_value = statl_response.get("status", "").lower()
        is_active = status_value == "active"
        apply_further_tax = not is_active
        further_tax_rate = 4.0 if apply_further_tax else 0.0
        return {
            "registration_no": registration_no,
            "sales_tax_status": status_value,
            "is_active": is_active,
            "apply_further_tax": apply_further_tax,
            "further_tax_rate": further_tax_rate,
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Buyer validation failed: {str(e)}"
        )