from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app import models


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Location(APIModel):
    area: str
    address: str
    city: str
    lat: float
    lng: float


class Donor(APIModel):
    id: str
    name: str
    phone: str
    donor_type: str
    reliability: int
    preferred_radius_km: float
    location: Location


class NGO(APIModel):
    id: str
    name: str
    contact_name: str
    phone: str
    reliability: int
    max_daily_capacity: int
    current_load: int
    focus_areas: list[str] = Field(default_factory=list)
    location: Location


class DonationCreate(BaseModel):
    donor_id: str
    title: str
    category: str
    food_type: str
    prepared_time: datetime
    storage_condition: str
    quantity: int = Field(gt=0)
    unit: str
    meals_estimate: int = Field(ge=0)
    safety_window_hours: int = Field(default=2, ge=0)
    shelf_life_hours: float | None = Field(default=None, gt=0)
    image_url: str | None = None
    image_freshness_label: models.ImageFreshnessLabel | None = None
    image_visual_label: str | None = None
    image_visual_confidence: float | None = Field(default=None, ge=0, le=100)
    expires_at: datetime | None = None
    pickup_start: datetime
    pickup_end: datetime
    location: Location
    notes: str = ""


class Donation(APIModel):
    id: str
    donor_id: str
    title: str
    category: str
    food_type: str
    prepared_time: datetime
    storage_condition: str
    quantity: int
    unit: str
    meals_estimate: int
    safety_window_hours: int
    created_at: datetime
    expires_at: datetime
    pickup_start: datetime
    pickup_end: datetime
    status: models.DonationStatus
    location: Location
    shelf_life_hours: float | None = None
    image_url: str | None = None
    image_freshness_label: models.ImageFreshnessLabel | None = None
    image_visual_label: str | None = None
    image_visual_confidence: float | None = None
    notes: str = ""
    request_id: str | None = None
    reserved_for_request_id: str | None = None
    picked_up_at: datetime | None = None
    delivered_at: datetime | None = None


class RequestCreate(BaseModel):
    ngo_id: str
    title: str
    category: str
    quantity_needed: int = Field(gt=0)
    unit: str
    people_served: int = Field(ge=0)
    priority: int = Field(ge=1, le=5)
    needed_by: datetime
    max_distance_km: float = Field(gt=0)
    location: Location
    meal_slot: models.MealSlot | None = None
    notes: str = ""


class DonationRequestCreate(BaseModel):
    donation_id: str
    ngo_id: str


class Request(APIModel):
    id: str
    ngo_id: str
    title: str
    category: str
    quantity_needed: int
    unit: str
    people_served: int
    priority: int
    created_at: datetime
    needed_by: datetime
    max_distance_km: float
    status: models.RequestStatus
    location: Location
    meal_slot: models.MealSlot | None = None
    notes: str = ""
    matched_donation_id: str | None = None


class Notification(APIModel):
    id: str
    audience: str
    recipient_id: str | None
    title: str
    message: str
    level: models.NotificationLevel
    created_at: datetime
    read: bool


class ImpactMetrics(APIModel):
    snapshot_at: datetime
    total_donations: int
    active_donations: int
    delivered_donations: int
    total_quantity_kg: float
    meals_recovered: int
    co2e_avoided_kg: float
    open_requests: int
    fulfilled_requests: int
    donors_active: int
    ngos_active: int
    delivery_success_rate: float


class DonationStatusChange(BaseModel):
    status: models.DonationStatus
    request_id: str | None = None


class RequestStatusChange(BaseModel):
    status: models.RequestStatus
    donation_id: str | None = None


class RequestApprovalPayload(BaseModel):
    donation_id: str | None = None


class ReserveDonationRequest(BaseModel):
    request_id: str


class MatchFactorScores(BaseModel):
    distance: float
    expiry_urgency: float
    safety_window: float
    capacity: float
    demand: float
    reliability: float


class MatchCandidate(BaseModel):
    request_id: str
    ngo_id: str
    request_title: str
    ngo_name: str
    total_score: float
    distance_km: float
    factor_scores: MatchFactorScores
    explanation: str


class AdminOverview(BaseModel):
    snapshot_at: datetime
    donor_count: int
    ngo_count: int
    donation_count: int
    open_request_count: int
    reserved_donation_count: int
    expiring_donations: list[Donation]
    notifications: list[Notification]
    top_matches: list[MatchCandidate]
    impact: ImpactMetrics


class AIFactorBreakdown(APIModel):
    distance: float
    capacity: float
    quantity_fit: float
    urgency_fit: float
    category_fit: float
    acceptance_likelihood: float
    demand_pressure: float


class AIMatchCandidate(APIModel):
    request_id: str
    ngo_id: str
    ngo_name: str
    request_title: str
    model_version: str | None = None
    food_category: str
    category_confidence: float | None = None
    confidence_bucket: str | None = None
    category_uncertain: bool = False
    uncertainty_reason: str | None = None
    top_categories: list[CategoryPrediction] = Field(default_factory=list)
    fit_percentage: float
    confidence_percentage: float
    distance_km: float
    eta_minutes: int
    time_left_hours: float
    feasible: bool
    feasibility_reason: str
    visual_label: str | None = None
    visual_confidence: float | None = None
    time_based_status: str
    final_status: str
    reasons: list[str]
    explanation: str
    breakdown: AIFactorBreakdown


class AIMatchResponse(BaseModel):
    donation_id: str
    best_match: AIMatchCandidate | None = None
    matches: list[AIMatchCandidate] = Field(default_factory=list)


class CategoryPrediction(APIModel):
    label: str
    confidence: float


class ExpiryPredictionRequest(BaseModel):
    food_type: str
    food_category: str | None = None
    prepared_time: datetime
    current_time: datetime | None = None
    storage_condition: str = "ambient"
    quantity: int = Field(gt=0)
    image_label: models.ImageFreshnessLabel | None = None
    visual_label: str | None = None
    visual_confidence: float | None = Field(default=None, ge=0, le=100)
    category_confidence: float | None = Field(default=None, ge=0, le=1)
    confidence_bucket: str | None = None
    category_uncertain: bool = False
    uncertainty_reason: str | None = None
    top_categories: list[CategoryPrediction] = Field(default_factory=list)
    model_version: str | None = None
    debug: bool = False
    shelf_life_hours: float | None = Field(default=None, gt=0)


class ExpiryPredictionResponse(BaseModel):
    model_version: str | None = None
    food_category: str
    category_confidence: float | None = None
    confidence_bucket: str | None = None
    category_uncertain: bool = False
    uncertainty_reason: str | None = None
    top_categories: list[CategoryPrediction] = Field(default_factory=list)
    shelf_life_hours: float
    time_elapsed_hours: float
    time_left_hours: float
    safe_until: datetime
    visual_label: str | None = None
    visual_confidence: float | None = None
    urgency_status: str
    time_based_status: str
    final_status: str
    recommended_action: str
    explanation: str
    debug_summary: str | None = None


class RouteOptimizationRequest(BaseModel):
    donation_id: str
    request_ids: list[str] = Field(default_factory=list)


class RouteStop(APIModel):
    request_id: str
    ngo_id: str
    ngo_name: str
    area: str
    distance_km: float
    eta_minutes_from_previous: int
    cumulative_eta_minutes: int
    priority_label: str
    time_left_hours: float
    feasible: bool
    feasibility_reason: str


class RouteOptimizationResponse(BaseModel):
    donation_id: str
    total_distance_km: float
    total_eta_minutes: int
    summary: str
    stops: list[RouteStop] = Field(default_factory=list)


class AreaInsight(APIModel):
    area: str
    request_count: int
    urgency_score: float
    explanation: str


class ActorInsight(APIModel):
    actor_id: str
    actor_name: str
    metric_value: float
    explanation: str


class AIImpactSummaryResponse(BaseModel):
    snapshot_at: datetime
    meals_saved_this_week: int
    waste_reduced_kg: float
    co2_saved_kg: float
    expected_meals_next_week: int
    weekly_growth_pct: float
    high_need_zones: list[AreaInsight] = Field(default_factory=list)
    top_donor: ActorInsight | None = None
    top_ngo: ActorInsight | None = None
    explanation: list[str] = Field(default_factory=list)


class ImpactForecastPoint(APIModel):
    label: str
    predicted_meals_saved: int
    predicted_waste_reduced_kg: float
    predicted_open_requests: int


class AIImpactForecastResponse(BaseModel):
    snapshot_at: datetime
    trend_direction: str
    confidence_percentage: float
    projected_meals_saved_next_week: int
    projected_waste_reduced_kg_next_week: float
    high_need_zones: list[AreaInsight] = Field(default_factory=list)
    forecast: list[ImpactForecastPoint] = Field(default_factory=list)
    explanation: str


class AIAssistantRequest(BaseModel):
    question: str = Field(min_length=2, max_length=400)


class AIAssistantResponse(BaseModel):
    answer: str
    bullet_points: list[str] = Field(default_factory=list)
    follow_up_prompts: list[str] = Field(default_factory=list)
    cited_entity_ids: list[str] = Field(default_factory=list)


class FoodImageAnalysisResponse(BaseModel):
    model_version: str
    food_type_guess: str
    food_category: str
    category_confidence: float
    confidence_bucket: str
    category_uncertain: bool
    uncertainty_reason: str | None = None
    top_categories: list[CategoryPrediction] = Field(default_factory=list)
    visual_label: str
    visual_confidence: float
    image_label: models.ImageFreshnessLabel
    quantity_estimate: str
    packaging_quality: str
    model_key: str
    suggested_storage: str
    distribution_urgency: str
    explanation: str
    debug_summary: str | None = None


class ModelInfoResponse(BaseModel):
    model_version: str
    trained_at: str
    num_classes: int
    class_names: list[str]
    model_path: str
    class_map_path: str


class WasteRiskResponse(BaseModel):
    donation_id: str
    risk_score: float
    risk_label: str
    final_status: str
    top_reasons: list[str] = Field(default_factory=list)
    recommended_action: str
    safe_hours_remaining: float
    best_match_fit: float


class AuthRegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    role: models.UserRole


class AuthLoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    role: models.UserRole


class AuthUser(APIModel):
    id: str
    email: str
    role: models.UserRole
    profile_id: str | None


class AuthSession(BaseModel):
    token: str
    user: AuthUser


class LogoutResponse(BaseModel):
    success: bool


class HealthResponse(BaseModel):
    status: str
    dataset: str
    donors: int
    ngos: int
    donations: int
    requests: int
