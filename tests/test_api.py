import os

os.environ["INSTAGRAM_PROVIDER"] = "demo"

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_demo_analysis():
    response = client.get("/api/v1/accounts/who/analysis?limit=3")
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "who"
    assert body["post_count"] == 3
    assert body["top_topics"]


def test_rejects_bad_username():
    response = client.get("/api/v1/accounts/not%20valid/analysis")
    assert response.status_code == 422


def test_research_returns_dataframe_records_without_saving():
    response = client.post("/api/v1/research", json={
        "username": "@who",
        "research_query": "Which health themes are gaining traction?",
        "limit": 2,
        "save_json": False,
    })
    assert response.status_code == 200
    body = response.json()
    assert len(body["records"]) == 2
    assert body["records"][0]["permalink"].startswith("https://www.instagram.com/p/")
    assert body["export_id"] is None


def test_provider_error_is_returned_as_bad_gateway(monkeypatch):
    from app import main
    from app.providers import ProviderError

    monkeypatch.setattr(main, "make_provider", lambda *args: (_ for _ in ()).throw(ProviderError("Login required")))
    response = client.get("/api/v1/accounts/example/analysis?refresh=true")
    assert response.status_code == 502
    assert response.json() == {"detail": "Login required"}


def test_top_engagement_selection():
    response = client.post("/api/v1/research", json={
        "username": "who",
        "limit": 2,
        "selection": "top_engagement",
        "scan_limit": 4,
        "save_json": False,
    })
    assert response.status_code == 200
    body = response.json()["analysis"]
    assert body["selection_method"] == "top_engagement"
    assert body["scanned_post_count"] == 4
    assert [post["engagement"] for post in body["posts"]] == [1298, 1051]
