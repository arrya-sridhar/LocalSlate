import os
import json
import logging
from pathlib import Path
from uuid import uuid4
from datetime import datetime

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SLM_MODEL_PATH = PROJECT_ROOT / ".models" / "slm" / "phi3-mini-4k.gguf"

class SLMProcessorError(Exception):
    pass

class SLMProcessor:
    def __init__(self):
        if Llama is None:
            raise ImportError("llama-cpp-python is not installed.")
        
        if not SLM_MODEL_PATH.exists():
            logging.warning(f"SLM model not found at {SLM_MODEL_PATH}. Inference will fail if not downloaded.")
            self.llm = None
        else:
            try:
                # Initialize Llama with n_threads=2 to bound CPU usage
                self.llm = Llama(
                    model_path=str(SLM_MODEL_PATH),
                    n_threads=2,
                    n_ctx=4096,
                    verbose=False
                )
            except Exception as e:
                logging.error(f"Failed to load SLM model: {e}")
                self.llm = None

        self.system_prompt = """You are an intelligence extractor. Read the following field note and output strictly a JSON object conforming to this schema:
{
  "incident_id": "uuid4",
  "iso_timestamp": "YYYY-MM-DDTHH:MM:SSZ",
  "computed_priority_level": "LOW|MEDIUM|HIGH|CRITICAL", 
  "system_summary": "Brief 2-sentence summary of the field report.",
  "identified_entities": {
    "locations": ["Location 1"],
    "personnel": ["Person 1"]
  },
  "actionable_tasks": [
    {
      "task_desc": "Task description",
      "urgency": "CRITICAL"
    }
  ]
}

Ensure the output is ONLY valid JSON, without any markdown formatting or extra text."""

    def extract_incident(self, text: str) -> dict:
        if self.llm is None:
            raise SLMProcessorError("SLM model was not loaded successfully.")

        prompt = f"<|system|>\n{self.system_prompt}\n<|user|>\nTEXT: {text}\n<|assistant|>\n"
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.llm(
                    prompt,
                    max_tokens=1024,
                    temperature=0.1,
                    stop=["<|end|>"]
                )
                
                output_text = response["choices"][0]["text"].strip()
                
                # Clean up markdown formatting if the model still outputs it
                if output_text.startswith("```json"):
                    output_text = output_text[7:]
                if output_text.startswith("```"):
                    output_text = output_text[3:]
                if output_text.endswith("```"):
                    output_text = output_text[:-3]
                
                output_text = output_text.strip()
                
                # Attempt to parse
                parsed_json = json.loads(output_text)
                
                # Fill missing auto-fields if not generated correctly by the model
                if "incident_id" not in parsed_json or parsed_json["incident_id"] == "uuid4":
                    parsed_json["incident_id"] = str(uuid4())
                if "iso_timestamp" not in parsed_json or parsed_json["iso_timestamp"] == "YYYY-MM-DDTHH:MM:SSZ":
                    parsed_json["iso_timestamp"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

                return parsed_json
            
            except json.JSONDecodeError as e:
                logging.warning(f"Attempt {attempt + 1}/{max_retries} failed to parse JSON: {e}")
                if attempt == max_retries - 1:
                    raise SLMProcessorError("Failed to generate valid JSON after 3 attempts.") from e
            except Exception as e:
                raise SLMProcessorError(f"Inference error: {e}") from e
