from fastapi import APIRouter

from app.api.routers import admin, ai, auth, donations, donors, impact, ngos, requests

api_router = APIRouter()
api_router.include_router(ai.router)
api_router.include_router(auth.router)
api_router.include_router(donors.router)
api_router.include_router(ngos.router)
api_router.include_router(donations.router)
api_router.include_router(requests.router)
api_router.include_router(impact.router)
api_router.include_router(admin.router)
