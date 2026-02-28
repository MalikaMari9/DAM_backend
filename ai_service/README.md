# AI Service (Port 9010)

This is the upgraded AI service integrated from `PollutionKKK/Pollution ETL/AntiDev/webapp`.

## Run locally

1. `cd backend/ai_service`
2. `python -m venv .venv`
3. `.venv\Scripts\activate`
4. `pip install -r requirements.txt`
5. `python app.py`

Service URL: `http://127.0.0.1:9010`

## Backend proxy wiring

Your main backend forwards chat requests from:

- `POST /ai/chat` (backend app) -> `POST /api/chat` (this service)

Configure backend `.env`:

```env
AI_MODEL_BASE_URL=http://127.0.0.1:9010
```

## Optional env vars

- `AI_IHME_RAW_PATH`: absolute path to raw IHME JSON (`health_ihme_clean.json`).
  If not set, the service tries local fallback paths.
- `AI_SERVICE_PORT`: service port (default `9010`).
