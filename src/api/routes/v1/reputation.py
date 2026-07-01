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
    return ReputationCheckResponse(
        url=request.url,
        is_safe=is_safe,
        risk_score=10 if is_safe else 90,
        categories=["benign"] if is_safe else ["phishing", "malware"],
        details={"domain": domain, "checked_by": "ReputationManager"}
    )

