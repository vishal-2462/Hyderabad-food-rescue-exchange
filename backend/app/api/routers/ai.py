from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app import schemas
from app.services.ai_assistant import answer_question
from app.services.ai_matching import rank_ai_matches
from app.services.freshness_engine import analyze_freshness
from app.services.image_inference import analyze_food_image
from app.services.impact_analytics import forecast_impact, summarize_impact_intelligence
from app.services.model_loader import load_category_model_artifacts
from app.services.route_optimizer import optimize_route
from app.services.waste_risk import score_waste_risk
from app.store import get_store

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/match/{donation_id}", response_model=schemas.AIMatchResponse)
def get_ai_match(donation_id: str) -> schemas.AIMatchResponse:
    store = get_store()
    donation = store.donations.get(donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found")

    matches = rank_ai_matches(donation, list(store.requests.values()), store.ngos, store.donors)
    return schemas.AIMatchResponse(
        donation_id=donation.id,
        best_match=schemas.AIMatchCandidate.model_validate(matches[0]) if matches else None,
        matches=[schemas.AIMatchCandidate.model_validate(match) for match in matches],
    )


def _serialize_freshness(payload: schemas.ExpiryPredictionRequest) -> schemas.ExpiryPredictionResponse:
    prediction = analyze_freshness(
        food_type=payload.food_type,
        food_category=payload.food_category,
        prepared_time=payload.prepared_time,
        current_time=payload.current_time,
        storage_condition=payload.storage_condition,
        quantity=payload.quantity,
        image_label=payload.image_label,
        visual_label=payload.visual_label,
        visual_confidence=payload.visual_confidence,
        category_confidence=payload.category_confidence,
        confidence_bucket=payload.confidence_bucket,
        category_uncertain=payload.category_uncertain,
        uncertainty_reason=payload.uncertainty_reason,
        top_categories=tuple(payload.top_categories),
        model_version=payload.model_version,
        debug_summary=None,
        shelf_life_hours=payload.shelf_life_hours,
    )
    return schemas.ExpiryPredictionResponse(
        model_version=prediction.model_version,
        food_category=prediction.food_category,
        category_confidence=prediction.category_confidence,
        confidence_bucket=prediction.confidence_bucket,
        category_uncertain=prediction.category_uncertain,
        uncertainty_reason=prediction.uncertainty_reason,
        top_categories=[schemas.CategoryPrediction.model_validate(item) for item in prediction.top_categories],
        shelf_life_hours=prediction.shelf_life_hours,
        time_elapsed_hours=prediction.time_elapsed_hours,
        time_left_hours=prediction.time_left_hours,
        safe_until=prediction.safe_until,
        visual_label=prediction.visual_label,
        visual_confidence=prediction.visual_confidence,
        urgency_status=prediction.urgency_status,
        time_based_status=prediction.time_based_status,
        final_status=prediction.final_status,
        recommended_action=prediction.recommended_action,
        explanation=prediction.explanation,
        debug_summary=prediction.debug_summary if payload.debug else None,
    )


@router.get("/model-info", response_model=schemas.ModelInfoResponse)
def get_model_info() -> schemas.ModelInfoResponse:
    artifacts = load_category_model_artifacts()
    return schemas.ModelInfoResponse(
        model_version=artifacts.version,
        trained_at=artifacts.trained_at,
        num_classes=artifacts.num_classes,
        class_names=list(artifacts.class_names),
        model_path=str(artifacts.model_path),
        class_map_path=str(artifacts.class_map_path),
    )


@router.post("/analyze-freshness", response_model=schemas.ExpiryPredictionResponse)
def analyze_food_freshness(payload: schemas.ExpiryPredictionRequest) -> schemas.ExpiryPredictionResponse:
    return _serialize_freshness(payload)


@router.post("/predict-expiry", response_model=schemas.ExpiryPredictionResponse)
def predict_expiry(payload: schemas.ExpiryPredictionRequest) -> schemas.ExpiryPredictionResponse:
    return _serialize_freshness(payload)


@router.post("/optimize-route", response_model=schemas.RouteOptimizationResponse)
def optimize_delivery_route(payload: schemas.RouteOptimizationRequest) -> schemas.RouteOptimizationResponse:
    store = get_store()
    donation = store.donations.get(payload.donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found")

    if payload.request_ids:
        requests = []
        for request_id in payload.request_ids:
            request = store.requests.get(request_id)
            if request is None:
                raise HTTPException(status_code=404, detail=f"Request not found: {request_id}")
            requests.append(request)
    else:
        requests = list(store.requests.values())

    route = optimize_route(donation, requests, store.ngos, store.donors)
    return schemas.RouteOptimizationResponse(
        donation_id=donation.id,
        total_distance_km=route.total_distance_km,
        total_eta_minutes=route.total_eta_minutes,
        summary=route.summary,
        stops=[schemas.RouteStop.model_validate(stop) for stop in route.stops],
    )


@router.get("/impact-summary", response_model=schemas.AIImpactSummaryResponse)
def get_ai_impact_summary() -> schemas.AIImpactSummaryResponse:
    store = get_store()
    summary = summarize_impact_intelligence(list(store.donations.values()), list(store.requests.values()), list(store.donors.values()), list(store.ngos.values()))
    return schemas.AIImpactSummaryResponse(
        snapshot_at=summary.snapshot_at,
        meals_saved_this_week=summary.meals_saved_this_week,
        waste_reduced_kg=summary.waste_reduced_kg,
        co2_saved_kg=summary.co2_saved_kg,
        expected_meals_next_week=summary.expected_meals_next_week,
        weekly_growth_pct=summary.weekly_growth_pct,
        high_need_zones=[schemas.AreaInsight.model_validate(zone) for zone in summary.high_need_zones],
        top_donor=schemas.ActorInsight.model_validate(summary.top_donor) if summary.top_donor is not None else None,
        top_ngo=schemas.ActorInsight.model_validate(summary.top_ngo) if summary.top_ngo is not None else None,
        explanation=summary.explanation,
    )


@router.get("/impact-forecast", response_model=schemas.AIImpactForecastResponse)
def get_ai_impact_forecast() -> schemas.AIImpactForecastResponse:
    store = get_store()
    forecast = forecast_impact(list(store.donations.values()), list(store.requests.values()), list(store.donors.values()), list(store.ngos.values()))
    return schemas.AIImpactForecastResponse(
        snapshot_at=forecast.snapshot_at,
        trend_direction=forecast.trend_direction,
        confidence_percentage=forecast.confidence_percentage,
        projected_meals_saved_next_week=forecast.projected_meals_saved_next_week,
        projected_waste_reduced_kg_next_week=forecast.projected_waste_reduced_kg_next_week,
        high_need_zones=[schemas.AreaInsight.model_validate(zone) for zone in forecast.high_need_zones],
        forecast=[schemas.ImpactForecastPoint.model_validate(point) for point in forecast.forecast],
        explanation=forecast.explanation,
    )


@router.post("/assistant", response_model=schemas.AIAssistantResponse)
def ask_ai_assistant(payload: schemas.AIAssistantRequest) -> schemas.AIAssistantResponse:
    store = get_store()
    response = answer_question(payload.question, list(store.donations.values()), list(store.requests.values()), list(store.donors.values()), list(store.ngos.values()))
    return schemas.AIAssistantResponse(
        answer=response.answer,
        bullet_points=response.bullet_points,
        follow_up_prompts=response.follow_up_prompts,
        cited_entity_ids=response.cited_entity_ids,
    )


@router.post("/analyze-food-image", response_model=schemas.FoodImageAnalysisResponse)
async def analyze_uploaded_food_image(file: UploadFile = File(...)) -> schemas.FoodImageAnalysisResponse:
    content = await file.read()
    analysis = analyze_food_image(filename=file.filename or "upload.jpg", content_type=file.content_type, byte_length=len(content))
    return schemas.FoodImageAnalysisResponse(
        model_version=analysis.model_version,
        food_type_guess=analysis.food_type_guess,
        food_category=analysis.food_category,
        category_confidence=analysis.category_confidence,
        confidence_bucket=analysis.confidence_bucket,
        category_uncertain=analysis.category_uncertain,
        uncertainty_reason=analysis.uncertainty_reason,
        top_categories=[schemas.CategoryPrediction.model_validate(item) for item in analysis.top_categories],
        visual_label=analysis.visual_label,
        visual_confidence=analysis.visual_confidence,
        image_label=analysis.image_label,
        quantity_estimate=analysis.quantity_estimate,
        packaging_quality=analysis.packaging_quality,
        model_key=analysis.model_key,
        suggested_storage=analysis.suggested_storage,
        distribution_urgency=analysis.distribution_urgency,
        explanation=analysis.explanation,
        debug_summary=analysis.debug_summary,
    )


@router.get("/waste-risk/{donation_id}", response_model=schemas.WasteRiskResponse)
def get_waste_risk(donation_id: str) -> schemas.WasteRiskResponse:
    store = get_store()
    donation = store.donations.get(donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found")

    risk = score_waste_risk(donation, list(store.requests.values()), store.ngos, store.donors)
    return schemas.WasteRiskResponse(
        donation_id=risk.donation_id,
        risk_score=risk.risk_score,
        risk_label=risk.risk_label,
        final_status=risk.final_status,
        top_reasons=risk.top_reasons,
        recommended_action=risk.recommended_action,
        safe_hours_remaining=risk.safe_hours_remaining,
        best_match_fit=risk.best_match_fit,
    )
