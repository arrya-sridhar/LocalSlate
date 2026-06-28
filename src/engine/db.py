import os
import uuid
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field

# Determine project root and DB path dynamically to ensure environment parity
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "antigravity.db"

class ActionableTask(BaseModel):
    task_desc: str
    urgency: str

class IdentifiedEntities(BaseModel):
    locations: list[str] = Field(default_factory=list)
    personnel: list[str] = Field(default_factory=list)

class IncidentReport(BaseModel):
    incident_id: str
    iso_timestamp: str
    computed_priority_level: str
    system_summary: str
    identified_entities: IdentifiedEntities
    actionable_tasks: list[ActionableTask] = Field(default_factory=list)

class DatabaseEngine:
    def __init__(self):
        # Ensure data directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.db_path = DB_PATH
        self.initialize()

    def get_connection(self):
        return sqlite3.connect(str(self.db_path))

    def initialize(self):
        """Executes DDL statements to create tables if they do not exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    iso_timestamp TEXT NOT NULL,
                    computed_priority_level TEXT NOT NULL,
                    system_summary TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS identified_locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL,
                    location_name TEXT NOT NULL,
                    FOREIGN KEY(incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS identified_personnel (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL,
                    personnel_name TEXT NOT NULL,
                    FOREIGN KEY(incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS actionable_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL,
                    task_desc TEXT NOT NULL,
                    urgency TEXT NOT NULL,
                    FOREIGN KEY(incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE
                );

                -- Optimization indexes for local querying
                CREATE INDEX IF NOT EXISTS idx_incidents_priority ON incidents(computed_priority_level);
                CREATE INDEX IF NOT EXISTS idx_incidents_timestamp ON incidents(iso_timestamp);
            """)
            conn.commit()

    def insert_incident(self, json_data: dict):
        """Inserts a validated JSON dictionary into the normalized SQLite schema."""
        try:
            # Validate using Pydantic
            incident = IncidentReport(**json_data)
        except Exception as e:
            raise ValueError(f"Failed to validate JSON data against schema: {e}")

        with self.get_connection() as conn:
            # Enable foreign key support in sqlite
            conn.execute("PRAGMA foreign_keys = ON;")
            cursor = conn.cursor()
            
            # Insert root incident
            cursor.execute(
                "INSERT INTO incidents (incident_id, iso_timestamp, computed_priority_level, system_summary) VALUES (?, ?, ?, ?)",
                (incident.incident_id, incident.iso_timestamp, incident.computed_priority_level, incident.system_summary)
            )

            # Insert locations
            for loc in incident.identified_entities.locations:
                cursor.execute(
                    "INSERT INTO identified_locations (incident_id, location_name) VALUES (?, ?)",
                    (incident.incident_id, loc)
                )

            # Insert personnel
            for person in incident.identified_entities.personnel:
                cursor.execute(
                    "INSERT INTO identified_personnel (incident_id, personnel_name) VALUES (?, ?)",
                    (incident.incident_id, person)
                )

            # Insert actionable tasks
            for task in incident.actionable_tasks:
                cursor.execute(
                    "INSERT INTO actionable_tasks (incident_id, task_desc, urgency) VALUES (?, ?, ?)",
                    (incident.incident_id, task.task_desc, task.urgency)
                )
            
            conn.commit()
