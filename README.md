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

Status checked on 24 October 2026.

The latest public APK is [MakeupArt V8 v8.0.195](https://github.com/mipox331-netizen/makeupart-v8/releases/tag/v8.0.195), published on 22 October 2026. [Download MakeupArt-V8.apk](https://github.com/mipox331-netizen/makeupart-v8/releases/download/v8.0.195/MakeupArt-V8.apk). This artifact was built from commit `6ac6233cb1ef1e5e88c3d4009f9c26618c37a9d9`, not from the latest `main` source. The release workflow reported that `ANDROID_KEYSTORE_BASE64` was missing and signed the APK with Flutter's debug key. It is for manual sideloading only; it is not Play Store-ready and may not update an existing installation signed with another key.

The active API target documented for the Android client is the Render service at `https://makeupart-api.onrender.com/api/v1`; Supabase is the intended PostgreSQL database. Production monitor [#508](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39906865481) passed liveness and readiness checks on 23 October. Those probes alone do not identify the running commit or prove that a photo can be uploaded and recovered.

The latest `main` commit is [`bf8a3ec`](https://github.com/mipox331-netizen/makeupart-v8/commit/bf8a3ec09067b49cd2a4a41a9e11d994cc82634d), which includes the permanent Google Drive media-deletion fix. PR validation on source commit [`63712b8`](https://github.com/mipox331-netizen/makeupart-v8/commit/63712b8f248118782be4d6fb1ce5a67544863c08) passed backend migrations/tests, Flutter analysis/tests, Android debug APK build, Python dependency audit and third-party license inventory ([CI #652](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40108060325), [dependency audit #173](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40108060323), [license inventory #192](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40108060418)). The APK produced by that PR check is a debug-signed validation artifact, not a production release. No newer public release APK is verified yet. The readiness endpoint now reports `deployment_commit`, and the release workflow requires the exact backend commit plus persistent release signing before publishing; the post-merge production deployment and release still need their own successful run.

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

The backend contains a private Google Drive media adapter for salon logos and before/after photos. It uses Google's OAuth `drive.file` scope, stores objects privately, verifies restored content, can restore missing local media, and now permanently deletes matched media with the Drive `files.delete` endpoint instead of moving it to Trash. The permanent-deletion regression test passed in PR validation; a live production deletion was not exercised. The legacy Modal deployment workflow can pass `GOOGLE_DRIVE_CLIENT_ID`, `GOOGLE_DRIVE_CLIENT_SECRET`, and `GOOGLE_DRIVE_REFRESH_TOKEN` into Modal; the active Render service requires these variables to be set separately in Render's environment settings. **Drive durability is not active or verified until those credentials are set and a real upload plus restore after a service restart succeeds.**

Production mode now fails closed when Google Drive credentials or access are missing, even if the legacy `REQUIRE_DURABLE_MEDIA` flag is `false`; `/health/ready` returns HTTP 503 instead of treating local-only photos as durable. Configure the Google Drive OAuth variables on the Render service and separately in the GitHub `production` environment. Do not declare photo durability complete until a real app upload, a service restart, restored image downloads and matching checksums succeed.

Existing photos are not backfilled automatically: run `backend/scripts/backfill_media_to_google_drive.py` against files that are still accessible. Photos that existed only on a lost ephemeral filesystem cannot be recovered by code changes alone.

The encrypted database backup [#44](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39892512971) and isolated database restore drill [#54](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39892567266) both passed on 23 October. The current encrypted media backup [#48](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39893692218) failed because the private Drive inventory contained 0 files / 0 bytes; its restore drill was skipped. The media workflow intentionally refuses to report success for an empty archive. Customer photo/logo recovery is not proven until a real authorized image is uploaded by the running app, survives a service restart, and is recovered with a matching checksum. Set a unique passphrase of at least 24 characters in the `production` GitHub environment and store it safely offline. Before depending on database recovery, verify that the runtime `DATABASE_URL` and backup URL point at the same live Supabase database and complete a restore drill.

## Licensing and AI capabilities

Original MakeupArt V8 project code is proprietary; see [LICENSE](LICENSE). Third-party components retain their own licenses. Review the [third-party license audit record](docs/THIRD_PARTY_LICENSE_AUDIT.md) before commercial distribution.

Classic enhancement uses MediaPipe face landmarks and OpenCV effects, including face-aware lipstick, blush, eyeshadow and eyeliner/wing presets. This is a lightweight local effect—not a FaceApp-equivalent generative reference-image transfer model. The optional OpenAI image-edit path is disabled without server-side credentials and may incur provider costs; for a $0 operating budget, keep classic mode as the default.

The app checks GitHub Releases and prompts users to download newer APKs. Android still requires the user to approve installation. No successful Google Play publication or signed iOS distribution is verified.

See [release readiness](docs/RELEASE_READINESS.md), [mobile release notes](docs/MOBILE_RELEASE.md), [AI and model licensing](docs/AI_CAPABILITIES_AND_LICENSES.md), and [production runbook](docs/PRODUCTION_RUNBOOK.md).
