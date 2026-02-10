# SAP v3

Security Analyst Platform v3 (SAP v3) implements deterministic user access reviews with regulatory-grade auditability for banking-focused security operations.

## Architecture

- Backend: FastAPI + SQLAlchemy (`/backend`)
- Frontend: React + TypeScript + Tailwind (`/frontend`)
- Database: PostgreSQL (single DB)
- Deployment: Railway (single web service + single PostgreSQL service)

The frontend is built and served from the same web service runtime.

## Features in this baseline

- Invite-based registration, login, refresh token rotation, role-based access
- Framework and application management
- Review workflow lifecycle:
  - create review
  - upload document
  - extraction and confirmation
  - deterministic analysis
  - findings disposition
  - review approval
- Reference dataset upload and attachment
- Hash-chained audit log and verification endpoint
- Health and readiness endpoints

## Local Development

### 1) Environment

```bash
cp .env.example .env
```

### 2) Run with Docker Compose

```bash
docker compose up --build
```

Backend/API: [http://localhost:8000](http://localhost:8000)

### 3) Run without Docker

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Frontend dev URL: [http://localhost:5173](http://localhost:5173)

## Bootstrap scripts

Create initial admin:

```bash
cd backend
python -m app.scripts.create_initial_admin
```

Seed Fedlink starter framework/application/template:

```bash
cd backend
python -m app.scripts.seed_fedlink_starter
```

## Railway Deployment

1. Create Railway project and PostgreSQL service.
2. Link this GitHub repo to Railway.
3. Configure environment variables:
- `DATABASE_URL`
- `SECRET_KEY`
- `APP_ENV=production`
- `CORS_ORIGINS` (JSON array)
4. Ensure healthcheck path is `/health`.

`railway.toml` is already included for Dockerfile deployment.

## Tests

Backend:

```bash
cd backend
pytest
```

Frontend build/typecheck:

```bash
cd frontend
npm run typecheck
npm run build
```
