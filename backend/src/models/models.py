import datetime
import uuid
from typing import List, Literal
from pydantic import BaseModel, Field


class Task(BaseModel):
    task_desc: str = Field(..., description="Actionable task description")
    urgency: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        ..., description="Urgency of task"
    )


class Entities(BaseModel):
    locations: List[str] = Field(
        default_factory=list, description="List of identified locations"
    )
    personnel: List[str] = Field(
        default_factory=list, description="List of identified personnel"
    )


class IncidentReport(BaseModel):
    incident_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    iso_timestamp: str = Field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )
    computed_priority_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    system_summary: str = Field(
        ..., description="Brief 2-sentence summary of the incident"
    )
    identified_entities: Entities
    actionable_tasks: List[Task] = Field(default_factory=list)
