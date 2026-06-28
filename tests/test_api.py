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
