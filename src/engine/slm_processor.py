import os
import json
import logging
from pathlib import Path
import datetime
import uuid
from typing import List, Literal
from pydantic import BaseModel, Field, ValidationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SLM_MODEL_PATH = PROJECT_ROOT / ".models" / "slm" / "phi3-mini-4k.gguf"

# Pydantic Schemas
class Task(BaseModel):
    task_desc: str = Field(..., description="Actionable task description")
    urgency: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(..., description="Urgency of task")

class Entities(BaseModel):
    locations: List[str] = Field(default_factory=list, description="List of identified locations")
    personnel: List[str] = Field(default_factory=list, description="List of identified personnel")

class IncidentReport(BaseModel):
    incident_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    iso_timestamp: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    computed_priority_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    system_summary: str = Field(..., description="Brief 2-sentence summary of the incident")
    identified_entities: Entities
    actionable_tasks: List[Task] = Field(default_factory=list)

def mock_extraction(text: str) -> dict:
    # Simulates Phi-3 extraction with regex/rules
    import time
    time.sleep(1.5) # Simulate CPU inference time
    
    text_lower = text.lower()
    
    # Priority
    priority = "LOW"
    if "critical" in text_lower or "danger" in text_lower:
        priority = "CRITICAL"
    elif "high" in text_lower or "urgent" in text_lower or "leak" in text_lower:
        priority = "HIGH"
    elif "medium" in text_lower or "warning" in text_lower:
        priority = "MEDIUM"
        
    # Locations
    locations = []
    import re
    loc_matches = re.findall(r"(sector\s+\d+|room\s+[a-z]|main\s+node|cooling\s+array)", text_lower)
    for m in loc_matches:
        locations.append(m.title())
    if not locations:
        locations = ["Sector 7"] if "sector 7" in text_lower else ["Unknown Area"]
        
    # Personnel
    personnel = []
    pers_matches = re.findall(r"(agent\s+[a-z]|operative\s+[a-z])", text_lower)
    for m in pers_matches:
        personnel.append(m.title())
    if not personnel:
        personnel = ["Agent K", "Operative J"] if "agent k" in text_lower or "operative j" in text_lower else ["Duty Staff"]
        
    # Tasks
    tasks = []
    if "cooling" in text_lower:
        tasks.append({"task_desc": "Deploy secondary cooling array", "urgency": "CRITICAL"})
    if "leak" in text_lower or "water" in text_lower:
        tasks.append({"task_desc": "Evacuate Server Room B and isolate leak", "urgency": "CRITICAL"})
    if not tasks:
        tasks.append({"task_desc": "Perform routine safety checks", "urgency": "LOW"})
        
    # Summary
    summary = f"Field report detailing operations. Priority: {priority}."
    if len(text) > 10:
        summary = text[:120] + "..." if len(text) > 120 else text
        
    report = {
        "incident_id": str(uuid.uuid4()),
        "iso_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "computed_priority_level": priority,
        "system_summary": summary,
        "identified_entities": {
            "locations": list(set(locations)),
            "personnel": list(set(personnel))
        },
        "actionable_tasks": tasks
    }
    return report

def check_ram_usage():
    try:
        import psutil
        mem = psutil.virtual_memory()
        # If RAM usage is above 3.8 GB
        if mem.used > 3.8 * 1024 * 1024 * 1024 or mem.percent > 95:
            return True
    except ImportError:
        pass
    return False

def structure_text(text: str) -> dict:
    if len(text) > 4000:
        logging.warning("Input text exceeds 4000 characters. Truncating context.")
        text = text[:4000]
        
    if check_ram_usage():
        logging.error("OOM Protection active: System RAM usage is above 3.8GB limit. Aborting inference.")
        raise MemoryError("Inference aborted due to high RAM usage (>3.8GB)")

    if not SLM_MODEL_PATH.exists():
        logging.warning("Phi-3 GGUF model not found. Using mock JSON extraction.")
        report_data = mock_extraction(text)
        # Validate through Pydantic
        report = IncidentReport(**report_data)
        return report.model_dump()
        
    # Real llama-cpp-python execution
    from llama_cpp import Llama
    
    # Prompt with structured JSON guidance
    system_prompt = (
        "You are an intelligence extractor. Read the following field note and output strictly a JSON object "
        "conforming to this schema:\n"
        "{\n"
        "  \"incident_id\": \"string (uuid4)\",\n"
        "  \"iso_timestamp\": \"string (ISO 8601)\",\n"
        "  \"computed_priority_level\": \"LOW | MEDIUM | HIGH | CRITICAL\",\n"
        "  \"system_summary\": \"Brief 2-sentence summary\",\n"
        "  \"identified_entities\": {\n"
        "    \"locations\": [\"string\"],\n"
        "    \"personnel\": [\"string\"]\n"
        "  },\n"
        "  \"actionable_tasks\": [\n"
        "    { \"task_desc\": \"string\", \"urgency\": \"LOW | MEDIUM | HIGH | CRITICAL\" }\n"
        "  ]\n"
        "}\n"
        "Do not include markdown wrappers (e.g. ```json) in your final response. "
        "Output ONLY the JSON object. Do not explain your response."
    )
    
    prompt = f"<|system|>\n{system_prompt}<|end|>\n<|user|>\n{text}<|end|>\n<|assistant|>\n"
    
    for attempt in range(1, 4):
        try:
            logging.info(f"Loading Phi-3 GGUF model from {SLM_MODEL_PATH} (attempt {attempt})...")
            # Limit llama-cpp context window and threads
            llm = Llama(
                model_path=str(SLM_MODEL_PATH),
                n_ctx=2048,
                n_threads=2,
                verbose=False
            )
            
            logging.info("Running llama.cpp inference...")
            response = llm(
                prompt,
                max_tokens=512,
                temperature=0.1,
                stop=["<|end|>"]
            )
            
            output_text = response["choices"][0]["text"].strip()
            
            # Clean output text
            if output_text.startswith("```"):
                output_text = output_text.strip("`").strip()
                if output_text.startswith("json"):
                    output_text = output_text[4:].strip()
                    
            report_data = json.loads(output_text)
            
            # Validate with Pydantic
            report = IncidentReport(**report_data)
            logging.info("Successfully structured and validated text via SLM.")
            return report.model_dump()
            
        except (json.JSONDecodeError, ValidationError) as e:
            logging.warning(f"Inference attempt {attempt} failed to produce valid schema: {e}")
            if attempt == 3:
                logging.error("All 3 SLM inference attempts failed. Gracefully falling back to mock extraction.")
                # Fallback report with partial info
                report_data = mock_extraction(text)
                return IncidentReport(**report_data).model_dump()
        except Exception as e:
            logging.error(f"Llama-cpp inference error: {e}")
            raise e
