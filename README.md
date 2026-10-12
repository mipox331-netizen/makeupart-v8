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
The live production backend runs on Modal with Supabase PostgreSQL. The production API is:
`https://mipox331-netizen--makeupart-v8-api-fastapi-app.modal.run`

GitHub Actions deploys the backend, runs Alembic migrations, verifies the migration head, verifies MediaPipe + OpenCV image-preservation runtime, and checks `/health/ready`.

The checked-in Docker Compose + Caddy stack remains available as a self-hosted deployment option. See `docs/PRODUCTION_RUNBOOK.md`.

## Licensing

Original MakeupArt V8 project code is proprietary; see [LICENSE](LICENSE). Third-party components retain their own licenses. The [third-party license audit record](docs/THIRD_PARTY_LICENSE_AUDIT.md) explains the automated inventory and the remaining manual review required before commercial distribution.

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

The primary cloud deployment is Modal + Supabase. Android production builds use the Modal API URL through `API_BASE_URL`.

Project administration is controlled by the production secret `PLATFORM_ADMIN_EMAILS` (comma-separated e-mail addresses). Platform admins can view users, see blocked accounts, block/unblock users, and manage salon subscriptions.

All newly registered salons start on a permanent Free plan with a monthly AI-processing quota; no payment is required to start using the app.


## Release readiness

- Current Android download: [MakeupArt V8 v8.0.145](https://github.com/mipox331-netizen/makeupart-v8/releases/download/v8.0.145/MakeupArt-V8.apk).
- The app checks GitHub Releases for a newer APK and prompts the user to download it; Android confirmation is still required to install.
- The current beauty effect uses MediaPipe + OpenCV and is not generative makeup.
- Google Play, iOS distribution, database/media disaster recovery and the full third-party dependency/model-asset license audit have separate release gates.

See [release-readiness dashboard](docs/RELEASE_READINESS.md), [AI and model licensing](docs/AI_CAPABILITIES_AND_LICENSES.md), [mobile release notes](docs/MOBILE_RELEASE.md), and [production runbook](docs/PRODUCTION_RUNBOOK.md).
