from fastapi import APIRouter, Depends

from . import (
    analytics, agents, api_keys, audit, auth, browser_sessions,
    deception, dx, incidents, jobs, organizations, policies,
    reputation, risk, sandbox, security_events, settings,
    system, tenants, users, observability
)

from api.auth import RequireRole
from db.models import UserRole

# Define role tiers
viewer_roles = [UserRole.OWNER, UserRole.ADMIN, UserRole.OPERATOR, UserRole.SECURITY_ANALYST, UserRole.DEVELOPER, UserRole.VIEWER, UserRole.admin, UserRole.operator, UserRole.viewer]
dev_roles = [UserRole.OWNER, UserRole.ADMIN, UserRole.OPERATOR, UserRole.DEVELOPER, UserRole.admin, UserRole.operator]
sec_roles = [UserRole.OWNER, UserRole.ADMIN, UserRole.OPERATOR, UserRole.SECURITY_ANALYST, UserRole.admin, UserRole.operator]
operator_roles = [UserRole.OWNER, UserRole.ADMIN, UserRole.OPERATOR, UserRole.SECURITY_ANALYST, UserRole.DEVELOPER, UserRole.admin, UserRole.operator]
admin_roles = [UserRole.OWNER, UserRole.ADMIN, UserRole.admin]

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(dx.router, prefix="/dx", tags=["Developer Experience"], dependencies=[Depends(RequireRole(dev_roles))])
api_v1_router.include_router(observability.router, prefix="/observability", tags=["Observability & Security Intelligence"])
api_v1_router.include_router(users.router, prefix="/users", tags=["Users"], dependencies=[Depends(RequireRole(admin_roles))])
api_v1_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations"], dependencies=[Depends(RequireRole(admin_roles))])
api_v1_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"], dependencies=[Depends(RequireRole(admin_roles))])
api_v1_router.include_router(api_keys.router, prefix="/api-keys", tags=["API Keys"], dependencies=[Depends(RequireRole(admin_roles))])
api_v1_router.include_router(agents.router, prefix="/agents", tags=["Agents"], dependencies=[Depends(RequireRole(dev_roles))])
api_v1_router.include_router(browser_sessions.router, prefix="/browser-sessions", tags=["Browser Sessions"], dependencies=[Depends(RequireRole(dev_roles))])
api_v1_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"], dependencies=[Depends(RequireRole(dev_roles))])
api_v1_router.include_router(sandbox.router, prefix="/sandbox", tags=["Sandbox"], dependencies=[Depends(RequireRole(dev_roles))])
api_v1_router.include_router(incidents.router, prefix="/incidents", tags=["Incidents"], dependencies=[Depends(RequireRole(sec_roles))])
api_v1_router.include_router(security_events.router, prefix="/security-events", tags=["Security Events"], dependencies=[Depends(RequireRole(sec_roles))])
api_v1_router.include_router(audit.router, prefix="/audit", tags=["Audit"], dependencies=[Depends(RequireRole(sec_roles))])
api_v1_router.include_router(policies.router, prefix="/policies", tags=["Policies"], dependencies=[Depends(RequireRole(admin_roles))])
api_v1_router.include_router(risk.router, prefix="/risk", tags=["Risk"], dependencies=[Depends(RequireRole(sec_roles))])
api_v1_router.include_router(reputation.router, prefix="/reputation", tags=["Reputation"], dependencies=[Depends(RequireRole(sec_roles))])
api_v1_router.include_router(deception.router, prefix="/deception", tags=["Deception"], dependencies=[Depends(RequireRole(admin_roles))])
api_v1_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"], dependencies=[Depends(RequireRole(viewer_roles))])
api_v1_router.include_router(settings.router, prefix="/settings", tags=["Settings"], dependencies=[Depends(RequireRole(admin_roles))])
api_v1_router.include_router(system.router, prefix="/system", tags=["System"])
