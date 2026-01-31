from fastapi import APIRouter, Depends
from src.api.v1.pwa import (
    jobs,
    customers,
    chat,
    invoices,
    settings,
    onboarding,
    billing,
    routing,
    expenses,
    quickbooks,
    user,
    business,
    quotes,
    addresses,
    services,
    data_management,
    requests,
    analytics_proxy,
    marketing,
    templates,
    dev,
    backup,
    maintenance,
)
from src.api.dependencies.clerk_auth import verify_token

router = APIRouter()

# Public/Special endpoints
router.include_router(
    analytics_proxy.router, prefix="/analytics/proxy", tags=["pwa-analytics"]
)
router.include_router(backup.router, prefix="/backup", tags=["pwa-backup"])
router.include_router(
    maintenance.router, prefix="/maintenance", tags=["pwa-maintenance"]
)

# Protected endpoints
protected_router = APIRouter(dependencies=[Depends(verify_token)])
protected_router.include_router(
    onboarding.router, prefix="/onboarding", tags=["pwa-onboarding"]
)
protected_router.include_router(jobs.router, prefix="/jobs", tags=["pwa-jobs"])
protected_router.include_router(
    customers.router, prefix="/customers", tags=["pwa-customers"]
)
protected_router.include_router(
    requests.router, prefix="/requests", tags=["pwa-requests"]
)
protected_router.include_router(chat.router, prefix="/chat", tags=["pwa-chat"])
protected_router.include_router(
    invoices.router, prefix="/invoices", tags=["pwa-invoices"]
)
protected_router.include_router(quotes.router, prefix="/quotes", tags=["pwa-quotes"])
protected_router.include_router(
    addresses.router, prefix="/addresses", tags=["pwa-addresses"]
)
protected_router.include_router(
    services.router, prefix="/services", tags=["pwa-services"]
)
protected_router.include_router(
    settings.router, prefix="/settings", tags=["pwa-settings"]
)
protected_router.include_router(billing.router, prefix="/billing", tags=["pwa-billing"])
protected_router.include_router(routing.router, prefix="/routing", tags=["pwa-routing"])
protected_router.include_router(
    expenses.router, prefix="/expenses", tags=["pwa-expenses"]
)
protected_router.include_router(
    quickbooks.router, prefix="/quickbooks", tags=["pwa-quickbooks"]
)
protected_router.include_router(user.router, prefix="/user", tags=["pwa-user"])
protected_router.include_router(
    business.router, prefix="/business", tags=["pwa-business"]
)
protected_router.include_router(
    data_management.router, prefix="/data-management", tags=["pwa-data-management"]
)
protected_router.include_router(
    marketing.router, prefix="/marketing", tags=["pwa-marketing"]
)
protected_router.include_router(
    templates.router, prefix="/templates", tags=["pwa-templates"]
)
protected_router.include_router(dev.router, prefix="/dev", tags=["pwa-dev"])

router.include_router(protected_router)

# Public endpoints - include AFTER protected to avoid catch-all conflicts
router.include_router(
    analytics_proxy.router, prefix="/analytics/proxy", tags=["pwa-analytics"]
)
