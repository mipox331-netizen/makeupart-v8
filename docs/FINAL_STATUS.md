# MakeupArt V8 — Current Engineering Status

Status checked: 2 November 2026. This report distinguishes repository-source changes, automated checks, live-service evidence, and customer-device verification. No production secret values or customer media were accessed.

## Current work

- Review baseline on main: [`620593f6042da17777584cb97bc1f917202da08d`](https://github.com/mipox331-netizen/makeupart-v8/commit/620593f6042da17777584cb97bc1f917202da08d).
- Working branch: `fix/production-api-config-and-storage-gates`.
- Open review: [PR #55 — Fix production API configuration and expose deployment revision](https://github.com/mipox331-netizen/makeupart-v8/pull/55).
- Latest PR source at this status update: [`1355b046c39bcbd57648d442bc8d3cbb563a6f1d`](https://github.com/mipox331-netizen/makeupart-v8/commit/1355b046c39bcbd57648d442bc8d3cbb563a6f1d).
- The branch has **not** been merged into main.

## Editor capability work

- Added server-side brightness, contrast, saturation, warmth and sharpness controls to the image-processing request/response.
- Manual adjustments are applied after the selected photo finish and before the salon watermark, so the exported watermarked PNG contains those changes. Defaults preserve the existing image; values are bounded in both the API schema and processing service.
- Added the five controls and reset action to the Impression editor panel.
- Extended salon look presets to save and restore all five adjustment values. Existing saved presets without the new fields remain readable and default to neutral adjustments.
- Added regression coverage for pixel changes, unchanged default values, safe adjustment bounds, upload API propagation, preset compatibility, and the editor slider/reset flow.
- Added [FEATURE_PARITY.md](FEATURE_PARITY.md), comparing source-verified MakeupArt capabilities with FaceApp and YouCam. It explicitly lists unavailable filters instead of implying that a roadmap tile works.
- This does not make MakeupArt feature-identical to FaceApp. Hair color, age/gender transformations, smile editing, face reshaping, beard/glasses tools, live camera overlays, multi-select and favorites are still absent or not release-verified. Hairstyle generation remains dependent on a configured external provider.

## API and release configuration work

- Removed hardcoded Render API URLs from the Flutter client, CI, production monitor, Android release, iOS compile and Google Play workflows.
- Added one repository variable, `API_BASE_URL`, as the source of production API configuration. Production workflows reject missing or malformed values rather than publishing an APK pointing at an assumed host.
- Android emulator debug builds retain an explicit local emulator default (`http://10.0.2.2:8000/api/v1`); this is not a physical-device or production endpoint.
- `/health/ready` now prefers provider-neutral `APP_GIT_COMMIT`, with the old Render commit value retained only as a fallback. The Modal deploy workflow injects its source commit into the production secret.
- Backend regression coverage verifies the provider-neutral deployment commit.

## Automated verification

- The initial API-configuration revision of this PR passed backend build, Alembic migrations/check, backend tests, Flutter analysis/tests, Android debug APK build and artifact upload, unsigned iOS compile, Python security audit, and third-party license inventory.
- These checks are **not sufficient evidence for the later editor-control changes**. The latest source commit `1355b046...` has a fresh PR CI, iOS compile, Python audit and license inventory run queued/in progress as of this status update. Wait for those exact-source runs before accepting the new controls.
- No production-signed APK has been built from the latest source. The CI artifact is a debug APK.
- No physical Android device smoke test has been completed during this review.

## Production failures observed on 2 November

- Production monitor [run #41411853250](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/41411853250) timed out against the old hardcoded Render URL (HTTP 000).
- Encrypted database backup [run #41422955166](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/41422955166) created and validated the encrypted PostgreSQL archive, but the Google Drive upload failed because OAuth returned `invalid_grant`.
- Encrypted media backup [run #41424743670](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/41424743670) failed at Google Drive OAuth refresh before media inventory/download.

## External configuration and release blockers

1. Set the repository Actions variable `API_BASE_URL` to the actual deployed HTTPS API URL ending in `/api/v1`. Do not guess the host. Production monitor and release gate must verify `/health/live`, `/health/ready` and `/health/media-ready` on the same host.
2. Reauthorize Google Drive OAuth and replace `GOOGLE_DRIVE_REFRESH_TOKEN` in the production GitHub environment. The existing token returns `invalid_grant`; repository code cannot create a new user refresh token.
3. Align the active media backend with the backup source. `modal_app.py` forces `modal_volume`, while the GitHub media-backup workflow inventories Google Drive. A Google Drive archive does not back up the Modal Volume.
4. Confirm the four Android signing secrets belong to the persistent keystore used by the installed app: `ANDROID_KEYSTORE_BASE64`, `ANDROID_STORE_PASSWORD`, `ANDROID_KEY_PASSWORD` and `ANDROID_KEY_ALIAS`. Their values were not inspected.
5. Complete physical Android smoke tests: registration/login, client consent reset, camera/gallery, makeup processing, five manual adjustments, watermark/logo, before/after, export, recent history, preset save/load, logout/re-login and update compatibility.
6. Resolve the competing Alembic `0010` migration in existing feature PR #18 before merging its payment/favorites/social changes.
7. Keep the known Python dependency-audit exception visible; do not describe the project as having zero vulnerabilities.

## Release decision

**Not production-ready for public customer launch based on current evidence.** The source changes are in PR #55. Initial API-configuration checks passed, but the latest editor-control source still needs exact-commit CI verification. API host, media-store/backup alignment, refreshed Drive OAuth, persistent Android release signing and physical-device testing remain open. Do not mark these gates green without new evidence.
