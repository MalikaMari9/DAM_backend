# AI Service (Port 9000)

This service powers `/api/chat` and PM2.5/health prediction endpoints.

## Run locally

1. `cd backend/ai_service`
2. `python -m venv .venv`
3. `.venv\Scripts\activate`
4. `pip install -r requirements.txt`
5. `python app.py`

The service listens on `http://127.0.0.1:9000`.

## Optional env vars

- `AI_IHME_RAW_PATH`: path to large raw IHME JSON for age-stratified detail.
  If unset or missing, service falls back to baseline aggregation.
