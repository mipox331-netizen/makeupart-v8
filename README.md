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

The latest public Android APK is [MakeupArt V8 v8.0.169](https://github.com/mipox331-netizen/makeupart-v8/releases/tag/v8.0.169). [Download MakeupArt-V8.apk](https://github.com/mipox331-netizen/makeupart-v8/releases/download/v8.0.169/MakeupArt-V8.apk). It was published on 15 October 2026; it is the last published build, not proof that the current source has deployed successfully.

That published APK still points to `https://makeupart-api.onrender.com/api/v1`. The current release workflow on `main` now targets the Modal API at `https://mipox331-netizen--makeupart-v8-api-fastapi-app.modal.run/api/v1`, but a replacement APK has not yet passed production checks. On 20 October 2026, the latest Modal deployment run failed with `Token not found`, and the Android release run failed because the Android signing secrets were incomplete. The current public APK therefore must not be treated as proof of a working connection to the current production backend.

For a reliable upgrade path, configure all four Android signing secrets using the same release keystore that signed the installed build. A different signing key can prevent Android from installing an update over an existing copy. A passing build and API health check still need to be followed by a real-device sign-in/photo-save smoke test before calling the release production-ready.

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

The backend now contains a private Google Drive media adapter for salon logos and before/after photos. It uses Google's OAuth `drive.file` scope, stores objects privately, verifies restored content, and can restore missing local media. The Modal deployment workflow passes `GOOGLE_DRIVE_CLIENT_ID`, `GOOGLE_DRIVE_CLIENT_SECRET`, and `GOOGLE_DRIVE_REFRESH_TOKEN` from the selected GitHub environment into the deployed service when those secrets are configured. **Drive durability is not active or verified until those credentials are set and a real upload plus restore after a service restart succeeds.**

Keep the GitHub environment variable `REQUIRE_DURABLE_MEDIA=false` during setup. After OAuth is configured and a real photo/logo upload and restore are verified, set it to `true` so readiness fails closed instead of silently accepting local-only media. Setting it to true before Drive is configured intentionally makes `/health/ready` return HTTP 503.

Existing photos are not backfilled automatically: run `backend/scripts/backfill_media_to_google_drive.py` against files that are still accessible. Photos that existed only on a lost ephemeral filesystem cannot be recovered by code changes alone.

The encrypted media-backup workflow currently archives the Modal media volume; it is not an independent backup of the Google Drive account. The most recent database and media backup workflows failed because `BACKUP_ENCRYPTION_PASSPHRASE` was missing, so there is no confirmed current encrypted backup/restore proof. Set a unique passphrase of at least 24 characters in the `production` GitHub environment and store it safely offline. Before depending on database recovery, verify that the runtime `DATABASE_URL` and backup URL point at the same live Supabase database and complete a restore drill.

## Licensing and AI capabilities

Original MakeupArt V8 project code is proprietary; see [LICENSE](LICENSE). Third-party components retain their own licenses. Review the [third-party license audit record](docs/THIRD_PARTY_LICENSE_AUDIT.md) before commercial distribution.

Classic enhancement uses MediaPipe face landmarks and OpenCV effects, including face-aware lipstick, blush, eyeshadow and eyeliner/wing presets. This is a lightweight local effect—not a FaceApp-equivalent generative reference-image transfer model. The optional OpenAI image-edit path is disabled without server-side credentials and may incur provider costs; for a $0 operating budget, keep classic mode as the default.

The app checks GitHub Releases and prompts users to download newer APKs. Android still requires the user to approve installation. No successful Google Play publication or signed iOS distribution is verified.

See [release readiness](docs/RELEASE_READINESS.md), [mobile release notes](docs/MOBILE_RELEASE.md), [AI and model licensing](docs/AI_CAPABILITIES_AND_LICENSES.md), and [production runbook](docs/PRODUCTION_RUNBOOK.md).
