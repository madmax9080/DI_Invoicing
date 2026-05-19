from typing import Dict, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=3, max=20),
    retry=retry_if_exception_type(
        (
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.ReadTimeout,
            httpx.HTTPStatusError,
        )
    ),
)

async def post_to_fbr(url: str, headers: Dict[str, str], payload: Dict) -> Dict:
    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code in (429, 502, 503, 504):
            response.raise_for_status()
        try:
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            raise Exception(f"FBR error {response.status_code}: {error_body}")
        
def extract_fbr_invoice_numbers(fbr_response: Dict[str, Any]) -> Dict[str, Any]:
    main_no = fbr_response.get("invoiceNumber")
    item_numbers = []
    validation = fbr_response.get("validationResponse", {})
    for row in validation.get("invoiceStatuses", []):
        if row.get("invoiceNo"):
            item_numbers.append(row["invoiceNo"])
    return {
        "invoiceNumber": main_no,
        "itemInvoiceNumbers": item_numbers,
    }
