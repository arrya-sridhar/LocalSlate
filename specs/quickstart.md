# Quickstart Guide (Zero-Network Configuration)

Follow these instructions to establish environment parity on your local machine *before* disconnecting from the network.

---

## 1. Directory Structure Initialization
Run the commands below to ensure all git-ignored paths exist:
```bash
mkdir -p .models/whisper .models/slm data/cache data/queue data/failed_audio
```

---

## 2. Model Weight Placements
Download the model weights while you still have internet access and place them in the correct directories:

1. **Whisper Model**:
   - Download the `faster-whisper-base-en` files.
   - Place `model.bin`, `config.json`, and `vocabulary.txt` inside `./.models/whisper/`.
2. **Phi-3 SLM**:
   - Download `Phi-3-mini-4k-instruct-q4.gguf`.
   - Place the `.gguf` file strictly at `./.models/slm/phi3-mini-4k.gguf`.

---

## 3. Dependency Installation
We use `uv` for fast dependency resolution:
```bash
# 1. Install uv
pip install uv

# 2. Create the virtual environment
uv venv -p 3.11

# 3. Activate the environment
# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate

# 4. Install requirements
uv pip install -r backend/requirements.txt
```

---

## 4. Run the Web Application
Start the FastAPI server locally:
```bash
.venv\Scripts\uvicorn backend.main:app --reload
```
Open `http://127.0.0.1:8000/` to access the frontend client dashboard.

---

## 5. Run the Interactive CLI Dashboard
To view resource levels, ingestion states, and database logs inside the terminal:
```bash
.venv\Scripts\python backend/src/app/dashboard.py
```
