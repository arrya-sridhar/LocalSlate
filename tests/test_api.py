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


def test_process_text_flow():
    # Submit unstructured text to POST /process
    payload = {
        "text": "Water leak detected in room b by Agent K. Warning: cooling array is down. Urgent evacuation needed."
    }
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


def test_gachibowli_accident_flow():
    # Submit unstructured accident text to POST /process
    text = "Accident report: A severe bike crash occurred at Gachibowli Flyover. Ramesh and Suresh are injured. Traffic is blocked on the flyover. Ambulance and police are required immediately."
    payload = {"text": text}
    response = client.post("/process", json=payload)
    assert response.status_code == 200
    report = response.json()
    assert "incident_id" in report

    # Assert correct extraction of severity/priority
    assert report["computed_priority_level"] == "CRITICAL"

    # Assert correct extraction of location
    assert "Gachibowli Flyover" in report["identified_entities"]["locations"]

    # Assert correct extraction of injured people
    assert "Ramesh" in report["identified_entities"]["personnel"]
    assert "Suresh" in report["identified_entities"]["personnel"]

    # Assert actionable tasks (blocked traffic & emergency services)
    tasks = report["actionable_tasks"]
    task_descs = [t["task_desc"] for t in tasks]

    # Check blocked traffic task
    assert any(
        "Clear blocked traffic" in desc and "Gachibowli Flyover" in desc
        for desc in task_descs
    )

    # Check required emergency services tasks
    assert any("medical services" in desc or "ambulance" in desc for desc in task_descs)
    assert any("police" in desc for desc in task_descs)

    # Retrieve incidents using GET /incidents to ensure it's saved in MySQL
    get_response = client.get("/incidents")
    assert get_response.status_code == 200
    incidents = get_response.json()
    assert len(incidents) == 1
    saved_incident = incidents[0]
    assert saved_incident["incident_id"] == report["incident_id"]
    assert "Gachibowli Flyover" in saved_incident["identified_entities"]["locations"]
    assert "Ramesh" in saved_incident["identified_entities"]["personnel"]
    assert "Suresh" in saved_incident["identified_entities"]["personnel"]


def test_building_a_fire_flow():
    # Submit unstructured fire text to POST /process
    text = "A fire broke out in the chemical storage room of Building A at 3:15 PM. Two workers are trapped inside. Smoke is spreading rapidly."
    payload = {"text": text}
    response = client.post("/process", json=payload)
    assert response.status_code == 200
    report = response.json()
    assert "incident_id" in report

    # Assert correct extraction of severity/priority
    assert report["computed_priority_level"] == "CRITICAL"

    # Assert correct extraction of location
    assert (
        "Building A - Chemical Storage Room"
        in report["identified_entities"]["locations"]
    )

    # Assert correct extraction of trapped people
    assert "two workers" in report["identified_entities"]["personnel"]

    # Assert actionable tasks (fire hazard, rescue, ambulance/medical, evacuation)
    tasks = report["actionable_tasks"]
    task_descs = [t["task_desc"] for t in tasks]

    assert any(
        "fire department" in desc and "Building A - Chemical Storage Room" in desc
        for desc in task_descs
    )
    assert any("Rescue two trapped workers" in desc for desc in task_descs)
    assert any("medical services" in desc or "ambulance" in desc for desc in task_descs)
    assert any(
        "Evacuate nearby area" in desc and "Building A - Chemical Storage Room" in desc
        for desc in task_descs
    )

    # Retrieve incidents using GET /incidents to ensure it's saved in MySQL
    get_response = client.get("/incidents")
    assert get_response.status_code == 200
    incidents = get_response.json()
    assert len(incidents) == 1
    saved_incident = incidents[0]
    assert saved_incident["incident_id"] == report["incident_id"]
    assert (
        "Building A - Chemical Storage Room"
        in saved_incident["identified_entities"]["locations"]
    )
    assert "two workers" in saved_incident["identified_entities"]["personnel"]


def test_water_leakage_exact_sentence_flow():
    # Submit unstructured text to POST /process
    text = "A water pipe burst in Server Room B. Water is reaching electrical equipment and cooling system is down."
    payload = {"text": text}
    response = client.post("/process", json=payload)
    assert response.status_code == 200
    report = response.json()
    assert "incident_id" in report

    # Assert correct extraction of severity/priority
    assert report["computed_priority_level"] == "HIGH"

    # Assert extra rule-based fields
    assert report["incident_type"] == "Water Leakage"
    assert report["location"] == "Server Room B"
    assert report["affected_systems"] == ["Electrical Equipment", "Cooling System"]

    # Assert actionable tasks (order matches exactly: Shut off water supply, Isolate electrical equipment, Repair burst pipe, Restore cooling system)
    tasks = report["actionable_tasks"]
    task_descs = [t["task_desc"] for t in tasks]
    assert task_descs == [
        "Shut off water supply",
        "Isolate electrical equipment",
        "Repair burst pipe",
        "Restore cooling system",
    ]

    # Assert tasks urgency is HIGH
    for t in tasks:
        assert t["urgency"] == "HIGH"

    # Retrieve incidents using GET /incidents to ensure it's saved in MySQL
    get_response = client.get("/incidents")
    assert get_response.status_code == 200
    incidents = get_response.json()
    assert len(incidents) == 1
    saved_incident = incidents[0]
    assert saved_incident["incident_id"] == report["incident_id"]
    assert saved_incident["incident_type"] == "Water Leakage"
    assert saved_incident["location"] == "Server Room B"
    assert saved_incident["affected_systems"] == [
        "Electrical Equipment",
        "Cooling System",
    ]


def test_disconnected_database_fallback(monkeypatch):
    # Simulate Render deployment where DB is missing/empty
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("DB_HOST", "")

    # Reset singletons to force DB service recreation in disconnected mode
    import backend.src.database.db as db_mod

    db_mod._global_db_service = None

    # Test /health endpoint (must always return 200 OK)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is False
    assert response.json()["database"] == "error"

    # Test /db-health endpoint
    response = client.get("/db-health")
    assert response.status_code == 200
    assert response.json()["connected"] is False

    # Test /status endpoint (must not fail!)
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert "is_running" in data
    assert "db_stats" in data
    assert data["db_stats"]["total"] == 0

    # Test /incidents endpoint (returns clear 503 error)
    response = client.get("/incidents")
    assert response.status_code == 503
    assert "error" in response.json()

    # Test /process endpoint (returns clear 503 error)
    payload = {"text": "Simple test incident note."}
    response = client.post("/process", json=payload)
    assert response.status_code == 503
    assert "error" in response.json()
