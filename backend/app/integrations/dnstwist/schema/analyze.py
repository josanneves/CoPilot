from typing import List, Optional
from pydantic import BaseModel, Field

class DomainData(BaseModel):
    dns_a: Optional[List[str]]
    dns_mx: Optional[List[str]]
    dns_ns: Optional[List[str]]
    domain: str
    fuzzer: str

class DomainAnalysisResponse(BaseModel):
    data: List[DomainData]
    message: str
    success: bool

class DomainRequestBody(BaseModel):
    domain: str = Field("socfortress.co", description="The domain to analyze.")