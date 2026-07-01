from fastapi import APIRouter
import uuid
from typing import Any, Dict

router = APIRouter()

@router.post("/honeytokens")
async def create_honeytoken() -> Dict[str, Any]:
    """Create a new deception honeytoken."""
    token_id = f"ht_{uuid.uuid4().hex[:12]}"
    return {
        "id": token_id,
        "token_type": "AWS_KEY",
        "value": f"AKIA{uuid.uuid4().hex.upper()[:16]}",
        "status": "ACTIVE",
        "message": "Honeytoken generated. Inject this into agent context to detect exfiltration."
    }

@router.get("/honeytokens")
async def list_honeytokens() -> Dict[str, Any]:
    """List active deception honeytokens."""
    return {
        "total": 1,
        "items": [
            {
                "id": "ht_default",
                "token_type": "DATABASE_CREDENTIAL",
                "value": "postgres://admin:secret@honeytoken.internal:5432/production",
                "status": "ACTIVE",
                "triggered_count": 0
            }
        ]
    }
