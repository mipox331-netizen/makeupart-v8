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

The target production configuration uses private `supabase_storage` for server-side salon photos, with the Flutter app also retaining its phone Gallery copies. Encrypted PostgreSQL and media archives are designed to be stored separately in Cloudflare R2 and verified by restore drills. The deploy workflow switches off `local_only` only after the Supabase bucket and credentials pass preflight. See [Cloudflare R2 backup setup](docs/CLOUDFLARE_R2_BACKUP.md).

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

Every successfully processed result is copied to the phone's shared Android MediaStore folder `Pictures/MakeupArtV8`, using a stable salon-scoped filename so retries update the same copy instead of creating duplicates. The ten latest images also remain in private in-app history. When the salon workspace opens or returns to the foreground, MakeupArt quietly retries pending Gallery copies. For server-side recovery, the production API stores media objects in a private Supabase Storage bucket; a separate encrypted inventory archive is uploaded to Cloudflare R2. The two cloud copies serve different purposes: Supabase is the app's live object store and R2 is the off-site encrypted backup.

## Photo durability and disaster recovery

The planned production configuration is `MEDIA_STORAGE_BACKEND=supabase_storage` with a private bucket named `makeupart-media`. The API fails closed when Supabase Storage credentials are absent or when the bucket is public. The backup workflow downloads and checksums that private bucket, creates an AES-256 GPG archive, and uploads it to the private Cloudflare R2 bucket. Database backups follow the same encrypted R2 path. Restore drills download from R2, verify SHA-256, decrypt, and restore into disposable isolated environments; failed uploads cannot be counted as successful restores.

Phone Gallery copies remain useful as another copy but do not replace cloud recovery. Older photos that were processed while production was in `local_only` mode were not saved on the server and are not retroactively placed in Supabase Storage by this change; existing copies remain on the customer's phone unless explicitly uploaded again. This migration protects media processed after private Supabase Storage is confirmed live.

## Licensing and AI capabilities

Original MakeupArt V8 project code is proprietary; see [LICENSE](LICENSE). Third-party components retain their own licenses. Review the [third-party license audit record](docs/THIRD_PARTY_LICENSE_AUDIT.md) before commercial distribution.

Classic enhancement uses MediaPipe face landmarks and OpenCV effects, including face-aware lipstick, blush, eyeshadow and eyeliner/wing presets. This is a lightweight local effect—not a FaceApp-equivalent generative reference-image transfer model. The optional OpenAI image-edit path is disabled without server-side credentials and may incur provider costs; for a $0 operating budget, keep classic mode as the default.

The app checks GitHub Releases and prompts users to download newer APKs. Android still requires the user to approve installation. No successful Google Play publication or signed iOS distribution is verified.

See [release readiness](docs/RELEASE_READINESS.md), [mobile release notes](docs/MOBILE_RELEASE.md), [AI and model licensing](docs/AI_CAPABILITIES_AND_LICENSES.md), and [production runbook](docs/PRODUCTION_RUNBOOK.md).
