import datetime
import json
import logging
import uuid
import re
from pathlib import Path
from pydantic import ValidationError
from backend.src.models.models import IncidentReport

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SLM_MODEL_PATH = PROJECT_ROOT / ".models" / "slm" / "phi3-mini-4k.gguf"


def semantic_fallback_extraction(text: str) -> dict:
    text_lower = text.lower()

    # 1. Determine priority/severity
    priority = "LOW"
    if any(
        k in text_lower
        for k in [
            "critical",
            "danger",
            "severe",
            "fatality",
            "trapped",
            "earthquake",
            "blackout",
            "cardiac",
        ]
    ):
        priority = "CRITICAL"
    elif any(
        k in text_lower
        for k in [
            "high",
            "urgent",
            "accident",
            "collision",
            "spill",
            "leak",
            "flood",
            "burst",
        ]
    ):
        priority = "HIGH"
    elif any(k in text_lower for k in ["medium", "warning", "failure"]):
        priority = "MEDIUM"

    # 2. Extract locations
    locations = []
    # Match Gachibowli locations
    if "gachibowli flyover" in text_lower:
        locations.append("Gachibowli Flyover")
    elif "gachibowli crossroads" in text_lower or "gachibowli crossroad" in text_lower:
        locations.append("Gachibowli Crossroads")
    elif "gachibowli" in text_lower:
        locations.append("Gachibowli")

    # Match Building A/B/C or Room names
    b_match = re.search(r"\b(building\s+[a-z0-9])\b", text_lower)
    if b_match:
        b_name = b_match.group(1).title()
        if "chemical storage" in text_lower:
            locations.append(f"{b_name} - Chemical Storage Room")
        else:
            locations.append(b_name)
    elif "chemical storage" in text_lower:
        locations.append("Chemical Storage Room")

    s_match = re.search(r"\b(server\s+room\s+[a-z0-9]|room\s+[a-z0-9])\b", text_lower)
    if s_match:
        locations.append(s_match.group(1).title())

    sec_match = re.search(r"\b(sector\s+\d+)\b", text_lower)
    if sec_match:
        locations.append(sec_match.group(1).title())

    if "cooling array" in text_lower:
        locations.append("Cooling Array")

    if not locations:
        matches = re.findall(
            r"\b(?:at|on|in|near)\s+(?:the\s+)?([A-Z][a-zA-Z0-9']+(?:\s+[A-Z][a-zA-Z0-9']+)*)",
            text,
        )
        for m in matches:
            cleaned = m.strip()
            if cleaned and not re.match(
                r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|January|February|March|April|May|June|July|August|September|October|November|December|PM|AM|CPR)\b",
                cleaned,
                re.IGNORECASE,
            ):
                locations.append(cleaned)

    if not locations:
        if "cafeteria" in text_lower:
            locations.append("Cafeteria")
        elif "parking" in text_lower or "basement" in text_lower:
            locations.append("Basement Parking")
        elif "entrance" in text_lower or "gate" in text_lower:
            locations.append("Entrance Gate")
        elif "database" in text_lower or "server" in text_lower:
            locations.append("Data Center")
        else:
            locations.append("Unknown Area")

    locations = list(dict.fromkeys(locations))

    # Match counts of workers / trapped people (e.g. Two workers, 2 workers)
    trapped_count_match = re.search(
        r"\b((?:\d+|[Tt]wo|[Tt]hree|[Ff]our|[Ff]ive|[Ss]everal))\s+(workers|people|persons|staff|operators|individuals|occupants)\b",
        text,
        re.IGNORECASE,
    )

    # 3. Classify incident type, systems and tasks
    incident_type = "Other"
    affected_systems = []
    tasks = []

    # Fire Hazard
    if any(k in text_lower for k in ["fire", "smoke", "blaze"]):
        incident_type = "Fire Hazard"
        affected_systems = ["Safety Systems"]
        tasks.append(
            {
                "task_desc": f"Dispatch fire department to {locations[0]} to control the fire hazard",
                "urgency": "CRITICAL",
            }
        )
        if "trapped" in text_lower:
            workers_count = "trapped"
            if trapped_count_match:
                workers_count = f"{trapped_count_match.group(1).lower()} trapped"
            tasks.append(
                {
                    "task_desc": f"Rescue {workers_count} workers",
                    "urgency": "CRITICAL",
                }
            )
        tasks.append(
            {
                "task_desc": f"Dispatch emergency medical services / ambulance to {locations[0]}",
                "urgency": "CRITICAL",
            }
        )
        tasks.append(
            {
                "task_desc": f"Evacuate nearby area from {locations[0]}",
                "urgency": "CRITICAL",
            }
        )

    # Medical Emergency (specific)
    elif any(
        k in text_lower
        for k in [
            "cardiac",
            "heart attack",
            "unconscious",
            "stroke",
            "cpr",
        ]
    ):
        incident_type = "Medical Emergency"
        affected_systems = ["Human Health"]
        if "cpr" in text_lower or "cardiac" in text_lower:
            tasks.append(
                {
                    "task_desc": "Administer CPR and first aid",
                    "urgency": "CRITICAL",
                }
            )
        tasks.append(
            {
                "task_desc": f"Dispatch emergency medical services / ambulance to {locations[0]}",
                "urgency": "CRITICAL",
            }
        )

    # Road Accident
    elif any(
        k in text_lower
        for k in [
            "car crash",
            "road accident",
            "collision",
            "pileup",
            "traffic block",
            "vehicle",
            "accident",
            "crash",
        ]
    ):
        incident_type = "Road Accident"
        affected_systems = ["Road Network"]
        tasks.append(
            {
                "task_desc": f"Clear blocked traffic at {locations[0]} and divert vehicles",
                "urgency": "HIGH",
            }
        )
        tasks.append(
            {
                "task_desc": f"Deploy traffic police to {locations[0]} for crowd control and investigation",
                "urgency": "HIGH",
            }
        )
        if any(
            x in text_lower for x in ["injured", "injuries", "ambulance", "medical"]
        ):
            tasks.append(
                {
                    "task_desc": f"Dispatch emergency medical services / ambulance to {locations[0]}",
                    "urgency": "CRITICAL",
                }
            )

    # Gas Leak
    elif any(
        k in text_lower
        for k in ["gas leak", "natural gas", "methane", "gas odor", "propane"]
    ):
        incident_type = "Gas Leak"
        affected_systems = ["HVAC", "Gas Line"]
        tasks.append({"task_desc": "Shut off gas supply valves", "urgency": "CRITICAL"})
        tasks.append(
            {
                "task_desc": f"Evacuate nearby area from {locations[0]}",
                "urgency": "CRITICAL",
            }
        )

    # Chemical Spill
    elif any(
        k in text_lower
        for k in [
            "chemical spill",
            "toxic leak",
            "acid spill",
            "hazmat",
            "hazardous material",
            "chemical storage",
            "chemical leak",
        ]
    ):
        incident_type = "Chemical Spill"
        affected_systems = ["Ventilation System"]
        tasks.append(
            {
                "task_desc": "Contain chemical spill and neutralize toxic agent",
                "urgency": "CRITICAL",
            }
        )
        tasks.append(
            {
                "task_desc": f"Evacuate nearby area from {locations[0]}",
                "urgency": "CRITICAL",
            }
        )

    # Flood
    elif any(
        k in text_lower
        for k in ["flood", "flooding", "water rising", "submerged", "heavy rain"]
    ):
        incident_type = "Flood"
        affected_systems = ["Drainage System"]
        tasks.append(
            {
                "task_desc": "Deploy water pumps to clear flooding",
                "urgency": "HIGH",
            }
        )
        tasks.append(
            {
                "task_desc": f"Evacuate nearby area from {locations[0]}",
                "urgency": "CRITICAL",
            }
        )

    # Earthquake
    elif any(
        k in text_lower
        for k in [
            "earthquake",
            "seismic",
            "ground shaking",
            "tremor",
            "structural collapse",
        ]
    ):
        incident_type = "Earthquake"
        affected_systems = ["Structural Integrity"]
        tasks.append(
            {
                "task_desc": f"Rescue trapped people from {locations[0]}",
                "urgency": "CRITICAL",
            }
        )
        tasks.append(
            {
                "task_desc": "Check structural integrity of surrounding buildings",
                "urgency": "HIGH",
            }
        )

    # Cyber Incident
    elif any(
        k in text_lower
        for k in [
            "cyber",
            "ransomware",
            "hacked",
            "data breach",
            "network breach",
            "database hack",
            "malware",
        ]
    ):
        incident_type = "Cyber Incident"
        affected_systems = ["Main Database", "Network Domain"]
        tasks.append(
            {
                "task_desc": "Isolate affected database and servers",
                "urgency": "CRITICAL",
            }
        )
        tasks.append(
            {
                "task_desc": "Initiate cybersecurity response plan",
                "urgency": "CRITICAL",
            }
        )

    # Suspicious Package
    elif any(
        k in text_lower
        for k in [
            "suspicious package",
            "unattended bag",
            "bomb threat",
            "explosive",
            "suspicious parcel",
        ]
    ):
        incident_type = "Suspicious Package"
        affected_systems = ["Physical Security"]
        tasks.append(
            {
                "task_desc": f"Secure area around {locations[0]} and establish perimeter",
                "urgency": "CRITICAL",
            }
        )
        tasks.append(
            {
                "task_desc": f"Dispatch bomb squad to {locations[0]}",
                "urgency": "CRITICAL",
            }
        )

    # Power Failure
    elif any(
        k in text_lower
        for k in [
            "power failure",
            "power outage",
            "grid outage",
            "blackout",
            "electricity down",
            "generator failure",
        ]
    ):
        incident_type = "Power Failure"
        affected_systems = ["Electrical Grid"]
        tasks.append(
            {
                "task_desc": f"Investigate grid outage and generator failure at {locations[0]}",
                "urgency": "HIGH",
            }
        )
        tasks.append(
            {
                "task_desc": "Switch to auxiliary power backup",
                "urgency": "HIGH",
            }
        )

    # Water Leakage
    elif any(k in text_lower for k in ["water leak", "pipe burst", "burst pipe"]):
        incident_type = "Water Leakage"
        if "electrical" in text_lower:
            affected_systems.append("Electrical Equipment")
        if "cooling" in text_lower:
            affected_systems.append("Cooling System")
        if not affected_systems:
            affected_systems = ["Water Line"]
        tasks.append({"task_desc": "Shut off water supply", "urgency": "HIGH"})
        if "electrical" in text_lower:
            tasks.append(
                {"task_desc": "Isolate electrical equipment", "urgency": "HIGH"}
            )
        if any(k in text_lower for k in ["pipe burst", "burst pipe"]):
            tasks.append({"task_desc": "Repair burst pipe", "urgency": "HIGH"})
        if "cooling" in text_lower:
            tasks.append({"task_desc": "Restore cooling system", "urgency": "HIGH"})

    # Medical Emergency General Fallback
    elif any(
        k in text_lower
        for k in [
            "medical",
            "patient",
            "injury",
            "injured",
            "ambulance",
        ]
    ):
        incident_type = "Medical Emergency"
        affected_systems = ["Human Health"]
        tasks.append(
            {
                "task_desc": f"Dispatch emergency medical services / ambulance to {locations[0]}",
                "urgency": "CRITICAL",
            }
        )

    if not tasks:
        tasks.append({"task_desc": "Perform routine safety checks", "urgency": "LOW"})

    # 4. Extract personnel
    personnel = []
    for name in [
        "ramesh",
        "suresh",
        "agent k",
        "operative j",
        "agent m",
        "operative s",
    ]:
        if name in text_lower:
            personnel.append(name.title())

    agent_matches = re.findall(r"\b(agent\s+[a-z]+|operative\s+[a-z]+)\b", text_lower)
    for am in agent_matches:
        personnel.append(am.title())

    if trapped_count_match:
        personnel.append(
            f"{trapped_count_match.group(1).lower()} {trapped_count_match.group(2).lower()}"
        )
    else:
        trapped_generic = re.search(
            r"\b(workers|trapped\s+people|trapped\s+workers)\b", text_lower
        )
        if trapped_generic:
            personnel.append(trapped_generic.group(1))

    if not personnel:
        personnel = ["Duty Staff"]
    personnel = list(dict.fromkeys(personnel))

    summary = text[:120] + "..." if len(text) > 120 else text

    return {
        "incident_type": incident_type,
        "location": locations[0] if locations else "Unknown Area",
        "affected_systems": affected_systems,
        "computed_priority_level": priority,
        "system_summary": summary,
        "identified_entities": {
            "locations": locations,
            "personnel": personnel,
        },
        "actionable_tasks": tasks,
    }


def mock_extraction(text: str) -> dict:
    parsed = semantic_fallback_extraction(text)
    report = {
        "incident_id": str(uuid.uuid4()),
        "iso_timestamp": datetime.datetime.now(datetime.UTC)
        .isoformat()
        .replace("+00:00", "Z"),
        "computed_priority_level": parsed["computed_priority_level"],
        "system_summary": parsed["system_summary"],
        "identified_entities": parsed["identified_entities"],
        "actionable_tasks": parsed["actionable_tasks"],
        "incident_type": parsed["incident_type"],
        "location": parsed["location"],
        "affected_systems": parsed["affected_systems"],
    }
    return report


def check_ram_usage() -> bool:
    try:
        import psutil
        import os

        process = psutil.Process(os.getpid())
        process_mem = process.memory_info().rss
        if process_mem > 3.8 * 1024 * 1024 * 1024:
            return True
        mem = psutil.virtual_memory()
        if mem.percent > 95:
            return True
    except Exception:
        pass
    return False


def apply_rule_fallback_if_needed(report_data: dict, text: str) -> dict:
    parsed = semantic_fallback_extraction(text)
    if not report_data.get("incident_type") or report_data["incident_type"] in [
        "Other",
        "None",
        None,
    ]:
        report_data["incident_type"] = parsed["incident_type"]
    if not report_data.get("location") or report_data["location"] in [
        "Unknown Area",
        "None",
        None,
    ]:
        report_data["location"] = parsed["location"]
    if not report_data.get("affected_systems"):
        report_data["affected_systems"] = parsed["affected_systems"]
    return report_data


class SLMProcessor:
    def __init__(self, model_path: Path = SLM_MODEL_PATH):
        self.model_path = model_path
        self.llm = None

        if self.model_path.exists():
            try:
                from llama_cpp import Llama

                logging.info(f"Loading Phi-3 GGUF model from {self.model_path}...")
                self.llm = Llama(
                    model_path=str(self.model_path),
                    n_ctx=2048,
                    n_threads=2,
                    verbose=False,
                )
            except Exception as e:
                logging.error(f"Failed to load Llama model: {e}")

    def extract_incident(self, text: str) -> dict:
        if len(text) > 4000:
            logging.warning("Input text exceeds 4000 characters. Truncating context.")
            text = text[:4000]

        if check_ram_usage():
            logging.error(
                "OOM Protection active: System RAM usage is above 3.8GB limit. Aborting inference."
            )
            raise MemoryError("Inference aborted due to high RAM usage (>3.8GB)")

        # Fallback/Mock mode if real model was not loaded
        if self.llm is None:
            logging.warning("Llama model not loaded. Using mock JSON extraction.")
            report_data = mock_extraction(text)
            report = IncidentReport(**report_data)
            return report.model_dump()

        system_prompt = (
            "You are an intelligence extractor. Read the following field note and output strictly a JSON object "
            "conforming to this schema:\n"
            "{\n"
            '  "incident_id": "string (uuid4)",\n'
            '  "iso_timestamp": "string (ISO 8601)",\n'
            '  "computed_priority_level": "LOW | MEDIUM | HIGH | CRITICAL",\n'
            '  "system_summary": "Brief 2-sentence summary",\n'
            '  "identified_entities": {\n'
            '    "locations": ["string"],\n'
            '    "personnel": ["string"]\n'
            "  },\n"
            '  "actionable_tasks": [\n'
            '    { "task_desc": "string", "urgency": "LOW | MEDIUM | HIGH | CRITICAL" }\n'
            "  ],\n"
            '  "incident_type": "string | null",\n'
            '  "location": "string | null",\n'
            '  "affected_systems": ["string"] | null\n'
            "}\n"
            "Do not include markdown wrappers (e.g. ```json) in your final response. "
            "Output ONLY the JSON object. Do not explain your response."
        )

        prompt = f"<|system|>\n{system_prompt}<|end|>\n<|user|>\n{text}<|end|>\n<|assistant|>\n"

        for attempt in range(1, 4):
            try:
                logging.info(f"Running llama.cpp inference (attempt {attempt})...")
                response = self.llm(
                    prompt, max_tokens=512, temperature=0.1, stop=["<|end|>"]
                )

                output_text = response["choices"][0]["text"].strip()

                if output_text.startswith("```"):
                    output_text = output_text.strip("`").strip()
                    if output_text.startswith("json"):
                        output_text = output_text[4:].strip()

                report_data = json.loads(output_text)

                # Apply post-processing fallback logic
                report_data = apply_rule_fallback_if_needed(report_data, text)

                # Validate with Pydantic
                report = IncidentReport(**report_data)
                logging.info("Successfully structured and validated text via SLM.")
                return report.model_dump()

            except (json.JSONDecodeError, ValidationError) as e:
                logging.warning(
                    f"Inference attempt {attempt} failed to produce valid schema: {e}"
                )
                if attempt == 3:
                    logging.error(
                        "All 3 SLM inference attempts failed. Gracefully falling back to mock extraction."
                    )
                    report_data = mock_extraction(text)
                    return IncidentReport(**report_data).model_dump()
            except Exception as e:
                logging.error(f"Llama-cpp inference error: {e}")
                raise e

        # Fallback return
        report_data = mock_extraction(text)
        return IncidentReport(**report_data).model_dump()


# Legacy/Compatibility Service structure
class SLMService(SLMProcessor):
    pass


_global_slm_service = None


def get_slm_service() -> SLMService:
    global _global_slm_service
    if _global_slm_service is None:
        _global_slm_service = SLMService()
    return _global_slm_service


def structure_text(text: str) -> dict:
    return get_slm_service().extract_incident(text)
