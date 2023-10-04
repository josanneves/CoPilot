from fastapi import APIRouter, HTTPException, Security, security, Depends
from fastapi.security import HTTPAuthorizationCredentials
from app.smtp.schema.configure import SMTPResponse
import regex
from app.auth.utils import AuthHandler
from app.db.db_session import session
from app.integrations.dnstwist.schema.analyze import DomainAnalysisResponse, DomainRequestBody
from app.integrations.dnstwist.services.analyze import analyze_domain, analyze_domain_phishing
from loguru import logger

dnstwist_router = APIRouter()

def is_domain(domain: str) -> DomainRequestBody:
    """
    Check if the provided domain is valid.

    Args:
        domain (str): The domain to check.

    Returns:
        bool: True if the domain is valid, False otherwise.
    """
    logger.info(f"Checking if domain {domain} is valid.")
    pattern = regex.compile(
        r"^(?:[a-zA-Z0-9]+([-._]?[a-zA-Z0-9]+)*\.)+[a-zA-Z]{2,}$",
    )
    if not pattern.match(domain):
        raise HTTPException(status_code=400, detail="Invalid domain")
    return DomainRequestBody(domain=domain)

@dnstwist_router.post('/analyze', response_model=DomainAnalysisResponse, status_code=200, description='Analyze domain with DNS Twist')
async def analyze(body: DomainRequestBody = Depends(is_domain)):
    return analyze_domain(body.domain)

# ! TODO: Add phishing analysis - Need more clarification on this
# @dnstwist_router.post('/analyze/phishing', response_model=DomainAnalysisResponse, status_code=200, description='Analyze domain with DNS Twist')
# async def analyze_phishing(body: DomainRequestBody = Depends(is_domain)):
#     return analyze_domain_phishing(body.domain)
