import sqlite3
from pathlib import Path
import json
import logging

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "localslate.db"

def get_db_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # incidents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        incident_id TEXT PRIMARY KEY,
        iso_timestamp TEXT NOT NULL,
        computed_priority_level TEXT NOT NULL,
        system_summary TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # identified_locations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS identified_locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT NOT NULL,
        location_name TEXT NOT NULL,
        FOREIGN KEY(incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE
    );
    """)
    
    # identified_personnel table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS identified_personnel (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT NOT NULL,
        personnel_name TEXT NOT NULL,
        FOREIGN KEY(incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE
    );
    """)
    
    # actionable_tasks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS actionable_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        incident_id TEXT NOT NULL,
        task_desc TEXT NOT NULL,
        urgency TEXT NOT NULL,
        FOREIGN KEY(incident_id) REFERENCES incidents(incident_id) ON DELETE CASCADE
    );
    """)
    
    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_priority ON incidents(computed_priority_level);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_timestamp ON incidents(iso_timestamp);")
    
    conn.commit()
    conn.close()
    logging.info("Database initialized successfully.")

def insert_incident(data: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION;")
        
        # Insert incident
        cursor.execute("""
        INSERT INTO incidents (incident_id, iso_timestamp, computed_priority_level, system_summary)
        VALUES (?, ?, ?, ?);
        """, (
            data["incident_id"],
            data["iso_timestamp"],
            data["computed_priority_level"],
            data["system_summary"]
        ))
        
        # Insert locations
        entities = data.get("identified_entities", {})
        locations = entities.get("locations", [])
        for loc in locations:
            cursor.execute("""
            INSERT INTO identified_locations (incident_id, location_name)
            VALUES (?, ?);
            """, (data["incident_id"], loc))
            
        # Insert personnel
        personnel = entities.get("personnel", [])
        for pers in personnel:
            cursor.execute("""
            INSERT INTO identified_personnel (incident_id, personnel_name)
            VALUES (?, ?);
            """, (data["incident_id"], pers))
            
        # Insert actionable tasks
        tasks = data.get("actionable_tasks", [])
        for task in tasks:
            cursor.execute("""
            INSERT INTO actionable_tasks (incident_id, task_desc, urgency)
            VALUES (?, ?, ?);
            """, (data["incident_id"], task.get("task_desc", ""), task.get("urgency", "")))
            
        conn.commit()
        logging.info(f"Successfully inserted incident {data['incident_id']} into the database.")
    except Exception as e:
        conn.rollback()
        logging.error(f"Error inserting incident {data.get('incident_id', 'unknown')}: {e}")
        raise e
    finally:
        conn.close()

def get_latest_incidents(limit=5):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT incident_id, iso_timestamp, computed_priority_level, system_summary, created_at
        FROM incidents
        ORDER BY created_at DESC
        LIMIT ?;
        """, (limit,))
        rows = cursor.fetchall()
        incidents = []
        for row in rows:
            inc_id = row[0]
            
            # Fetch locations
            cursor.execute("SELECT location_name FROM identified_locations WHERE incident_id = ?;", (inc_id,))
            locations = [r[0] for r in cursor.fetchall()]
            
            # Fetch personnel
            cursor.execute("SELECT personnel_name FROM identified_personnel WHERE incident_id = ?;", (inc_id,))
            personnel = [r[0] for r in cursor.fetchall()]
            
            # Fetch tasks
            cursor.execute("SELECT task_desc, urgency FROM actionable_tasks WHERE incident_id = ?;", (inc_id,))
            tasks = [{"task_desc": r[0], "urgency": r[1]} for r in cursor.fetchall()]
            
            incidents.append({
                "incident_id": inc_id,
                "iso_timestamp": row[1],
                "computed_priority_level": row[2],
                "system_summary": row[3],
                "created_at": row[4],
                "identified_entities": {
                    "locations": locations,
                    "personnel": personnel
                },
                "actionable_tasks": tasks
            })
        return incidents
    except Exception as e:
        logging.error(f"Error retrieving latest incidents: {e}")
        return []
    finally:
        conn.close()
