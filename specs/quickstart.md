# Quickstart Guide (Zero-Network Configuration)

Follow these instructions exactly to establish environment parity on your local machine *before* disconnecting from the network.

## 1. Repository Setup
Clone the repository and navigate into the root:
```bash
git clone https://code.swecha.org/arrya.sridhar/hackathon_3.git
cd hackathon_3
```

## 2. Directory Structure Initialization
Run the initialization script (or create these manually) to ensure all `.gitignore` paths exist:
```bash
mkdir -p .models/whisper
mkdir -p .models/slm
mkdir -p data/cache
mkdir -p data/queue
mkdir -p data/failed_audio
```

## 3. Manual Model Deposition
**CRITICAL:** You must download the model weights while you still have internet access and place them in the correct directories. They will *not* be tracked by git.

1.  **Whisper Model:**
    *   Download the `faster-whisper-base-en` (or equivalent int8 quantization) model files.
    *   Place the `model.bin`, `config.json`, and `vocabulary.txt` inside `./.models/whisper/`
2.  **Phi-3 SLM:**
    *   Download `Phi-3-mini-4k-instruct-q4.gguf` from HuggingFace (e.g., from TheBloke or Microsoft).
    *   Place the `.gguf` file strictly at `./.models/slm/phi3-mini-4k.gguf`

## 4. Local Dependency Setup
We use `uv` for isolated, fast dependency resolution.

```bash
# 1. Install uv (if not installed)
pip install uv

# 2. Create the virtual environment pinned to Python 3.11
uv venv -p 3.11

# 3. Activate the environment
# On Mac/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# 4. Install dependencies strictly from the pinned requirements
uv pip install -r requirements.txt
```

## 5. Pre-commit & Ready State
Install the pre-commit hooks to guarantee code cleanliness:
```bash
pre-commit install
```

You are now fully configured. You may disconnect from the internet. Run the engine via:
```bash
python src/app/dashboard.py
```
