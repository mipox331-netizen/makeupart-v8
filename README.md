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

Status checked on 23 October 2026.

The latest public APK is [MakeupArt V8 v8.0.195](https://github.com/mipox331-netizen/makeupart-v8/releases/tag/v8.0.195), published on 22 October 2026. [Download MakeupArt-V8.apk](https://github.com/mipox331-netizen/makeupart-v8/releases/download/v8.0.195/MakeupArt-V8.apk). This artifact was built from commit `6ac6233cb1ef1e5e88c3d4009f9c26618c37a9d9`, not from the latest `main` source. The release workflow reported that `ANDROID_KEYSTORE_BASE64` was missing and signed the APK with Flutter's debug key. It is for manual sideloading only; it is not Play Store-ready and may not update an existing installation signed with another key.

The active API target documented for the Android client is the Render service at `https://makeupart-api.onrender.com/api/v1`; Supabase is the intended PostgreSQL database. Production monitor [#508](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39906865481) passed liveness and readiness checks on 23 October. Those probes alone do not identify the running commit or prove that a photo can be uploaded and recovered.

The latest `main` commit at the time of this audit is [`8b2aee9`](https://github.com/mipox331-netizen/makeupart-v8/commit/8b2aee9269628e58089a89cf3486bb385932179f). Android workflow [#196](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39814335881) classified that backend change successfully but skipped its APK-build job. Therefore, there is no verified APK built from that latest source. The proposed release-hardening change adds the running Render commit to `/health/ready` and makes the APK workflow wait for an exact commit match before building, so a skipped or stale release cannot be mistaken for a completed build.

For update-compatible releases, configure all four Android signing secrets (`ANDROID_KEYSTORE_BASE64`, `ANDROID_STORE_PASSWORD`, `ANDROID_KEY_PASSWORD`, and `ANDROID_KEY_ALIAS`) using the same persistent release keystore as the installed app. Never generate a different key for an update intended to replace an existing installation. After a signed APK is built, run a real-device sign-in and photo-save smoke test before calling the release production-ready.

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

The backend now contains a private Google Drive media adapter for salon logos and before/after photos. It uses Google's OAuth `drive.file` scope, stores objects privately, verifies restored content, and can restore missing local media. The legacy Modal deployment workflow can pass `GOOGLE_DRIVE_CLIENT_ID`, `GOOGLE_DRIVE_CLIENT_SECRET`, and `GOOGLE_DRIVE_REFRESH_TOKEN` into Modal; the active Render service requires these variables to be set separately in Render's environment settings. **Drive durability is not active or verified until those credentials are set and a real upload plus restore after a service restart succeeds.**

Keep the GitHub environment variable `REQUIRE_DURABLE_MEDIA=false` during setup. After OAuth is configured and a real photo/logo upload and restore are verified, set it to `true` so readiness fails closed instead of silently accepting local-only media. Setting it to true before Drive is configured intentionally makes `/health/ready` return HTTP 503.

Existing photos are not backfilled automatically: run `backend/scripts/backfill_media_to_google_drive.py` against files that are still accessible. Photos that existed only on a lost ephemeral filesystem cannot be recovered by code changes alone.

The encrypted database backup [#44](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39892512971) and isolated database restore drill [#54](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39892567266) both passed on 23 October. The current encrypted media backup [#48](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39893692218) failed because the private Drive inventory contained 0 files / 0 bytes; its restore drill was skipped. The media workflow intentionally refuses to report success for an empty archive. Customer photo/logo recovery is not proven until a real authorized image is uploaded by the running app, survives a service restart, and is recovered with a matching checksum. Set a unique passphrase of at least 24 characters in the `production` GitHub environment and store it safely offline. Before depending on database recovery, verify that the runtime `DATABASE_URL` and backup URL point at the same live Supabase database and complete a restore drill.

## Licensing and AI capabilities

Original MakeupArt V8 project code is proprietary; see [LICENSE](LICENSE). Third-party components retain their own licenses. Review the [third-party license audit record](docs/THIRD_PARTY_LICENSE_AUDIT.md) before commercial distribution.

Classic enhancement uses MediaPipe face landmarks and OpenCV effects, including face-aware lipstick, blush, eyeshadow and eyeliner/wing presets. This is a lightweight local effect—not a FaceApp-equivalent generative reference-image transfer model. The optional OpenAI image-edit path is disabled without server-side credentials and may incur provider costs; for a $0 operating budget, keep classic mode as the default.

The app checks GitHub Releases and prompts users to download newer APKs. Android still requires the user to approve installation. No successful Google Play publication or signed iOS distribution is verified.

See [release readiness](docs/RELEASE_READINESS.md), [mobile release notes](docs/MOBILE_RELEASE.md), [AI and model licensing](docs/AI_CAPABILITIES_AND_LICENSES.md), and [production runbook](docs/PRODUCTION_RUNBOOK.md).
