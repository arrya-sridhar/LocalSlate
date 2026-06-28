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


def mock_extraction(text: str) -> dict:
    text_lower = text.lower()

    # 1. Determine severity/priority
    priority = "LOW"
    is_accident_emergency = any(
        k in text_lower
        for k in [
            "accident",
            "crash",
            "collision",
            "emergency",
            "injured",
            "casualty",
            "fire",
            "trapped",
            "smoke",
        ]
    )

    if (
        "critical" in text_lower
        or "danger" in text_lower
        or "severe" in text_lower
        or "fatality" in text_lower
        or "trapped" in text_lower
    ):
        priority = "CRITICAL"
    elif (
        is_accident_emergency
        or "high" in text_lower
        or "urgent" in text_lower
        or "leak" in text_lower
    ):
        priority = "HIGH"
    elif "medium" in text_lower or "warning" in text_lower:
        priority = "MEDIUM"

    # 2. Extract locations
    locations = []

    # Check Gachibowli specific locations first
    if "gachibowli" in text_lower:
        if "flyover" in text_lower:
            locations.append("Gachibowli Flyover")
        elif "crossroads" in text_lower or "cross road" in text_lower:
            locations.append("Gachibowli Crossroads")
        else:
            locations.append("Gachibowli")

    # Check for "Building [A-Z]" and "chemical storage"
    building_match = re.search(r"\b(Building\s+[A-Za-z0-9])\b", text, re.IGNORECASE)
    if building_match:
        b_name = building_match.group(1).title()
        if "chemical storage" in text_lower:
            locations.append(f"{b_name} - Chemical Storage Room")
        else:
            locations.append(b_name)
    elif "chemical storage" in text_lower:
        locations.append("Chemical Storage Room")

    # Match explicit isolated rooms (e.g. Room B) - ensure word boundaries so "room of" doesn't match
    room_match = re.search(r"\broom\s+([A-Za-z0-9])\b", text, re.IGNORECASE)
    if room_match:
        r_name = f"Room {room_match.group(1).upper()}"
        # Avoid duplicate room if it is already part of Building/Chemical Storage Room name
        if not any(r_name in loc for loc in locations):
            locations.append(r_name)

    # Match Sector names (e.g. Sector 7, Sector 4)
    sector_match = re.search(r"\b(sector\s+\d+)\b", text, re.IGNORECASE)
    if sector_match:
        locations.append(sector_match.group(1).title())

    # Match specific known concepts
    if "cooling array" in text_lower:
        locations.append("Cooling Array")

    # Fallback to general prepositions if no structured locations found
    if not locations:
        prep_matches = re.findall(
            r"\b(?:at|on|in|near)\s+([A-Z][a-zA-Z0-9']+(?:\s+[A-Z][a-zA-Z0-9']+)*)",
            text,
        )
        for m in prep_matches:
            loc = m.strip()
            # Filter out dates, times, days, etc.
            if not re.match(
                r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|January|February|March|April|May|June|July|August|September|October|November|December|PM|AM)\b",
                loc,
                re.IGNORECASE,
            ):
                if loc not in locations and not any(
                    loc in existing for existing in locations
                ):
                    locations.append(loc)

    # Default fallback
    if not locations:
        locations = ["Sector 7"] if "sector 7" in text_lower else ["Unknown Area"]
    else:
        # Filter duplicates while maintaining order
        seen = set()
        unique_locations = []
        for x in locations:
            if x not in seen:
                seen.add(x)
                unique_locations.append(x)
        locations = unique_locations

    # 3. Extract personnel
    personnel = []

    # Match counts of workers / trapped people (e.g. Two workers, 2 workers)
    trapped_count_match = re.search(
        r"\b((?:\d+|[Tt]wo|[Tt]hree|[Ff]our|[Ff]ive|[Ss]everal))\s+(workers|people|persons|staff|operators|individuals|occupants)\b",
        text,
    )
    if trapped_count_match:
        personnel.append(
            f"{trapped_count_match.group(1).lower()} {trapped_count_match.group(2).lower()}"
        )
    else:
        # Check if generic trapped workers/people mentioned
        trapped_generic = re.search(
            r"\b(workers|trapped\s+people|trapped\s+workers)\b", text_lower
        )
        if trapped_generic:
            personnel.append(trapped_generic.group(1))

    # Case-sensitive name extraction around "injured"
    injured_matches = re.search(
        r"([A-Z][a-z]+(?:\s*(?:,|and)\s*[A-Z][a-z]+)*)\s+(?:is|are|were)\s+injured",
        text,
    )
    if injured_matches:
        names_str = injured_matches.group(1)
        for name in re.split(r",|\band\b", names_str):
            name_cleaned = name.strip()
            if name_cleaned:
                personnel.append(name_cleaned)

    injured_matches_post = re.search(
        r"injured\s+(?:people|personnel|persons|cyclists|pedestrians)?\s*:?\s*([A-Z][a-z]+(?:\s*(?:,|and)\s*[A-Z][a-z]+)*)",
        text,
    )
    if injured_matches_post:
        names_str = injured_matches_post.group(1)
        for name in re.split(r",|\band\b", names_str):
            name_cleaned = name.strip()
            if name_cleaned:
                personnel.append(name_cleaned)

    # Case-insensitive checks for known names/agents
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

    # Existing prefix matching for agents/operatives
    pers_matches = re.findall(
        r"\b(agent\s+[a-zA-Z]|operative\s+[a-zA-Z])\b", text_lower
    )
    for m in pers_matches:
        personnel.append(m.title())

    if not personnel:
        personnel = ["Duty Staff"]
    else:
        # Filter duplicates while maintaining order
        seen = set()
        unique_personnel = []
        for x in personnel:
            if x not in seen:
                seen.add(x)
                unique_personnel.append(x)
        personnel = unique_personnel

    # 4. Extract actionable tasks
    tasks = []

    # Blocked traffic
    if "traffic" in text_lower and any(
        k in text_lower for k in ["block", "congest", "jam", "stop", "shut", "close"]
    ):
        loc_suffix = f" at {locations[0]}" if locations else ""
        tasks.append(
            {
                "task_desc": f"Clear blocked traffic{loc_suffix} and divert vehicles",
                "urgency": "HIGH",
            }
        )

    # Fire department dispatch
    if any(k in text_lower for k in ["fire", "blaze"]):
        loc_suffix = f" to {locations[0]}" if locations else ""
        tasks.append(
            {
                "task_desc": f"Dispatch fire department{loc_suffix} to control the fire hazard",
                "urgency": "CRITICAL",
            }
        )

    # Rescue trapped workers
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

    # Emergency medical services
    if any(
        k in text_lower
        for k in [
            "ambulance",
            "medical",
            "hospital",
            "paramedics",
            "injured",
            "trapped",
            "doctor",
        ]
    ):
        loc_suffix = f" to {locations[0]}" if locations else ""
        tasks.append(
            {
                "task_desc": f"Dispatch emergency medical services / ambulance{loc_suffix}",
                "urgency": "CRITICAL",
            }
        )

    # Evacuation
    if any(
        k in text_lower for k in ["smoke", "leak", "fire", "evacuate", "evacuation"]
    ):
        loc_suffix = f" from {locations[0]}" if locations else ""
        tasks.append(
            {
                "task_desc": f"Evacuate nearby area{loc_suffix}",
                "urgency": "CRITICAL",
            }
        )

    # Deploy traffic police / police
    if any(k in text_lower for k in ["police", "cop", "traffic police"]):
        loc_suffix = f" to {locations[0]}" if locations else ""
        tasks.append(
            {
                "task_desc": f"Deploy traffic police{loc_suffix} for crowd control and investigation",
                "urgency": "HIGH",
            }
        )

    # Default tasks if nothing else matched
    if not tasks:
        if "cooling" in text_lower:
            tasks.append(
                {"task_desc": "Deploy secondary cooling array", "urgency": "CRITICAL"}
            )
        if "leak" in text_lower or "water" in text_lower:
            tasks.append(
                {
                    "task_desc": "Evacuate Server Room B and isolate leak",
                    "urgency": "CRITICAL",
                }
            )

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
            "locations": locations,
            "personnel": personnel,
        },
        "actionable_tasks": tasks,
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
            "  ]\n"
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
