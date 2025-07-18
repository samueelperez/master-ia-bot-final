"""
API routes for the External Data Service.
"""
from fastapi import APIRouter

from api.routes import news, social, economic, integration, auth

# Create API router
api_router = APIRouter()

# Include routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(news.router, prefix="/news", tags=["news"])
api_router.include_router(social.router, prefix="/social", tags=["social"])
api_router.include_router(economic.router, prefix="/economic", tags=["economic"])
api_router.include_router(integration.router, prefix="/integration", tags=["integration"])
