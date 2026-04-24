from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.schemas import HealthResponse
from app.services.model_loader import validate_category_model_integrity
from app.store import get_store


logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    validate_category_model_integrity()
    app = FastAPI(
        title="PS-12 Food Rescue Platform",
        version="1.0.0",
        description="Backend API for donors, NGOs, donations, requests, impact analytics, and admin operations.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    def health_check() -> HealthResponse:
        store = get_store()
        return HealthResponse(
            status="ok",
            dataset="hyderabad-demo",
            donors=len(store.donors),
            ngos=len(store.ngos),
            donations=len(store.donations),
            requests=len(store.requests),
        )

    app.include_router(api_router)
    return app
