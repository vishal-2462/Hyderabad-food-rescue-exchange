export type DonationStatus =
  | "available"
  | "requested"
  | "reserved"
  | "picked_up"
  | "delivered"
  | "expired"
  | "cancelled";

export type RequestStatus =
  | "open"
  | "requested"
  | "matched"
  | "reserved"
  | "fulfilled"
  | "rejected"
  | "expired"
  | "cancelled";

export type NotificationLevel = "info" | "success" | "warning";

export type UserRole = "donor" | "ngo";

export type MealSlot = "breakfast" | "lunch" | "dinner";

export type ImageFreshnessLabel = "good" | "medium" | "spoiled";

export type FreshnessStatus = "safe" | "urgent" | "unsafe";

export interface Location {
  area: string;
  address: string;
  city: string;
  lat: number;
  lng: number;
}

export interface Donor {
  id: string;
  name: string;
  phone: string;
  donor_type: string;
  reliability: number;
  preferred_radius_km: number;
  location: Location;
}

export interface NGO {
  id: string;
  name: string;
  contact_name: string;
  phone: string;
  reliability: number;
  max_daily_capacity: number;
  current_load: number;
  focus_areas: string[];
  location: Location;
}

export interface Donation {
  id: string;
  donor_id: string;
  title: string;
  category: string;
  food_type: string;
  prepared_time: string;
  storage_condition: string;
  quantity: number;
  unit: string;
  meals_estimate: number;
  safety_window_hours: number;
  created_at: string;
  expires_at: string;
  pickup_start: string;
  pickup_end: string;
  status: DonationStatus;
  location: Location;
  shelf_life_hours: number | null;
  image_url: string | null;
  image_freshness_label: ImageFreshnessLabel | null;
  image_visual_label: string | null;
  image_visual_confidence: number | null;
  notes: string;
  request_id: string | null;
  reserved_for_request_id: string | null;
  picked_up_at: string | null;
  delivered_at: string | null;
}

export interface AidRequest {
  id: string;
  ngo_id: string;
  title: string;
  category: string;
  quantity_needed: number;
  unit: string;
  people_served: number;
  priority: number;
  created_at: string;
  needed_by: string;
  max_distance_km: number;
  status: RequestStatus;
  location: Location;
  meal_slot: MealSlot | null;
  notes: string;
  matched_donation_id: string | null;
}

export interface Notification {
  id: string;
  audience: string;
  recipient_id: string | null;
  title: string;
  message: string;
  level: NotificationLevel;
  created_at: string;
  read: boolean;
}

export interface ImpactMetrics {
  snapshot_at: string;
  total_donations: number;
  active_donations: number;
  delivered_donations: number;
  total_quantity_kg: number;
  meals_recovered: number;
  co2e_avoided_kg: number;
  open_requests: number;
  fulfilled_requests: number;
  donors_active: number;
  ngos_active: number;
  delivery_success_rate: number;
}

export interface MatchFactorScores {
  distance: number;
  expiry_urgency: number;
  safety_window: number;
  capacity: number;
  demand: number;
  reliability: number;
}

export interface MatchCandidate {
  request_id: string;
  ngo_id: string;
  request_title: string;
  ngo_name: string;
  total_score: number;
  distance_km: number;
  factor_scores: MatchFactorScores;
  explanation: string;
}

export interface AIFactorBreakdown {
  distance: number;
  capacity: number;
  quantity_fit: number;
  urgency_fit: number;
  category_fit: number;
  acceptance_likelihood: number;
  demand_pressure: number;
}

export interface CategoryPrediction {
  label: string;
  confidence: number;
}

export interface AIMatchCandidate {
  request_id: string;
  ngo_id: string;
  ngo_name: string;
  request_title: string;
  model_version?: string | null;
  fit_percentage: number;
  confidence_percentage: number;
  distance_km: number;
  eta_minutes: number;
  time_left_hours: number;
  feasible: boolean;
  feasibility_reason: string;
  food_category: string;
  category_confidence?: number | null;
  confidence_bucket?: string | null;
  category_uncertain: boolean;
  uncertainty_reason?: string | null;
  top_categories: CategoryPrediction[];
  visual_label: string | null;
  visual_confidence: number | null;
  time_based_status: FreshnessStatus;
  final_status: FreshnessStatus;
  reasons: string[];
  explanation: string;
  breakdown: AIFactorBreakdown;
}

export interface AIMatchResponse {
  donation_id: string;
  best_match: AIMatchCandidate | null;
  matches: AIMatchCandidate[];
}

export interface ExpiryPredictionRequest {
  food_type: string;
  food_category?: string;
  prepared_time: string;
  current_time?: string;
  storage_condition: string;
  quantity: number;
  image_label?: ImageFreshnessLabel;
  visual_label?: string;
  visual_confidence?: number;
  category_confidence?: number;
  confidence_bucket?: string;
  category_uncertain?: boolean;
  uncertainty_reason?: string;
  top_categories?: CategoryPrediction[];
  model_version?: string;
  debug?: boolean;
  shelf_life_hours?: number;
}

export interface ExpiryPredictionResponse {
  model_version?: string | null;
  food_category: string;
  category_confidence?: number | null;
  confidence_bucket?: string | null;
  category_uncertain: boolean;
  uncertainty_reason?: string | null;
  top_categories: CategoryPrediction[];
  shelf_life_hours: number;
  time_elapsed_hours: number;
  time_left_hours: number;
  safe_until: string;
  visual_label: string | null;
  visual_confidence: number | null;
  urgency_status: string;
  time_based_status: FreshnessStatus;
  final_status: FreshnessStatus;
  recommended_action: string;
  explanation: string;
  debug_summary?: string | null;
}

export interface RouteStop {
  request_id: string;
  ngo_id: string;
  ngo_name: string;
  area: string;
  distance_km: number;
  eta_minutes_from_previous: number;
  cumulative_eta_minutes: number;
  priority_label: string;
  time_left_hours: number;
  feasible: boolean;
  feasibility_reason: string;
}

export interface RouteOptimizationRequest {
  donation_id: string;
  request_ids?: string[];
}

export interface RouteOptimizationResponse {
  donation_id: string;
  total_distance_km: number;
  total_eta_minutes: number;
  summary: string;
  stops: RouteStop[];
}

export interface AreaInsight {
  area: string;
  request_count: number;
  urgency_score: number;
  explanation: string;
}

export interface ActorInsight {
  actor_id: string;
  actor_name: string;
  metric_value: number;
  explanation: string;
}

export interface AIImpactSummaryResponse {
  snapshot_at: string;
  meals_saved_this_week: number;
  waste_reduced_kg: number;
  co2_saved_kg: number;
  expected_meals_next_week: number;
  weekly_growth_pct: number;
  high_need_zones: AreaInsight[];
  top_donor: ActorInsight | null;
  top_ngo: ActorInsight | null;
  explanation: string[];
}

export interface ImpactForecastPoint {
  label: string;
  predicted_meals_saved: number;
  predicted_waste_reduced_kg: number;
  predicted_open_requests: number;
}

export interface AIImpactForecastResponse {
  snapshot_at: string;
  trend_direction: string;
  confidence_percentage: number;
  projected_meals_saved_next_week: number;
  projected_waste_reduced_kg_next_week: number;
  high_need_zones: AreaInsight[];
  forecast: ImpactForecastPoint[];
  explanation: string;
}

export interface AIAssistantRequest {
  question: string;
}

export interface AIAssistantResponse {
  answer: string;
  bullet_points: string[];
  follow_up_prompts: string[];
  cited_entity_ids: string[];
}

export interface FoodImageAnalysisResponse {
  model_version: string;
  food_type_guess: string;
  food_category: string;
  category_confidence: number;
  confidence_bucket: string;
  category_uncertain: boolean;
  uncertainty_reason?: string | null;
  top_categories: CategoryPrediction[];
  visual_label: string;
  visual_confidence: number;
  image_label: ImageFreshnessLabel;
  quantity_estimate: string;
  packaging_quality: string;
  model_key: string;
  suggested_storage: string;
  distribution_urgency: string;
  explanation: string;
  debug_summary?: string | null;
}

export interface ModelInfoResponse {
  model_version: string;
  trained_at: string;
  num_classes: number;
  class_names: string[];
  model_path: string;
  class_map_path: string;
}

export interface WasteRiskResponse {
  donation_id: string;
  risk_score: number;
  risk_label: "low" | "medium" | "high";
  final_status: FreshnessStatus;
  top_reasons: string[];
  recommended_action: string;
  safe_hours_remaining: number;
  best_match_fit: number;
}

export interface AdminOverview {
  snapshot_at: string;
  donor_count: number;
  ngo_count: number;
  donation_count: number;
  open_request_count: number;
  reserved_donation_count: number;
  expiring_donations: Donation[];
  notifications: Notification[];
  top_matches: MatchCandidate[];
  impact: ImpactMetrics;
}

export interface DashboardBundle {
  donors: Donor[];
  ngos: NGO[];
  donations: Donation[];
  requests: AidRequest[];
  impact: ImpactMetrics;
  admin: AdminOverview;
}

export interface DonationCreatePayload {
  donor_id: string;
  title: string;
  category: string;
  food_type: string;
  prepared_time: string;
  storage_condition: string;
  quantity: number;
  unit: string;
  meals_estimate: number;
  safety_window_hours: number;
  shelf_life_hours?: number;
  image_url?: string;
  image_freshness_label?: ImageFreshnessLabel;
  image_visual_label?: string;
  image_visual_confidence?: number;
  expires_at?: string;
  pickup_start: string;
  pickup_end: string;
  location: Location;
  notes: string;
}

export interface DonationRequestPayload {
  donation_id: string;
  ngo_id: string;
}

export interface MealRequestCreatePayload {
  ngo_id: string;
  title: string;
  category: string;
  quantity_needed: number;
  unit: string;
  people_served: number;
  priority: number;
  needed_by: string;
  max_distance_km: number;
  location: Location;
  meal_slot: MealSlot;
  notes: string;
}

export interface RequestApprovalPayload {
  donation_id?: string;
}

export interface AuthCredentials {
  email: string;
  password: string;
  role: UserRole;
}

export interface AuthUser {
  id: string;
  email: string;
  role: UserRole;
  profile_id: string | null;
}

export interface AuthSession {
  token: string;
  user: AuthUser;
}
