import os
import logging
from pathlib import Path
from typing import Optional
import pymysql
from dotenv import load_dotenv

from sqlalchemy import (
    create_engine,
    Column,
    String,
    DateTime,
    Integer,
    ForeignKey,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
import datetime
from backend.src.models.models import IncidentReport

# Resolve project root relative to backend/src/database/db.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Backward compatibility defaults
DB_PATH = PROJECT_ROOT / "data" / "localslate.db"


class Base(DeclarativeBase):
    pass


class Incident(Base):
    __tablename__ = "incidents"

    incident_id = Column(String(255), primary_key=True)
    iso_timestamp = Column(String(255), nullable=False)
    computed_priority_level = Column(String(50), nullable=False)
    system_summary = Column(String(1000), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    locations = relationship(
        "IdentifiedLocation", back_populates="incident", cascade="all, delete-orphan"
    )
    personnel = relationship(
        "IdentifiedPersonnel", back_populates="incident", cascade="all, delete-orphan"
    )
    tasks = relationship(
        "ActionableTask", back_populates="incident", cascade="all, delete-orphan"
    )


class IdentifiedLocation(Base):
    __tablename__ = "identified_locations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(
        String(255),
        ForeignKey("incidents.incident_id", ondelete="CASCADE"),
        nullable=False,
    )
    location_name = Column(String(255), nullable=False)

    incident = relationship("Incident", back_populates="locations")


class IdentifiedPersonnel(Base):
    __tablename__ = "identified_personnel"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(
        String(255),
        ForeignKey("incidents.incident_id", ondelete="CASCADE"),
        nullable=False,
    )
    personnel_name = Column(String(255), nullable=False)

    incident = relationship("Incident", back_populates="personnel")


class ActionableTask(Base):
    __tablename__ = "actionable_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(
        String(255),
        ForeignKey("incidents.incident_id", ondelete="CASCADE"),
        nullable=False,
    )
    task_desc = Column(String(1000), nullable=False)
    urgency = Column(String(50), nullable=False)

    incident = relationship("Incident", back_populates="tasks")


class DatabaseService:
    def __init__(self, db_path: Optional[Path] = None):
        # db_path parameter is kept for backward compatibility but ignored
        self.db_type = os.getenv("DB_TYPE", "sqlite").lower()
        self.host = os.getenv("DB_HOST", "127.0.0.1")
        self.port = os.getenv("DB_PORT", "3306")
        self.user = os.getenv("DB_USER", "root")
        self.password = os.getenv("DB_PASSWORD", "root")
        self.db_name = os.getenv("DB_NAME", "localslate")

        if self.db_type == "mysql":
            self.db_url = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}"
            try:
                self.engine = create_engine(
                    self.db_url,
                    pool_size=10,
                    max_overflow=20,
                    pool_recycle=3600,
                    pool_pre_ping=True,
                )
                self.SessionLocal = sessionmaker(
                    autocommit=False, autoflush=False, bind=self.engine
                )
            except Exception as e:
                logging.error(
                    f"Failed to construct MySQL engine: {e}. Falling back to SQLite."
                )
                self.db_type = "sqlite"
                self.setup_sqlite()
        else:
            self.setup_sqlite()

        self.initialize()

    def setup_sqlite(self) -> None:
        db_dir = PROJECT_ROOT / "data"
        db_dir.mkdir(parents=True, exist_ok=True)
        sqlite_db_path = db_dir / f"{self.db_name}.db"
        self.db_url = f"sqlite:///{sqlite_db_path}"
        self.engine = create_engine(self.db_url, connect_args={"timeout": 30.0})
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # Enable WAL mode and configure cache size for SQLite concurrency
        from sqlalchemy import event

        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA synchronous=NORMAL;")
            except Exception as e:
                logging.warning(
                    f"Failed to set SQLite PRAGMA journal_mode/synchronous: {e}"
                )
            finally:
                cursor.close()

    def create_database_if_not_exists(self) -> None:
        try:
            conn = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                port=int(self.port),
            )
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.db_name};")
            conn.commit()
            cursor.close()
            conn.close()
            logging.info(f"Database '{self.db_name}' checked/created successfully.")
        except Exception as e:
            logging.error(f"Failed to create database '{self.db_name}': {e}")
            raise

    def initialize(self) -> None:
        if self.db_type == "mysql":
            try:
                self.create_database_if_not_exists()
                Base.metadata.create_all(bind=self.engine)
                logging.info("MySQL database initialized successfully with SQLAlchemy.")
                return
            except Exception as e:
                logging.error(
                    f"Failed to initialize MySQL database: {e}. Falling back to SQLite."
                )
                self.db_type = "sqlite"
                self.setup_sqlite()

        try:
            Base.metadata.create_all(bind=self.engine)
            logging.info(
                f"SQLite database '{self.db_name}' initialized successfully at {self.db_url}"
            )
        except Exception as e:
            logging.error(f"Failed to initialize SQLite database: {e}")
            raise

    def get_connection(self):
        # Health check expects a closeable connection object
        try:
            return self.engine.raw_connection()
        except Exception as e:
            logging.error(f"Failed to get database connection: {e}")
            raise

    def insert_incident(self, json_data: dict) -> None:
        try:
            incident = IncidentReport(**json_data)
        except Exception as e:
            raise ValueError(f"Failed to validate JSON data against schema: {e}")

        db = self.SessionLocal()
        try:
            db.begin()

            db_incident = Incident(
                incident_id=incident.incident_id,
                iso_timestamp=incident.iso_timestamp,
                computed_priority_level=incident.computed_priority_level,
                system_summary=incident.system_summary,
            )

            for loc in incident.identified_entities.locations:
                db_incident.locations.append(IdentifiedLocation(location_name=loc))

            for pers in incident.identified_entities.personnel:
                db_incident.personnel.append(IdentifiedPersonnel(personnel_name=pers))

            for task in incident.actionable_tasks:
                db_incident.tasks.append(
                    ActionableTask(task_desc=task.task_desc, urgency=task.urgency)
                )

            db.add(db_incident)
            db.commit()
            logging.info(
                f"Incident {incident.incident_id} successfully saved to MySQL."
            )
        except Exception as e:
            db.rollback()
            logging.error(f"Transaction rolled back due to error: {e}")
            raise
        finally:
            db.close()

    def get_latest_incidents(self, limit: int = 5) -> list:
        db = self.SessionLocal()
        try:
            results = (
                db.query(Incident)
                .order_by(Incident.created_at.desc())
                .limit(limit)
                .all()
            )
            incidents = []
            for inc in results:
                created_str = (
                    inc.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if inc.created_at
                    else ""
                )
                incidents.append(
                    {
                        "incident_id": inc.incident_id,
                        "iso_timestamp": inc.iso_timestamp,
                        "computed_priority_level": inc.computed_priority_level,
                        "system_summary": inc.system_summary,
                        "created_at": created_str,
                        "identified_entities": {
                            "locations": [loc.location_name for loc in inc.locations],
                            "personnel": [
                                pers.personnel_name for pers in inc.personnel
                            ],
                        },
                        "actionable_tasks": [
                            {"task_desc": task.task_desc, "urgency": task.urgency}
                            for task in inc.tasks
                        ],
                    }
                )
            return incidents
        except Exception as e:
            logging.error(f"Failed to fetch latest incidents: {e}")
            return []
        finally:
            db.close()

    def get_db_stats(self) -> dict:
        db = self.SessionLocal()
        stats = {
            "total": 0,
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
        }
        try:
            stats["total"] = db.query(Incident).count()
            group_counts = (
                db.query(
                    Incident.computed_priority_level, func.count(Incident.incident_id)
                )
                .group_by(Incident.computed_priority_level)
                .all()
            )
            for priority, count in group_counts:
                if priority in stats:
                    stats[priority] = count
        except Exception as e:
            logging.error(f"Failed to get database stats: {e}")
        finally:
            db.close()
        return stats

    def clear_db(self) -> None:
        db = self.SessionLocal()
        try:
            db.begin()
            db.query(ActionableTask).delete()
            db.query(IdentifiedLocation).delete()
            db.query(IdentifiedPersonnel).delete()
            db.query(Incident).delete()
            db.commit()
            logging.info("MySQL database cleared successfully.")
        except Exception as e:
            db.rollback()
            logging.error(f"Failed to clear database, rollback executed: {e}")
            raise
        finally:
            db.close()


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
