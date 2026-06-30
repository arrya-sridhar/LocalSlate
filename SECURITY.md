# Security Policy

## Offline-First Guarantee
LocalSlate is built with a zero network footprint specification. All data processing (transcription, structured data extraction, and relational database storage) happens locally on physical hardware:
- Outbound network requests are disabled.
- No remote telemetry or cloud services are contacted.
- Model loading, weight inference, and transactions run fully sandbox-isolated.

## Host System Safety
- **RAM Limits**: An OS Memory watchdog monitors host RAM usage. Inference is aborted if allocation approaches `3.8GB` or system RAM exceeds `95%` to prevent host system instability.
- **Audio Pruning**: Raw audio files are securely unlinked (`deleted`) from the local file system immediately after transcription is completed to avoid leaks.
- **File Bounds**: Input file size is validated to prevent buffer overflow/exhaustion attacks (maximum of 25MB for WAV files, and 4000 characters for raw text notes).

## Reporting Vulnerabilities
If you discover a security issue or local resource leak:
1. Open a local GitLab issue under security classification.
2. Provide local system diagnostic logs from `data/localslate.log`.
