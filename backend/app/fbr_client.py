from typing import Any, Dict, List, Optional
import httpx

class FBRClient:
    def __init__(self, token: str, is_sandbox: bool = True):
        self.token = token
        self.is_sandbox = is_sandbox
        self.base_url = "https://gw.fbr.gov.pk"
        self.post_url = f"/di_data/v1/di/postinvoicedata"
        self.validate_url = f"/di_data/v1/di/validateinvoicedata"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
    async def _request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        ) -> Any:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    headers=self.headers,
                    json=json_data,
                    params=params,
                )
                response.raise_for_status()
                try:
                    return response.json()
                except Exception:
                    raise Exception(
                        f"FBR returned non-JSON response: {response.text}"
                    )
            except httpx.RequestError as e:
                raise Exception(f"FBR connection error: {str(e)}")
            
    async def post_invoice(self, payload: Dict) -> Dict:
        return await self._request(
            "POST",
            self.post_url,
            json_data=payload,
        )
    
    async def validate_invoice(self, payload: Dict) -> Dict:
        return await self._request(
            "POST",
            self.validate_url,
            json_data=payload,
        )
    
    async def get_provinces(self) -> List[Dict]:
        return await self._request("GET", "/pdi/v1/provinces")
    
    async def get_document_types(self) -> List[Dict]:
        return await self._request("GET", "/pdi/v1/doctypecode")
    
    async def get_item_codes(self) -> List[Dict]:
        return await self._request("GET", "/pdi/v1/itemdesccode")
    
    async def get_sro_item_codes(self) -> List[Dict]:
        return await self._request("GET", "/pdi/v1/sroitemcode")
    
    async def get_uoms(self) -> List[Dict]:
        return await self._request("GET", "/pdi/v1/uom")
    async def get_hs_uoms(self, hs_code: str, annexure_id: int) -> List[Dict]:
        params = {
            "hs_code": hs_code,
            "annexure_id": annexure_id,
        }
        return await self._request("GET", "/pdi/v2/HS_UOM", params=params)
    
    async def get_sro_schedules(
        self,
        rate_id: int,
        date: str,
        origination_supplier_csv: int,
    ) -> List[Dict]:
        params = {
            "rate_id": rate_id,
            "date": date,
            "origination_supplier_csv": origination_supplier_csv,
        }
        return await self._request("GET", "/pdi/v1/SroSchedule", params=params)
    
    async def get_sro_items(self, date: str, sro_id: int) -> List[Dict]:
        params = {
            "date": date,
            "sro_id": sro_id,
        }
        return await self._request("GET", "/pdi/v2/SROItem", params=params)
    
    async def get_transaction_types(self) -> List[Dict]:
        return await self._request("GET", "/pdi/v1/transtypecode")
    
    async def get_sale_type_rates(
        self,
        date: str,
        transTypeId: int,
        originationSupplier: int,
    ) -> List[Dict]:
        params = {
            "date": date,
            "transTypeId": transTypeId,
            "originationSupplier": originationSupplier,
        }
        return await self._request("GET", "/pdi/v2/SaleTypeToRate", params=params)
    
    async def get_registration_type(self, registration_no: str) -> Dict:
        payload = {
            "Registration_No":registration_no,
        }
        return await self._request(
            "POST",
            "/dist/v1/Get_Reg_Type",
            json_data=payload
        )
    
    async def get_statl(self, registration_no: str, date: str) -> Dict:
        payload = {
            "regno": registration_no,
            "date": date
        }
        return await self._request(
            "POST",
            "/dist/v1/statl",
            json_data=payload
        )

