from fastapi import APIRouter
from typing import Any
from db.schemas import RiskAssessmentRequest, RiskAssessmentResponse
from security.risk_scorer import RiskScorer

router = APIRouter()


@router.post("/assess", response_model=RiskAssessmentResponse)
async def assess_risk(request: RiskAssessmentRequest) -> Any:
    """Perform an on-demand risk assessment using RiskScorer."""
    scorer = RiskScorer()
    action_name = request.action or "navigate"
    action_params = {"url": request.url} if request.url else {"text": request.content or ""}
    current_url = request.url or ""

    res = scorer.calculate_risk(
        action_name=action_name,
        action_params=action_params,
        current_url=current_url,
        security_state="UNKNOWN"
    )

    recommendation = res.get("recommendation", "MONITOR")
    return RiskAssessmentResponse(
        risk_score=res["score"],
        risk_level=res["level"],
        breakdown=res["breakdown"],
        recommendations=[f"Recommended policy action: {recommendation}"]
    )

