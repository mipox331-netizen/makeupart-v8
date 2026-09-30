# MakeupArt V8

MakeupArt V8 is a salon-first beauty AI MVP with a FastAPI/PostgreSQL backend and Flutter mobile client.

## Project layout
- `backend/` — API, database migrations, beauty processing, maintenance and tests
- `makeup_art_v8/` — Flutter mobile app
- `docs/` — architecture, implementation and production runbook

## Backend development
From `backend/`:

```bash
cp .env.example .env
docker compose up --build
```

The API runs on port 8000. Health endpoints are:
- `/health`
- `/health/live`
- `/health/ready`

## Flutter development
From `makeup_art_v8/`:

```bash
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1
```

Use the computer's LAN address instead of `10.0.2.2` on a physical device.

## Production
Production deployment is packaged in `backend/docker-compose.production.yml` with PostgreSQL, private media volume, daily cleanup, and Caddy HTTPS termination.

See `docs/PRODUCTION_RUNBOOK.md` before deploying.

## Security
- Never commit environment files.
- Production requires explicit CORS configuration and a strong secret.
- Client consent is required before image processing.
- Customer-linked processing requires active stored consent when configured.
- Media is salon-isolated and served only through authenticated routes.
- Customer deletion removes associated consent, consultation, job and media data.

## Verification
GitHub Actions verifies:
- PostgreSQL and Alembic migrations
- backend pytest
- FastAPI startup and health
- Flutter dependency resolution, analyze and tests
- production Compose configuration
- Android debug build when platform files are present
