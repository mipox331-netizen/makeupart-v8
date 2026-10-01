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


## Physical Android phone testing

The default Android debug build targets the Android Emulator at `10.0.2.2`.
For a physical phone, the APK must use the backend machine's reachable API address, for example:

```text
http://192.168.1.20:8000/api/v1
```

In GitHub Actions, use **Run workflow** and set the `api_base_url` input to build a debug APK for that device/network without changing source code.

The phone and backend machine must be on a network that allows the phone to reach the API.


## Cloud deployment

The backend can run independently of a personal computer using Render. The repository includes a `render.yaml` Blueprint that provisions the Docker API service and managed PostgreSQL, with persistent media storage.

The production mobile build should point `API_BASE_URL` at the deployed Render HTTPS API URL, for example:
`https://<your-render-service>.onrender.com/api/v1`.

Render production requires a paid web service for the attached persistent disk used by uploaded and generated images. Render's managed PostgreSQL connection is wired privately through `fromDatabase`.
