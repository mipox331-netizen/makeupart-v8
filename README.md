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

Status checked on 27 October 2026.

The latest public APK is [MakeupArt V8 v8.0.201](https://github.com/mipox331-netizen/makeupart-v8/releases/tag/v8.0.201), published on 23 October 2026. [Download MakeupArt-V8.apk](https://github.com/mipox331-netizen/makeupart-v8/releases/download/v8.0.201/MakeupArt-V8.apk). The release workflow [#201](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39967233385) built it from commit `3a666d4ff610c30fcc6342a71204cba2b288ada1`. Its logs explicitly show that `ANDROID_KEYSTORE_BASE64` was absent and the APK was signed with Flutter's **Android Debug** certificate. It is for manual sideloading only; it is not Play Store-ready and may not update an app signed with another key.

The current `main` source is commit [`ac9921f`](https://github.com/mipox331-netizen/makeupart-v8/commit/ac9921fbc7367c2c311026c7361c489a4be7eff4). Main CI [#678](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40121282729) passed on that commit. It includes fixes merged after the v8.0.201 APK was built, so **the public APK is older than the current source**. PR [#40](https://github.com/mipox331-netizen/makeupart-v8/pull/40) hardens release automation to reject stale commits and require the matching commit's dependency-security and license checks before attempting publication; its checks must pass before merge.

The Android client targets the Render API at `https://makeupart-api.onrender.com/api/v1`, with Supabase as the intended PostgreSQL database. Production monitor [#701](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40563215368) passed liveness and readiness on 27 October. That monitor checks service status but does not log the deployed source SHA, and it does not prove an end-to-end photo upload/recovery.

For an update-compatible release, all four GitHub `production` environment secrets must be configured from the **same persistent keystore used by the installed app**: `ANDROID_KEYSTORE_BASE64`, `ANDROID_STORE_PASSWORD`, `ANDROID_KEY_PASSWORD`, and `ANDROID_KEY_ALIAS`. The current release workflow deliberately refuses to publish with an ephemeral debug key. After a new signed APK is built, run real-device smoke tests before declaring it production-ready.


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

Production mode now fails closed when Google Drive credentials or access are missing, even if the legacy `REQUIRE_DURABLE_MEDIA` flag is `false`; `/health/ready` returns HTTP 503 instead of treating local-only photos as durable. Configure the Google Drive OAuth variables on the Render service and separately in the GitHub `production` environment. Do not declare photo durability complete until a real app upload, a service restart, restored image downloads and matching checksums succeed.

Existing photos are not backfilled automatically: run `backend/scripts/backfill_media_to_google_drive.py` against files that are still accessible. Photos that existed only on a lost ephemeral filesystem cannot be recovered by code changes alone.

The latest encrypted database backup [#48](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40441672336) and isolated database restore drill [#58](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40441747764) both passed on 27 October. The encrypted media backup [#53](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40442965971) failed because the private Drive inventory contained 0 files / 0 bytes; its restore drill [#53](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40442985353) was skipped. The media workflow intentionally refuses to report success for an empty archive. Customer photo/logo recovery is not proven until a real authorized image is uploaded by the running app, survives a service restart, and is recovered with a matching checksum. Set a unique passphrase of at least 24 characters in the `production` GitHub environment and store it safely offline. Before depending on database recovery, verify that the runtime `DATABASE_URL` and backup URL point at the same live Supabase database and complete a restore drill.

## Licensing and AI capabilities

Original MakeupArt V8 project code is proprietary; see [LICENSE](LICENSE). Third-party components retain their own licenses. Review the [third-party license audit record](docs/THIRD_PARTY_LICENSE_AUDIT.md) before commercial distribution.

Classic enhancement uses MediaPipe face landmarks and OpenCV effects, including face-aware lipstick, blush, eyeshadow and eyeliner/wing presets. This is a lightweight local effect—not a FaceApp-equivalent generative reference-image transfer model. The optional OpenAI image-edit path is disabled without server-side credentials and may incur provider costs; for a $0 operating budget, keep classic mode as the default.

The app checks GitHub Releases and prompts users to download newer APKs. Android still requires the user to approve installation. No successful Google Play publication or signed iOS distribution is verified.

See [release readiness](docs/RELEASE_READINESS.md), [mobile release notes](docs/MOBILE_RELEASE.md), [AI and model licensing](docs/AI_CAPABILITIES_AND_LICENSES.md), and [production runbook](docs/PRODUCTION_RUNBOOK.md).
