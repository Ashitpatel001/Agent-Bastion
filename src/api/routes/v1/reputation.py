from fastapi import APIRouter
from typing import Any
from db.schemas import ReputationCheckRequest, ReputationCheckResponse
from security.reputation import ReputationManager

router = APIRouter()


@router.post("/check", response_model=ReputationCheckResponse)
async def check_reputation(request: ReputationCheckRequest) -> Any:
    """Check the reputation of a domain or URL using ReputationManager."""
    rep_mgr = ReputationManager()
    domain = rep_mgr.get_domain(request.url) or request.url
    is_safe = rep_mgr.check(domain)
    trust = "HIGH TRUST" if is_safe else "CRITICAL RISK"
    detail_str = f"Domain '{domain}' verified safe by Autonomous Threat Intelligence." if is_safe else f"Domain '{domain}' flagged as high-risk/denylisted by proxy firewall."
    return ReputationCheckResponse(
        url=request.url,
        domain=domain,
        trust_level=trust,
        is_safe=is_safe,
        risk_score=10 if is_safe else 90,
        categories=["benign"] if is_safe else ["phishing", "malware"],
        details=detail_str
    )

