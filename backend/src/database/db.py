import sqlite3
import logging
from pathlib import Path
from typing import Optional
from backend.src.models.models import IncidentReport

# Resolve project root relative to backend/src/database/db.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "localslate.db"


class DatabaseService:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = DB_PATH
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(
            "PRAGMA journal_mode = WAL;"
        )  # Avoid SQLite locking/concurrency issues
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        try:
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

                    CREATE INDEX IF NOT EXISTS idx_incidents_priority ON incidents(computed_priority_level);
                    CREATE INDEX IF NOT EXISTS idx_incidents_timestamp ON incidents(iso_timestamp);
                """)
                conn.commit()
            logging.info("SQLite database initialized successfully.")
        except Exception as e:
            logging.error(f"Failed to initialize SQLite database: {e}")
            raise

    def insert_incident(self, json_data: dict) -> None:
        try:
            incident = IncidentReport(**json_data)
        except Exception as e:
            raise ValueError(f"Failed to validate JSON data against schema: {e}")

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # Start transaction explicitly
            conn.execute("BEGIN TRANSACTION;")

            cursor.execute(
                "INSERT INTO incidents (incident_id, iso_timestamp, computed_priority_level, system_summary) VALUES (?, ?, ?, ?)",
                (
                    incident.incident_id,
                    incident.iso_timestamp,
                    incident.computed_priority_level,
                    incident.system_summary,
                ),
            )

            for loc in incident.identified_entities.locations:
                cursor.execute(
                    "INSERT INTO identified_locations (incident_id, location_name) VALUES (?, ?)",
                    (incident.incident_id, loc),
                )

            for person in incident.identified_entities.personnel:
                cursor.execute(
                    "INSERT INTO identified_personnel (incident_id, personnel_name) VALUES (?, ?)",
                    (incident.incident_id, person),
                )

            for task in incident.actionable_tasks:
                cursor.execute(
                    "INSERT INTO actionable_tasks (incident_id, task_desc, urgency) VALUES (?, ?, ?)",
                    (incident.incident_id, task.task_desc, task.urgency),
                )

            conn.commit()
            logging.info(
                f"Incident {incident.incident_id} successfully saved to database."
            )
        except Exception as e:
            conn.rollback()
            logging.error(f"Transaction rolled back due to error: {e}")
            raise
        finally:
            conn.close()

    def get_latest_incidents(self, limit: int = 5) -> list:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT incident_id, iso_timestamp, computed_priority_level, system_summary, created_at
                FROM incidents
                ORDER BY created_at DESC
                LIMIT ?;
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            incidents = []
            for row in rows:
                inc_id = row["incident_id"]
                cursor.execute(
                    "SELECT location_name FROM identified_locations WHERE incident_id = ?;",
                    (inc_id,),
                )
                locations = [r["location_name"] for r in cursor.fetchall()]

                cursor.execute(
                    "SELECT personnel_name FROM identified_personnel WHERE incident_id = ?;",
                    (inc_id,),
                )
                personnel = [r["personnel_name"] for r in cursor.fetchall()]

                cursor.execute(
                    "SELECT task_desc, urgency FROM actionable_tasks WHERE incident_id = ?;",
                    (inc_id,),
                )
                tasks = [
                    {"task_desc": r["task_desc"], "urgency": r["urgency"]}
                    for r in cursor.fetchall()
                ]

                incidents.append(
                    {
                        "incident_id": inc_id,
                        "iso_timestamp": row["iso_timestamp"],
                        "computed_priority_level": row["computed_priority_level"],
                        "system_summary": row["system_summary"],
                        "created_at": row["created_at"],
                        "identified_entities": {
                            "locations": locations,
                            "personnel": personnel,
                        },
                        "actionable_tasks": tasks,
                    }
                )
            return incidents
        except Exception as e:
            logging.error(f"Failed to fetch latest incidents: {e}")
            return []
        finally:
            conn.close()

    def get_db_stats(self) -> dict:
        conn = self.get_connection()
        cursor = conn.cursor()
        stats = {
            "total": 0,
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
        }
        try:
            cursor.execute("SELECT COUNT(*) FROM incidents;")
            stats["total"] = cursor.fetchone()[0]

            cursor.execute(
                "SELECT computed_priority_level, COUNT(*) FROM incidents GROUP BY computed_priority_level;"
            )
            for row in cursor.fetchall():
                priority = row["computed_priority_level"]
                count = row[1]
                if priority in stats:
                    stats[priority] = count
        except Exception as e:
            logging.error(f"Failed to get database stats: {e}")
        finally:
            conn.close()
        return stats

    def clear_db(self) -> None:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            conn.execute("BEGIN TRANSACTION;")
            cursor.execute("DELETE FROM identified_locations;")
            cursor.execute("DELETE FROM identified_personnel;")
            cursor.execute("DELETE FROM actionable_tasks;")
            cursor.execute("DELETE FROM incidents;")
            conn.commit()
            logging.info("SQLite database cleared successfully.")
        except Exception as e:
            conn.rollback()
            logging.error(f"Failed to clear database, rollback executed: {e}")
            raise
        finally:
            conn.close()


# Compatibility Legacy Classes and Functions
class DatabaseEngine(DatabaseService):
    pass


_global_db_service = None


def get_db_service() -> DatabaseService:
    global _global_db_service
    if _global_db_service is None:
        _global_db_service = DatabaseService()
    return _global_db_service


def init_db() -> None:
    get_db_service().initialize()


def insert_incident(data: dict) -> None:
    get_db_service().insert_incident(data)


def get_latest_incidents(limit: int = 5) -> list:
    return get_db_service().get_latest_incidents(limit=limit)


def get_db_stats() -> dict:
    return get_db_service().get_db_stats()


def clear_db() -> None:
    get_db_service().clear_db()
