from fastapi.testclient import TestClient

from backend.app import main


def test_metrics_requires_configured_api_token(monkeypatch):
    monkeypatch.setattr(main.settings, "api_auth_token", "test-metrics-token")
    client = TestClient(main.app)

    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"Authorization": "Bearer wrong"}).status_code == 401

    response = client.get("/metrics", headers={"Authorization": "Bearer test-metrics-token"})
    assert response.status_code == 200
    assert "agent_requests_total" in response.text


def test_x_api_key_remains_supported(monkeypatch):
    monkeypatch.setattr(main.settings, "api_auth_token", "test-api-token")
    client = TestClient(main.app)

    response = client.get("/metrics", headers={"X-API-Key": "test-api-token"})
    assert response.status_code == 200

