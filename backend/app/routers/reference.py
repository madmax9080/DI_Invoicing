# from datetime import datetime, timezone
# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from ..dependencies.fbr import get_fbr_client_secure
# from ..database import get_db
# from .. import crud
# from ..fbr_client import FBRClient
# router = APIRouter(prefix="/reference", tags=["reference"])
# @router.get("/{endpoint}")
# async def get_reference( 
#         endpoint: str,
#         fbr_client: FBRClient = Depends(get_fbr_client_secure),
#         db: Session = Depends(get_db)
#     ):
#     cached = crud.get_cached_reference(db, endpoint)
#     if cached and (datetime.now(timezone.utc) - cached.last_updated).total_seconds() < 86400:
#         return cached.data_json
#     try:
#         if endpoint == "provinces":
#             data = await fbr_client.get_provinces()
#         elif endpoint == "document_types":
#             data = await fbr_client.get_document_types()
#         elif endpoint == "uoms":
#             data = await fbr_client.get_uoms()
#         elif endpoint == "item_codes":
#             data = await fbr_client.get_item_codes()
#         elif endpoint == "transaction_types":
#             data = await fbr_client.get_transaction_types()  
#         else:
#             raise HTTPException(
#                 status_code=404,
#                 detail=f"Reference endpoint '{endpoint}' not supported",
#             )
#     except Exception as e:
#         raise HTTPException(status_code=503, detail=f"FBR API error: {str(e)}")
#     crud.update_reference_cache(db, endpoint, data)
#     return data

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..dependencies.fbr import get_fbr_client_secure
from ..database import get_db
from .. import crud
from ..fbr_client import FBRClient
import logging

router = APIRouter(prefix="/reference", tags=["reference"])
logger = logging.getLogger(__name__)
CACHE_TTL = timedelta(hours=24)
REFERENCE_ENDPOINTS = {
    "provinces": "get_provinces",
    "document_types": "get_document_types",
    "uoms": "get_uoms",
    "item_codes": "get_item_codes",
    "transaction_types": "get_transaction_types",
}

def is_cache_fresh(last_updated: datetime) -> bool:
    if not last_updated:
        return False
    if last_updated.tzinfo is None:
        last_updated = last_updated.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - last_updated) < CACHE_TTL

@router.get("/{endpoint}")
async def get_reference(
    endpoint: str,
    fbr_client: FBRClient = Depends(get_fbr_client_secure),
    db: Session = Depends(get_db),
):
    endpoint = endpoint.strip().lower()

    if endpoint not in REFERENCE_ENDPOINTS:
        raise HTTPException(
            status_code=404,
            detail=f"Reference endpoint '{endpoint}' not supported",
        )

    cached = crud.get_cached_reference(db, endpoint)
    if cached and is_cache_fresh(cached.last_updated):
        logger.info(f"[CACHE HIT] {endpoint}")
        return cached.data_json
    stale_data = cached.data_json if cached else None
    try:
        method_name = REFERENCE_ENDPOINTS[endpoint]
        fetcher = getattr(fbr_client, method_name)
        logger.info(f"[FBR FETCH] {endpoint}")
        data = await fetcher()
        crud.update_reference_cache(db, endpoint, data)
        return data
    except Exception as exc:
        logger.error(f"[FBR ERROR] {endpoint}: {exc}")
        if stale_data:
            logger.warning(f"[FALLBACK CACHE USED] {endpoint}")
            return stale_data
        raise HTTPException(
            status_code=503,
            detail=f"FBR API error: {str(exc)}",
        )