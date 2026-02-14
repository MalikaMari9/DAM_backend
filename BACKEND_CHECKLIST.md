# Backend Checklist (Air Pollution × Health DAM)

This checklist maps the intended platform design to the current backend. Mark items as `done` / `blocked` / `missing`.

## 1. Core Config & Security
- [x] `DATABASE_URL` and `JWT_SECRET_KEY` set. (done)
- [ ] `JWT_ALGORITHM`, `JWT_EXPIRES_MINUTES`, `FRONTEND_BASE_URL` set correctly for the environment. (needs confirm)
- [ ] CORS allows the frontend URL. (needs confirm; currently hardcoded to `http://localhost:8080` and `http://127.0.0.1:8080`)
- [ ] Password hashing (bcrypt/passlib) works on the target machine. (needs confirm)

## 2. PostgreSQL Schema & Constraints
- [x] Enums exist: `account_role_enum`, `application_status_enum`, `data_domain_enum`, `org_status_enum`, `org_type_enum`, `upload_status_enum`. (done)
- [x] Tables exist: `account_tbl`, `org_tbl`, `org_application_tbl`, `org_application_file_tbl`, `upload_tbl`, `password_reset_tbl`. (done)
- [x] Constraint: ORG accounts must reference `org_id`, ADMIN must be `NULL`. (done)
- [x] Unique index: `ux_account_email` on `lower(email)`. (done)
- [x] Unique index: `ux_org_official_email` on `lower(official_email)`. (done)
- [x] Unique index: `ux_upload_mongo_ref` on `(mongo_collection, mongo_ref_id)`. (done)
- [x] Trigger `trg_enforce_upload_org_rules` exists. (done)

## 3. Auth & Access Control
- [x] `POST /auth/login` returns JWT. (done)
- [x] `GET /auth/me` requires JWT. (done)
- [x] `POST /auth/change-password` requires JWT. (done)
- [x] `POST /auth/forgot-password` sends reset link. (done)
- [x] `POST /auth/reset-password` validates token. (done)
- [x] Admin-only routes guarded: `/admin/*`, `/orgs`, `/org-applications` list/review, `/files` list. (done)
- [x] Org-only routes guarded: `/orgs/me`, `/uploads` create. (done)

## 4. Onboarding Workflow
- [x] `POST /org-applications` creates application. (done)
- [x] `POST /files/applications/{application_id}` stores file + metadata. (done)
- [x] Admin can list applications by status and review. (done)
- [x] Approval creates `org_tbl` record. (done)
- [x] Approval creates ORG account. (done)
- [x] Approval emails temp password to official/contact email. (done)
- [x] Rejection updates status + optional `admin_note`. (done)
- [x] Rejection emails decision to official/contact email. (done)

## 5. Organization Management
- [x] Admin can list orgs. (done)
- [x] Admin can update org profile/status (including `SUSPENDED`). (done)
- [x] Org can view its own org profile (`/orgs/me`). (done)
- [x] Admin can create org account directly (`/admin/users/org`). (done)

## 6. Uploads (Metadata Governance)
- [x] Org creates upload record with `mongo_collection` + `mongo_ref_id`. (done)
- [x] Trigger enforces org/account/data_domain/country rules. (done)
- [x] Admin can update upload `status` and `error_message`. (done)

## 7. MongoDB Integration (Big-Data Layer)
- [ ] Mongo connection config exists. (missing in backend code)
- [ ] Raw dataset stored in Mongo on ingest. (missing in backend code)
- [ ] `mongo_collection` + `mongo_ref_id` returned and recorded in Postgres. (missing in backend code)
- [x] Duplicate ingest blocked by unique constraint. (done)

## 8. File Storage
- [x] `UPLOAD_DIR` exists or is created. (done)
- [x] `MAX_UPLOAD_BYTES` enforced. (done)
- [x] File metadata stored in `org_application_file_tbl`. (done)

## 9. Tests
- [x] Tests pass locally. (done)
- [ ] Coverage for org application approval flow. (missing)
- [ ] Coverage for upload trigger rules. (missing)
- [ ] Coverage for reset password expiry/used tokens. (missing)
- [ ] Coverage for role-guarded admin/org routes. (missing)
