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


def test_process_text_flow(tmp_path, monkeypatch):
    test_db = tmp_path / "test_localslate.db"
    
    import backend.src.database.db as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", test_db)
    
    # Reset the global db service so it re-initializes with the test database path
    db_mod._global_db_service = None
    db_mod.init_db()

    # Clear database
    response = client.delete("/incidents")
    assert response.status_code == 200

    # Submit unstructured text to POST /process
    payload = {"text": "Water leak detected in room b by Agent K. Warning: cooling array is down. Urgent evacuation needed."}
    response = client.post("/process", json=payload)
    assert response.status_code == 200
    report = response.json()
    assert "incident_id" in report
    assert report["computed_priority_level"] == "HIGH"
    
    # Retrieve incidents using GET /incidents
    get_response = client.get("/incidents")
    assert get_response.status_code == 200
    incidents = get_response.json()
    assert len(incidents) == 1
    assert incidents[0]["incident_id"] == report["incident_id"]
    assert "Room B" in incidents[0]["identified_entities"]["locations"]
    assert "Cooling Array" in incidents[0]["identified_entities"]["locations"]
    assert "Agent K" in incidents[0]["identified_entities"]["personnel"]


