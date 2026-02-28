# Backend README

FastAPI backend for the AirHealth project.

## Requirements
- Python 3.11+ (tested with 3.13)
- PostgreSQL
- (Optional) Gmail App Password for SMTP

## Setup
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Environment (.env)
Create or update `backend/.env` with:
```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/airpollutionhealth
JWT_SECRET_KEY=your_jwt_secret
JWT_ALGORITHM=HS256
JWT_EXPIRES_MINUTES=60
UPLOAD_DIR=uploads
MAX_UPLOAD_BYTES=10485760

# Frontend for reset links
FRONTEND_BASE_URL=http://localhost:8080

# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB_POLLUTION=Pollution
MONGO_COLLECTION_ACAG=ACAG
MONGO_COLLECTION_ACAG_PRED=ACAGPred
ACAG_PRED_START_YEAR=2020

# AI chat upstream (proxy target)
AI_MODEL_BASE_URL=http://127.0.0.1:9010

# SMTP (Gmail App Password)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_gmail_app_password
SMTP_FROM=AirHealth <your_email@gmail.com>
```

## Run
```powershell
uvicorn app.main:app --reload
```

API docs: `http://127.0.0.1:8000/docs`

## AI Integration

Frontend remains unchanged and still calls:
- `POST /ai/chat` on backend

Backend forwards that request to:
- `POST /api/chat` on AI service (`backend/ai_service`)

Run AI service in a separate terminal:
```powershell
cd backend/ai_service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Then run backend API:
```powershell
cd backend
uvicorn app.main:app --reload
```

## Database Notes
### Password reset table (required)
```sql
CREATE TABLE IF NOT EXISTS password_reset_tbl (
  reset_id BIGSERIAL PRIMARY KEY,
  account_id BIGINT NOT NULL REFERENCES account_tbl(account_id) ON DELETE CASCADE,
  token_hash TEXT NOT NULL UNIQUE,
  expires_at TIMESTAMPTZ NOT NULL,
  used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_password_reset_account_id ON password_reset_tbl(account_id);
CREATE INDEX IF NOT EXISTS idx_password_reset_expires_at ON password_reset_tbl(expires_at);
```

### Admin account
You must have at least one admin account in `account_tbl`.
If bcrypt/passlib fails, pin:
```powershell
pip install "bcrypt==4.0.1"
```

## Key Endpoints (Summary)
**Auth**
- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/change-password`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`

**Org Applications**
- `POST /org-applications` (public)
- `GET /org-applications` (admin)
- `PATCH /org-applications/{id}` (admin)

**Organizations**
- `GET /orgs` (admin)
- `GET /orgs/me` (org)
- `PATCH /orgs/{id}` (admin)

**Files**
- `POST /files/applications/{application_id}` (public)
- `GET /files/applications/{application_id}` (admin)

**Admin**
- `POST /admin/users/admin` (admin)
- `POST /admin/users/org` (admin)

**AI**
- `POST /ai/chat` (proxy to AI service)

## Tests
```powershell
pytest -q
```

## Notes
- The health endpoint path is currently `/healtsh` (intentional typo for testing).
- Email sending is best‑effort; failures do not block request processing.
