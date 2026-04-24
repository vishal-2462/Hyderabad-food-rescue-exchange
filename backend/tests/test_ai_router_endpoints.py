from fastapi.testclient import TestClient

from app.main import create_app
from app.store import reset_store


def test_ai_router_exposes_demo_ready_endpoints() -> None:
    reset_store()
    client = TestClient(create_app())

    match_response = client.get("/ai/match/donation-banjara-lunch")
    assert match_response.status_code == 200
    assert match_response.json()["matches"]
    assert "feasible" in match_response.json()["matches"][0]
    assert "top_categories" in match_response.json()["matches"][0]

    model_info = client.get("/ai/model-info")
    assert model_info.status_code == 200
    assert model_info.json()["model_version"]
    assert model_info.json()["class_names"]

    expiry_response = client.post(
        "/ai/analyze-freshness",
        json={
            "food_type": "biryani",
            "prepared_time": "2026-04-18T08:00:00Z",
            "storage_condition": "ambient",
            "quantity": 40,
            "image_label": "good",
        },
    )
    assert expiry_response.status_code == 200
    assert expiry_response.json()["final_status"] in {"safe", "urgent", "unsafe"}
    assert "food_category" in expiry_response.json()

    route_response = client.post("/ai/optimize-route", json={"donation_id": "donation-banjara-lunch"})
    assert route_response.status_code == 200
    assert route_response.json()["total_eta_minutes"] >= 0

    summary_response = client.get("/ai/impact-summary")
    assert summary_response.status_code == 200
    assert "expected_meals_next_week" in summary_response.json()

    forecast_response = client.get("/ai/impact-forecast")
    assert forecast_response.status_code == 200
    assert forecast_response.json()["forecast"]

    assistant_response = client.post("/ai/assistant", json={"question": "Which donation should be prioritized today?"})
    assert assistant_response.status_code == 200
    assert assistant_response.json()["answer"]

    image_response = client.post(
        "/ai/analyze-food-image",
        files={"file": ("meal-tray.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    assert image_response.status_code == 200
    assert image_response.json()["food_type_guess"]
    assert image_response.json()["food_category"]
    assert image_response.json()["visual_label"]
    assert image_response.json()["top_categories"]
    assert image_response.json()["model_version"]
    assert image_response.json()["image_label"] in {"good", "medium", "spoiled"}

    risk_response = client.get("/ai/waste-risk/donation-banjara-lunch")
    assert risk_response.status_code == 200
    assert risk_response.json()["risk_label"] in {"low", "medium", "high"}
