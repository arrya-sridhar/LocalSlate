# LocalSlate 🌌 User Manual

LocalSlate is a zero-trust, offline-first incident intelligence processing pipeline. It runs entirely on local commodity hardware, offering private and secure processing of unstructured incident reports (text notes and audio recordings).

---

## 📖 Table of Contents
1. [Application Overview](#-application-overview)
2. [Setup Instructions](#-setup-instructions)
3. [Local Run Guide](#-local-run-guide)
4. [Render Deployment](#-render-deployment)
5. [Railway MySQL Setup](#-railway-mysql-setup)
6. [Using Text Incident Input](#-using-text-incident-input)
7. [Using the Voice Recorder](#-using-the-voice-recorder)
8. [Using API Documentation (/docs)](#-using-api-documentation-docs)
9. [Troubleshooting](#-troubleshooting)

---

## 🌌 Application Overview
LocalSlate processes raw input files (audio or text) to extract structured, actionable incident data (locations, personnel, and tasks) using:
- **Faster-Whisper**: Quantized `int8` English transcription on local CPU.
- **Phi-3 SLM**: Loaded via `llama.cpp` to structure raw text into structured JSON.
- **SQLite Engine**: Safe local database operations utilizing Write-Ahead Logging (WAL) and transactional safety.
- **FastAPI Backend**: Secure REST API layer.
- **Vanilla SPA Frontend**: Modern dark-themed dashboard.

---

## ⚙️ Setup Instructions

### Prerequisites
1. **Python 3.11** or **Python 3.12** installed.
2. **Git** installed.
3. Access to a **MySQL** server (for Railway or local persistence).

### Installation Steps
1. Clone the repository.
2. Setup the directory structure:
   ```bash
   mkdir -p .models/whisper .models/slm data/cache data/queue data/failed_audio
   ```
3. Place model files:
   - Whisper: `model.bin`, `config.json`, `vocabulary.txt` in `.models/whisper/`.
   - Phi-3 SLM: `Phi-3-mini-4k-instruct-q4.gguf` in `.models/slm/phi3-mini-4k.gguf`.
4. Initialize and activate virtual environment:
   ```bash
   pip install uv
   uv venv -p 3.11
   .venv\Scripts\activate || source .venv/bin/activate
   ```
5. Install dependencies:
   ```bash
   uv pip install -r backend/requirements.txt
   ```

---

## 💻 Local Run Guide

### Run API Backend
Run FastAPI server locally on port 8000:
```bash
.venv\Scripts\uvicorn backend.main:app --reload
```
Open `http://127.0.0.1:8000` in your web browser.

### Run CLI Dashboard
To monitor queue stages, DB count, and CPU metrics:
```bash
.venv\Scripts\python backend/src/app/dashboard.py
```

---

## ☁️ Render Deployment
To deploy the backend to Render:
1. Create a Web Service pointing to your repository.
2. Set the **Root Directory** to `backend`.
3. Set the **Build Command** to `pip install -r requirements-render.txt`.
4. Set the **Start Command** to `uvicorn main:app --host 0.0.0.0 --port $PORT`.
5. Set the environment variables `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` to point to your database.

---

## 🛢️ Railway MySQL Setup
To persist incidents in a Railway-hosted MySQL instance:
1. Spin up a **MySQL** service on your Railway dashboard.
2. Retrieve the connection credentials from the service variables.
3. Add these credentials to your local `.env` file or Render environment configurations:
   ```ini
   DB_HOST=<railway-mysql-host>
   DB_PORT=3306
   DB_NAME=railway
   DB_USER=root
   DB_PASSWORD=<railway-provided-password>
   ```
The app will auto-create the necessary relational database schema upon startup.

---

## ✍️ Using Text Incident Input
1. Open the frontend dashboard.
2. In the "Ingest Incident" form, type or paste the raw field notes (up to 4,000 characters).
3. Click "Submit Text" to pass the data to the LLM processor.
4. The structured output will automatically appear in the active incident list.

---

## 🎙️ Using the Voice Recorder
1. Open the dashboard.
2. Ensure you have given mic permission to your browser.
3. Click "Record Audio" to record field reports.
4. Click "Stop & Upload" once you are finished speaking.
5. The audio is captured as a `16kHz` mono WAV, uploaded to the `/upload` API endpoint, processed by the Whisper model, and automatically committed to the database.

---

## 🔌 Using API Documentation (/docs)
FastAPI provides automatically generated interactive Swagger documentation:
- URL: `http://127.0.0.1:8000/docs`
- Use this page to test the endpoints (`POST /process`, `POST /upload`, `GET /status`, `GET /incidents`, etc.) directly from your browser.

---

## 🛠️ Troubleshooting
* **Database lock errors**: The system uses SQLite WAL mode to support concurrency. If you run into db write conflicts, verify no other process is holding a direct filesystem lock on `data/localslate.db`.
* **OOM / Out-of-memory errors**: Pipelined inference is resource-constrained. Ensure the host system has at least `3.8GB` of free RAM. If RAM usage exceeds this threshold, SLM execution pauses to prevent host crashes.
* **Audio upload failures**: Raw audio must be under `25MB`. Check that your browser supports standard WebRTC recording outputs.
