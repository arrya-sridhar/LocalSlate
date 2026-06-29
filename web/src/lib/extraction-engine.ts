/**
 * LocalSlate Intelligence Extraction Engine
 * TypeScript port of src/engine/slm_processor.py mock_extraction
 *
 * Runs entirely in the browser — zero API calls.
 * Extracts structured incident reports from raw field notes.
 */

export interface ActionableTask {
  task_desc: string;
  urgency: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
}

export interface IdentifiedEntities {
  locations: string[];
  personnel: string[];
}

export interface IncidentReport {
  incident_id: string;
  iso_timestamp: string;
  computed_priority_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | "PENDING_REVIEW";
  system_summary: string;
  identified_entities: IdentifiedEntities;
  actionable_tasks: ActionableTask[];
  created_at: string;
}

function generateUUID(): string {
  return crypto.randomUUID();
}

function extractPriority(text: string): IncidentReport["computed_priority_level"] {
  const lower = text.toLowerCase();
  if (lower.includes("critical") || lower.includes("danger") || lower.includes("emergency") || lower.includes("explosion")) {
    return "CRITICAL";
  }
  if (lower.includes("high") || lower.includes("urgent") || lower.includes("leak") || lower.includes("fire") || lower.includes("evacuate")) {
    return "HIGH";
  }
  if (lower.includes("medium") || lower.includes("warning") || lower.includes("malfunction")) {
    return "MEDIUM";
  }
  return "LOW";
}

function extractLocations(text: string): string[] {
  const lower = text.toLowerCase();
  const locations: Set<string> = new Set();

  // Sector patterns
  const sectorMatches = lower.matchAll(/sector\s+\d+/gi);
  for (const m of sectorMatches) locations.add(toTitleCase(m[0]));

  // Room patterns
  const roomMatches = lower.matchAll(/room\s+[a-z0-9]+/gi);
  for (const m of roomMatches) locations.add(toTitleCase(m[0]));

  // Known infrastructure
  const knownLocations = [
    "main node", "cooling array", "server room", "control room",
    "data center", "power grid", "communications hub", "field station",
    "observation post", "perimeter", "warehouse", "laboratory",
    "command center", "checkpoint", "hangar", "reactor"
  ];
  for (const loc of knownLocations) {
    if (lower.includes(loc)) locations.add(toTitleCase(loc));
  }

  // Building/area patterns
  const buildingMatches = lower.matchAll(/(?:building|facility|zone|area|wing|floor)\s+[a-z0-9]+/gi);
  for (const m of buildingMatches) locations.add(toTitleCase(m[0]));

  return locations.size > 0 ? Array.from(locations) : ["Unknown Area"];
}

function extractPersonnel(text: string): string[] {
  const lower = text.toLowerCase();
  const personnel: Set<string> = new Set();

  // Title + Name patterns
  const titlePatterns = [
    /(?:agent|operative|officer|captain|sergeant|lieutenant|commander|dr\.|professor|inspector|chief|corporal|private)\s+[a-z]+/gi
  ];
  for (const pattern of titlePatterns) {
    const matches = lower.matchAll(pattern);
    for (const m of matches) personnel.add(toTitleCase(m[0]));
  }

  // Team patterns
  const teamMatches = lower.matchAll(/(?:team|squad|unit)\s+(?:alpha|beta|gamma|delta|[a-z0-9]+)/gi);
  for (const m of teamMatches) personnel.add(toTitleCase(m[0]));

  return personnel.size > 0 ? Array.from(personnel) : ["Duty Staff"];
}

function extractTasks(text: string): ActionableTask[] {
  const lower = text.toLowerCase();
  const tasks: ActionableTask[] = [];

  // Pattern-based task extraction
  if (lower.includes("cooling") || lower.includes("temperature")) {
    tasks.push({ task_desc: "Deploy secondary cooling array", urgency: "CRITICAL" });
  }
  if (lower.includes("leak") || lower.includes("water") || lower.includes("flood")) {
    tasks.push({ task_desc: "Evacuate affected area and isolate leak source", urgency: "CRITICAL" });
  }
  if (lower.includes("fire") || lower.includes("smoke")) {
    tasks.push({ task_desc: "Activate fire suppression systems and evacuate", urgency: "CRITICAL" });
  }
  if (lower.includes("evacuate") || lower.includes("evacuation")) {
    tasks.push({ task_desc: "Initiate emergency evacuation protocol", urgency: "CRITICAL" });
  }
  if (lower.includes("power") || lower.includes("electrical") || lower.includes("outage")) {
    tasks.push({ task_desc: "Switch to backup power and diagnose electrical fault", urgency: "HIGH" });
  }
  if (lower.includes("communication") || lower.includes("radio") || lower.includes("signal")) {
    tasks.push({ task_desc: "Re-establish communication channels", urgency: "HIGH" });
  }
  if (lower.includes("investigate") || lower.includes("inspect")) {
    tasks.push({ task_desc: "Conduct detailed site investigation and report findings", urgency: "MEDIUM" });
  }
  if (lower.includes("repair") || lower.includes("fix") || lower.includes("maintenance")) {
    tasks.push({ task_desc: "Schedule maintenance and repair operations", urgency: "MEDIUM" });
  }
  if (lower.includes("report") || lower.includes("document")) {
    tasks.push({ task_desc: "File detailed incident documentation", urgency: "LOW" });
  }

  if (tasks.length === 0) {
    tasks.push({ task_desc: "Perform routine safety checks", urgency: "LOW" });
  }

  return tasks;
}

function generateSummary(text: string, priority: string): string {
  if (text.length > 120) {
    return text.slice(0, 120) + "...";
  }
  return text || `Field report. Priority: ${priority}.`;
}

function toTitleCase(str: string): string {
  return str
    .split(" ")
    .map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");
}

/**
 * Extract a structured incident report from raw text.
 * Runs entirely in-browser — no network calls.
 */
export function extractIncident(text: string): IncidentReport {
  // Enforce 4000-char limit
  const truncated = text.length > 4000 ? text.slice(0, 4000) : text;

  const priority = extractPriority(truncated);
  const locations = extractLocations(truncated);
  const personnel = extractPersonnel(truncated);
  const tasks = extractTasks(truncated);
  const summary = generateSummary(truncated, priority);
  const now = new Date().toISOString();

  return {
    incident_id: generateUUID(),
    iso_timestamp: now,
    computed_priority_level: priority,
    system_summary: summary,
    identified_entities: { locations, personnel },
    actionable_tasks: tasks,
    created_at: now,
  };
}

/**
 * Validate that a text input meets pipeline requirements.
 */
export function validateTextInput(text: string): { valid: boolean; error?: string } {
  if (!text || text.trim().length === 0) {
    return { valid: false, error: "Text input cannot be empty" };
  }
  if (text.length > 4000) {
    return { valid: true, error: `Text will be truncated to 4,000 characters (currently ${text.length})` };
  }
  return { valid: true };
}
