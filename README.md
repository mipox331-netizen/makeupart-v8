# MakeupArt V8

MakeupArt V8 is a salon-first beauty AI MVP with a FastAPI/PostgreSQL backend and Flutter mobile client.

## Project layout
- backend/ — API, database migrations, beauty processing and tests
- makeup_art_v8/ — Flutter mobile app
- docs/ — architecture and delivery notes

## Backend
Copy backend/.env.example to backend/.env and set a real SECRET_KEY outside test environments.

From backend/:
docker compose up --build

The API runs on port 8000 and health is available at /health.

## Flutter
From makeup_art_v8/:
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1

Use your computer LAN address instead of 10.0.2.2 when testing a physical device.

## Security
- Never commit .env.
- Production must use explicit CORS_ORIGINS.
- Client consent is required before image processing.
- Customer-linked processing requires active stored consent when consent_required is enabled.
- Production should use HTTPS and private durable media storage.

## Verification
GitHub Actions runs backend Docker/migrations/tests and Flutter analyze/tests on pushes to main.
