from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_get_status():
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert "is_running" in data
    assert "queue_count" in data


def test_get_incidents():
    response = client.get("/incidents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
