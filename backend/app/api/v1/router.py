"""
API v1 router aggregator.

Collects all endpoint routers under the ``/api/v1`` prefix.
Add new feature routers here as the application grows.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health
from app.api.v1.climate import router as climate_router
from app.api.v1.predict import router as predict_router

api_v1_router = APIRouter()

# Health endpoints
api_v1_router.include_router(health.router)

# Climate endpoints
api_v1_router.include_router(climate_router)

# Prediction endpoints
api_v1_router.include_router(predict_router)

# Future routers
# api_v1_router.include_router(simulation.router)
# api_v1_router.include_router(regions.router)