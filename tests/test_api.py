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


def test_process_audio_flow(monkeypatch):
    # Reset singletons to force DB service recreation with normal settings
    import backend.src.database.db as db_mod

    db_mod._global_db_service = None

    import io

    dummy_wav = io.BytesIO(
        b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80\x3e\x00\x00\x00\x7d\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    )
    files = {"file": ("recorded_mic.wav", dummy_wav, "audio/wav")}

    response = client.post("/process-audio", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "transcript" in data
    assert "report" in data
    assert data["saved"] is True

    # Assert expected water leakage content
    assert "water pipe burst" in data["transcript"].lower()
    report = data["report"]
    assert report["computed_priority_level"] == "HIGH"
    assert report["incident_type"] == "Water Leakage"
    assert report["location"] == "Server Room B"
    assert "Electrical Equipment" in report["affected_systems"]

    # Verify stored in DB
    get_response = client.get("/incidents")
    assert get_response.status_code == 200
    incidents = get_response.json()
    assert len(incidents) > 0
    saved = incidents[0]
    assert saved["incident_type"] == "Water Leakage"
    assert saved["location"] == "Server Room B"


def test_database_schema_migration():
    from sqlalchemy import create_engine, MetaData, Table, Column, String, inspect

    engine = create_engine("sqlite:///:memory:")

    # Define incidents table with missing columns
    metadata = MetaData()
    Table(
        "incidents",
        metadata,
        Column("incident_id", String(36), primary_key=True),
        Column("system_summary", String(1000)),
    )
    metadata.create_all(bind=engine)

    # Verify they don't exist initially
    inspector = inspect(engine)
    cols = [c["name"] for c in inspector.get_columns("incidents")]
    assert "incident_type" not in cols
    assert "location" not in cols
    assert "affected_systems" not in cols

    import backend.src.database.db as db_mod

    service = db_mod.DatabaseService()
    service.engine = engine
    service.host = "dummy"

    # Run the schema migration check
    service.run_schema_migrations()

    # Verify columns were added successfully
    inspector = inspect(engine)
    cols = [c["name"] for c in inspector.get_columns("incidents")]
    assert "incident_type" in cols
    assert "location" in cols
    assert "affected_systems" in cols


def test_incident_classification_regression():
    from backend.src.engine.slm_processor import mock_extraction

    # 1. Medical Emergencies
    med_text = "A patient is suffering from cardiac arrest at the Main Lobby. Ramesh is administering CPR."
    med_res = mock_extraction(med_text)
    assert med_res["incident_type"] == "Medical Emergency"
    assert med_res["location"] == "Main Lobby"
    assert "Human Health" in med_res["affected_systems"]
    assert any("CPR" in t["task_desc"] for t in med_res["actionable_tasks"])

    # 2. Road Accidents
    road_text = "Multi-car collision on the Gachibowli Flyover blocking all lanes. Traffic is backed up."
    road_res = mock_extraction(road_text)
    assert road_res["incident_type"] == "Road Accident"
    assert road_res["location"] == "Gachibowli Flyover"
    assert "Road Network" in road_res["affected_systems"]
    assert any(
        "traffic" in t["task_desc"].lower() for t in road_res["actionable_tasks"]
    )

    # 3. Gas Leaks
    gas_text = (
        "Natural gas leak detected in the Cafeteria kitchen. Methane levels rising."
    )
    gas_res = mock_extraction(gas_text)
    assert gas_res["incident_type"] == "Gas Leak"
    assert gas_res["location"] == "Cafeteria"
    assert "HVAC" in gas_res["affected_systems"]
    assert any("gas" in t["task_desc"].lower() for t in gas_res["actionable_tasks"])

    # 4. Chemical Spills
    chem_text = "Toxic acid spill in Building A - Chemical Storage Room. Hazardous fumes detected."
    chem_res = mock_extraction(chem_text)
    assert chem_res["incident_type"] == "Chemical Spill"
    assert chem_res["location"] == "Building A - Chemical Storage Room"
    assert "Ventilation System" in chem_res["affected_systems"]
    assert any(
        "chemical" in t["task_desc"].lower() for t in chem_res["actionable_tasks"]
    )

    # 5. Floods
    flood_text = "Flooding at the Basement Parking. Water level rising fast."
    flood_res = mock_extraction(flood_text)
    assert flood_res["incident_type"] == "Flood"
    assert flood_res["location"] == "Basement Parking"
    assert "Drainage System" in flood_res["affected_systems"]
    assert any(
        "water pumps" in t["task_desc"].lower() for t in flood_res["actionable_tasks"]
    )

    # 6. Earthquakes
    quake_text = "Earthquake tremor caused structural collapse in Sector 4. Trapped people reported."
    quake_res = mock_extraction(quake_text)
    assert quake_res["incident_type"] == "Earthquake"
    assert quake_res["location"] == "Sector 4"
    assert "Structural Integrity" in quake_res["affected_systems"]
    assert any(
        "trapped" in t["task_desc"].lower() for t in quake_res["actionable_tasks"]
    )

    # 7. Cyber Incidents
    cyber_text = (
        "Ransomware cyber attack detected on the Main Database. Systems encrypted."
    )
    cyber_res = mock_extraction(cyber_text)
    assert cyber_res["incident_type"] == "Cyber Incident"
    assert cyber_res["location"] == "Main Database"
    assert "Main Database" in cyber_res["affected_systems"]
    assert any(
        "cybersecurity" in t["task_desc"].lower() or "isolate" in t["task_desc"].lower()
        for t in cyber_res["actionable_tasks"]
    )

    # 8. Suspicious Packages
    pkg_text = "Unattended suspicious bag found at the Entrance Gate. Potential explosive device."
    pkg_res = mock_extraction(pkg_text)
    assert pkg_res["incident_type"] == "Suspicious Package"
    assert pkg_res["location"] == "Entrance Gate"
    assert "Physical Security" in pkg_res["affected_systems"]
    assert any(
        "bomb squad" in t["task_desc"].lower() for t in pkg_res["actionable_tasks"]
    )

    # 9. Power Failures
    power_text = "Total blackout power outage in Building B. Generator failed to start."
    power_res = mock_extraction(power_text)
    assert power_res["incident_type"] == "Power Failure"
    assert power_res["location"] == "Building B"
    assert "Electrical Grid" in power_res["affected_systems"]
    assert any(
        "outage" in t["task_desc"].lower() or "power" in t["task_desc"].lower()
        for t in power_res["actionable_tasks"]
    )
