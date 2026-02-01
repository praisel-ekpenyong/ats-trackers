# ATS Tracker

A general-purpose ATS Tracker web app for personal resume optimization. The app simulates recruiter-style ATS matching with transparent scoring channels. It is **not** for automating hiring decisions.

## Features
- Hybrid matching (normalization map + open-vocabulary extraction + Boolean search simulation).
- Transparent scoring channels with per-term explainability.
- Multi-resume and multi-job storage backed by SQLite.
- Streamlit UI with tabs for ingest, matches, drill-down, normalization, and search.

## Windows Setup

1. **Create a virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app**
   ```bash
   streamlit run app.py
   ```

## Notes
- PDF text extraction uses `pdfplumber` and warns if the extracted text is very small (likely a scanned PDF).
- Normalization map lives in `normalization.json` and can be edited in the UI.
- Scoring weights live in `config.json`.

## Self-check
You can run a lightweight self-check from Python:
```bash
python -c "from score import self_check; print(self_check())"
```
