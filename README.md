# LocalSlate 🌌

LocalSlate is a zero-trust, offline-first intelligence processing pipeline designed to extract structured incident reports from raw field notes (audio and text). It executes entirely on local commodity hardware with strict resource boundaries and absolute network isolation.

---

## 📖 Table of Contents
1. [System Specifications & Scope](#-system-specifications--scope)
2. [Folder Architecture](#-folder-architecture)
3. [Memory & Thread Allocation](#-memory--thread-allocation)
4. [Getting Started](#-getting-started)
5. [Local Run Guide](#-local-run-guide)
6. [Backend API Documentation](#-backend-api-documentation)
7. [Frontend Dashboard](#-frontend-dashboard)
8. [SQLite Concurrency Configurations](#-sqlite-concurrency-configurations)
9. [Offline AI Fallback & Resilience](#-offline-ai-fallback--resilience)
10. [Render Deployment Guide](#-render-deployment-guide)
11. [Troubleshooting](#-troubleshooting)

---

## ⚙️ System Specifications & Scope
* **Zero Network Footprint:** Operating under a zero-trust model, all processing is local. No outbound network requests are made.
* **Hardware Ceiling:** Optimized to run within **4GB RAM** and a maximum of **4 CPU threads**.
* **Audio Inputs:** Raw audio files must be mono, `16kHz`, `.wav` format, under `25MB` (~15 minutes of speech).
* **Text Inputs:** Plain UTF-8 text with a hard limit of `4,000 characters` (aligned with Phi-3 context limits).
* **Persistent Storage:** Data is stored in a structured MySQL database (configured via environment variables).

---

## 📁 Folder Architecture

```yaml
hackathon_3-1/
├── .models/                       # [Git-ignored] Local AI Model weights
│   ├── whisper/                   #   - Whisper transcription weights
│   └── slm/                       #   - Phi-3 SLM instructions & GGUF
├── backend/                       # REST Backend Service
│   ├── main.py                    #   - FastAPI startup lifespan entrypoint
│   ├── requirements.txt           #   - local backend dependencies
│   ├── requirements-render.txt    #   - lightweight Render platform requirements
│   └── src/                       #   - backend python package
│       ├── app/                   #     - Queue and CLI dashboard daemons
│       ├── database/              #     - MySQL DB ORM & transactional queries
│       ├── engine/                #     - Whisper & Phi-3 LLM processors
│       ├── models/                #     - Pydantic schema validation structures
│       └── api/                   #     - FastAPI routers & dependencies
├── frontend/                      # Vanilla SPA Frontend
│   ├── index.html                 #   - HTML layout grids
│   ├── css/                       #   - style.css rules (dark theme-friendly)
│   └── js/                        #   - main.js API request controller
├── specs/                         # Project technical design requirements
├── tests/                         # Consolidated integration test suite
├── tools/                         # Maintenance and format checks
├── README.md                      # This file
└── pytest.ini                     # Global testing setup configs
```

---

## 🧠 Memory & Thread Allocation

| Resource / Process | Max Memory Allocation | Max Thread Count |
| :--- | :--- | :--- |
| **OS Overhead** | ~500 MB | N/A |
| **faster-whisper (int8)** | ~500 MB | 2 (via `OMP_NUM_THREADS=2`) |
| **Phi-3-mini-4k (Q4_K_M)** | ~2200 MB | 2 (via `n_threads=2`) |
| **Python Dashboard & DB** | ~200 MB | 1 |
| **Total Peak Load** | **~3400 MB** | **Maximum 4 concurrent threads** |

---

## 🚀 Getting Started

### 1. Initialize Folders
Establish the required directory layout:
```bash
mkdir -p .models/whisper .models/slm data/cache data/queue data/failed_audio
```

### 2. Model Installation
1. **Whisper Engine**: Download `faster-whisper-base-en` files (`model.bin`, `config.json`, `vocabulary.txt`) and place them in `.models/whisper/`.
2. **Phi-3 SLM**: Download `Phi-3-mini-4k-instruct-q4.gguf` and place it at `.models/slm/phi3-mini-4k.gguf`.

### 3. Setup Virtual Environment
```bash
pip install uv
uv venv -p 3.11
# Activate Windows:
.venv\Scripts\activate
# Activate Mac/Linux:
source .venv/bin/activate

uv pip install -r backend/requirements.txt
```

### 4. Setup MySQL Database
1. Make sure MySQL server is installed and running (e.g. on port 3306).
2. Create a database for LocalSlate (e.g. `CREATE DATABASE localslate;`).
3. Create a `.env` file in the project root based on `.env.example` and set your credentials:
   ```ini
   DB_HOST=127.0.0.1
   DB_PORT=3306
   DB_NAME=localslate
   DB_USER=root
   DB_PASSWORD=your_password
   ```

---

## 💻 Local Run Guide

### Running the API & Frontend Web App
To run the server locally:
```bash
.venv\Scripts\uvicorn backend.main:app --reload
```
Open `http://127.0.0.1:8000/` in your browser.

### Running the Interactive CLI Dashboard
To monitor the system resources and database stream inside the terminal:
```bash
.venv\Scripts\python backend/src/app/dashboard.py
```

---

## 🔌 Backend API Documentation
FastAPI provides auto-generated API specifications:
* **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **OpenAPI Spec**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

### Core Endpoints:
- `GET /`: Serves the Single-Page Application.
- `GET /health`: JSON status of database connection connectivity.
- `GET /status`: Live host CPU/RAM metrics, active queue timeline stages, and DB records counts.
- `GET /incidents`: Feeds the latest 10 saved incident reports.
- `POST /process`: Direct text extraction and immediate DB write.
- `POST /upload`: Multipart upload to cash folder for watchdog ingestion.
- `DELETE /incidents`: Purges all database records.

---

## 🎨 Frontend Dashboard
The user interface is built on standard **HTML5**, **Vanilla CSS**, and **Vanilla Javascript**.
- **Features**: Glassmorphic theme layouts, direct text processing form, drag-and-drop file upload, live database streams with accordion JSON inspection, system resource graphs, and an instant light/dark mode switch.
- **Offline Friendly**: No external libraries or CDNs are contacted. All styles and scripting are packaged locally.

---

## 💾 MySQL Database Configurations
To handle concurrent reads/writes and optimize transaction throughput:
- Connections use SQLAlchemy connection pooling (`pool_size=10`, `max_overflow=20`).
- Stale connection detection is enabled automatically via `pool_pre_ping=True`.
- Transactions utilize SQLAlchemy Session contexts with safe `.commit()` and `.rollback()` error handlers.

---

## 🤖 Offline AI Fallback & Resilience
* **Model Detection**: The engines dynamically inspect `.models/` paths. If binaries are missing, the pipeline falls back gracefully to a mock structured regex extractor, ensuring that startup never crashes.
* **OOM protection**: Monitors memory utilization. If RAM allocation approaches 3.8GB, active inference is paused and rescheduled.

---

## ☁️ Render Deployment Guide
The web API and mock extraction demos are optimized to deploy easily on Render:
- **Root Directory**: `backend`
- **Build Command**: `pip install -r requirements-render.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- *Lightweight dependencies:* The Render deployment excludes heavyweight PyTorch and llama-cpp wheels, relying on local structured mock processing to showcase API flows.

### Render Environment Variables Setup
To enable database persistence on Render, configure the following Environment Variables in your Render Dashboard (under **Environment** settings for your Web Service):
- `DB_HOST`: The internal host address of your Render MySQL Database. **DO NOT set this to `127.0.0.1`** as localhost connection is not allowed on Render.
- `DB_PORT`: The connection port for the database (default: `3306`).
- `DB_NAME`: The database name.
- `DB_USER`: The database user.
- `DB_PASSWORD`: The database password.

*Graceful Degradation:* If `DB_HOST` is missing or is set to `127.0.0.1` on Render, the application will automatically initialize in **disconnected fallback mode**. In this mode, the server starts up successfully without crashing, and endpoints like `/status` and `/health` remain online.


---

## 🛠️ Troubleshooting
* **ModuleNotFoundError on pytest**: Run tests via `pytest` (configured with `pytest.ini`).
* **MySQL Connection Failures**: Check that the MySQL server is running, the port is open, and `.env` credentials are correct.

