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

The API runs on port 8000. Health endpoints are:
- `/health/live` — process liveness.
- `/health/ready` — database/API readiness for the deployed hosting provider. A temporary third-party storage outage does not restart the API process.
- `/health/media-ready` — private customer-photo storage readiness for the selected durable backend.

Media uploads fail closed when durable storage is unavailable. Production APK publication requires `/health/media-ready` to return a supported durable backend (`google_drive`, `modal_volume` or `supabase_storage`); API/login readiness alone is not a customer-photo release gate.

## Flutter development
From `makeup_art_v8/`:

```bash
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1
```

Use the computer's LAN address instead of `10.0.2.2` on a physical device.

## Current production and Android release

Status checked: 2 November 2026.

The API endpoint is deliberately not embedded in production workflows or app defaults. Configure the repository-level GitHub Actions variable `API_BASE_URL` as the deployed HTTPS API URL ending in `/api/v1` (for example, `https://your-api-host.example/api/v1`). CI, Android release, iOS compile and Google Play workflows consume this same variable. The Android debug build falls back to `http://10.0.2.2:8000/api/v1`, which is for a local Android emulator only; a physical-device build must receive the correct reachable API URL.

The latest public release is [v8.0.201](https://github.com/mipox331-netizen/makeupart-v8/releases/tag/v8.0.201), published on 23 October 2026. Its APK is [MakeupArt-V8.apk](https://github.com/mipox331-netizen/makeupart-v8/releases/download/v8.0.201/MakeupArt-V8.apk). It predates the current main source and was signed with Android Debug, so it is a manual testing package, not a safe update-compatible production release.

The latest main commit observed during this review was `620593f6042da17777584cb97bc1f917202da08d`. On 2 November, production monitor run [#41411853250](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/41411853250) timed out against the old hardcoded Render host. This does not establish that any replacement host is live. The production API address and current running deployment must be verified before a release.

Current-source Android release still requires the four persistent signing secrets in the `production` GitHub environment: `ANDROID_KEYSTORE_BASE64`, `ANDROID_STORE_PASSWORD`, `ANDROID_KEY_PASSWORD` and `ANDROID_KEY_ALIAS`. They must all belong to the same persistent keystore used by the already-installed app. Never publish an update using an ephemeral debug key.

## Editing capabilities and honest feature scope

Classic mode is local MediaPipe/OpenCV processing and does not require a paid image-generation key. It includes face-mesh-guided lipstick, blush, eyeshadow and eyeliner; face-region skin polish; five photo finishes; and server-side brightness, contrast, saturation, warmth and sharpness controls. Manual adjustments are applied before the salon watermark and are included in the saved PNG. Salon look presets retain these values, while presets created by older app versions load with neutral defaults.

The editor also supports camera/gallery import, interactive before/after comparison, salon watermarking, phone-gallery export, ten recent device-local results, salon-scoped client profiles and stored consent.

MakeupArt is **not yet a complete FaceApp replacement**. Hairstyle generation requires an external provider and separate consent. Hair recoloring, age/gender transforms, smile editing, face reshaping, beards, glasses, live camera overlays, filter multi-select, favorites and video generation are not implemented or not release-verified. See the evidence-based [FaceApp feature parity audit](docs/FEATURE_PARITY.md) before presenting any roadmap item as available.

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

## On-device photo history

The Android app keeps the ten most recent processed results in salon-scoped private app storage. When an older result is archived, it is published through Android MediaStore to the public `Pictures/MakeupArtV8` gallery with a salon-scoped filename. The private source is deleted only after Gallery confirms the save; permission or storage failures leave the original in app storage. This device archive is separate from the encrypted Google Drive production-media backup and does not replace the server-side recovery checks below.

## Photo durability and disaster recovery

The repository contains private Google Drive media storage and encrypted database/media backup workflows. The latest observed database backup [#41422955166](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/41422955166) successfully created and validated its encrypted PostgreSQL dump, but the Google Drive upload failed because OAuth returned `invalid_grant`. The latest media backup [#41424743670](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/41424743670) failed at token refresh before it could inventory or download media. No successful customer-media backup or restore is proven by those runs.

To restore Google Drive backup access, publish the Google OAuth consent app as **In production**, authorize the Drive client again with offline access, and replace the GitHub `production` environment secret `GOOGLE_DRIVE_REFRESH_TOKEN` with the newly issued refresh token. Keep all OAuth values private. Re-run database and media backups only after the credential has been refreshed; a successful database dump alone is not a backup until the encrypted archive is stored in the configured off-site destination.

**Storage/backup alignment is still a release blocker.** The Modal API entrypoint currently forces `MEDIA_STORAGE_BACKEND=modal_volume` and mounts the `makeupart-v8-media` Volume, while the scheduled GitHub media-backup workflow inventories Google Drive. A Google Drive backup does not back up a Modal Volume. The deployed service and backup workflow must target the same durable store before customer-photo recovery can be claimed. Verify a real salon image/logo upload, persistence across restart, checksum-matched retrieval, non-empty encrypted backup and isolated restore.

## Licensing and AI capabilities

Original MakeupArt V8 project code is proprietary; see [LICENSE](LICENSE). Third-party components retain their own licenses. Review the [third-party license audit record](docs/THIRD_PARTY_LICENSE_AUDIT.md) before commercial distribution.

Classic enhancement uses MediaPipe face landmarks and OpenCV effects, including face-aware lipstick, blush, eyeshadow and eyeliner/wing presets. This is a lightweight local effect—not a FaceApp-equivalent generative reference-image transfer model. The optional OpenAI image-edit path is disabled without server-side credentials and may incur provider costs; for a $0 operating budget, keep classic mode as the default.

The app checks GitHub Releases and prompts users to download newer APKs. Android still requires the user to approve installation. No successful Google Play publication or signed iOS distribution is verified.

See [release readiness](docs/RELEASE_READINESS.md), [mobile release notes](docs/MOBILE_RELEASE.md), [AI and model licensing](docs/AI_CAPABILITIES_AND_LICENSES.md), and [production runbook](docs/PRODUCTION_RUNBOOK.md).
