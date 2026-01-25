from fastapi import APIRouter, Depends
from src.api.v1.pwa import dashboard, jobs, customers, chat, invoices, settings, onboarding, billing
from src.api.dependencies.clerk_auth import verify_token

router = APIRouter(dependencies=[Depends(verify_token)])

router.include_router(dashboard.router, prefix="/dashboard", tags=["pwa-dashboard"])
router.include_router(onboarding.router, prefix="/onboarding", tags=["pwa-onboarding"])
router.include_router(jobs.router, prefix="/jobs", tags=["pwa-jobs"])
router.include_router(customers.router, prefix="/customers", tags=["pwa-customers"])
router.include_router(chat.router, prefix="/chat", tags=["pwa-chat"])
router.include_router(invoices.router, prefix="/invoices", tags=["pwa-invoices"])
router.include_router(settings.router, prefix="/settings", tags=["pwa-settings"])
router.include_router(billing.router, prefix="/billing", tags=["pwa-billing"])
