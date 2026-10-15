# MakeupArt V8

MakeupArt V8 is a salon-first beauty application with a Flutter Android client and a FastAPI/PostgreSQL backend.

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

The API runs on port 8000. Health endpoints are `/health`, `/health/live`, and `/health/ready`.

## Flutter development
From `makeup_art_v8/`:

```bash
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1
```

Use the computer's LAN address instead of `10.0.2.2` on a physical device.

## Current production and Android release

The current Android release is [MakeupArt V8 v8.0.164](https://github.com/mipox331-netizen/makeupart-v8/releases/tag/v8.0.164). [Download MakeupArt-V8.apk](https://github.com/mipox331-netizen/makeupart-v8/releases/download/v8.0.164/MakeupArt-V8.apk).

The release workflow passed Flutter analysis/tests, production API liveness/readiness checks, APK build and APK signature verification: [run #164](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38699306152). The workflow reported that Android release-signing secrets are not configured and used Flutter's debug signing key. This APK is for manual installation, not Google Play publication.

The APK targets the Render endpoint `https://makeupart-api.onrender.com/api/v1`. The connected Render workspace shows `makeupart-api` on the free plan. A free service can have cold starts; recent monitor checks pass but an earlier check timed out. Basic monitoring and release health checks now retry transient network/gateway failures once.

The repository retains a separate Modal deployment path. The current APK does **not** use that Modal endpoint. Modal's media-backup workflow still targets the separate `makeupart-v8-media` volume and has recently failed; do not treat it as a backup of files stored on Render.

## Backend development stack
The API uses FastAPI, PostgreSQL and Alembic. GitHub Actions checks migrations, backend tests, Flutter analysis/tests, the Android build and production health. See [release readiness](docs/RELEASE_READINESS.md) for live evidence and remaining blockers.

The checked-in Docker Compose + Caddy stack remains available as a self-hosted deployment option. See `docs/PRODUCTION_RUNBOOK.md`.

## Security
- Never commit environment files or provider credentials.
- Production requires explicit CORS configuration and a strong secret.
- Client consent is required before image processing.
- Customer-linked processing requires active stored consent when configured.
- Media routes authenticate requests and enforce salon isolation.
- Customer deletion removes associated consent, consultation, job and media records.
- Classic MediaPipe/OpenCV processing works without a paid external image-provider key.

## Photo durability and disaster recovery

The backend currently writes image files below its configured `MEDIA_ROOT`. The live Render service metadata does not show a persistent disk attached, while the existing encrypted media-backup workflow downloads a separate Modal volume. These locations are not proven to contain the same files. Before real customer photos are relied on, connect the live API to a durable object store and back up/restore that exact storage source.

Database backup and restore workflows have passed, but the runtime Render `DATABASE_URL` target has not been verified against the Supabase database URL selected by the backup workflow. The connected workspace also contains a free Render PostgreSQL resource expiring on 31 October 2026. Do not delete or rely on either database until the live connection target is confirmed.

## Licensing and AI capabilities

Original MakeupArt V8 project code is proprietary; see [LICENSE](LICENSE). Third-party components retain their own licenses. Review the [third-party license audit record](docs/THIRD_PARTY_LICENSE_AUDIT.md) before commercial distribution.

Classic enhancement uses MediaPipe face landmarks and OpenCV effects, including face-aware lipstick, blush, eyeshadow and eyeliner/wing presets. This is a lightweight local effect—not a FaceApp-equivalent generative reference-image transfer model. The optional OpenAI image-edit path is disabled without server-side credentials and may incur provider costs; for a $0 operating budget, keep classic mode as the default.

The app checks GitHub Releases and prompts users to download newer APKs. Android still requires the user to approve installation. No successful Google Play publication or signed iOS distribution is verified.

See [release readiness](docs/RELEASE_READINESS.md), [mobile release notes](docs/MOBILE_RELEASE.md), [AI and model licensing](docs/AI_CAPABILITIES_AND_LICENSES.md), and [production runbook](docs/PRODUCTION_RUNBOOK.md).
