# MakeupArt V8 — Current Engineering Status

Status checked: 2 November 2026. This report is based on the public repository source and GitHub Actions evidence visible during this review. It does not imply access to production secrets or an Android device.

## Source reviewed

- Main branch at review start: [`620593f6042da17777584cb97bc1f917202da08d`](https://github.com/mipox331-netizen/makeupart-v8/commit/620593f6042da17777584cb97bc1f917202da08d).
- A focused fix branch is being prepared: `fix/production-api-config-and-storage-gates`.
- Existing open feature PR [#18](https://github.com/mipox331-netizen/makeupart-v8/pull/18) is not safe to merge as-is. Its `0010_payment_ledger.py` migration competes with a different `0010` migration on main; rebase and reconcile the Alembic graph before considering it.

## Production failures observed on 2 November

- Production monitor [run #41411853250](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/41411853250) failed because requests to the hardcoded Render URL timed out with HTTP 000 and no response.
- Encrypted database backup [run #41422955166](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/41422955166) created the PostgreSQL dump, encrypted it, decrypted it and validated the archive. The subsequent Google Drive upload failed because the refresh token returned `invalid_grant`; the off-site backup step did not complete.
- Encrypted media backup [run #41424743670](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/41424743670) failed at Google Drive OAuth refresh before media inventory/download. Encryption and restore steps were skipped. Customer photo/logo recovery is not verified.

## Fixes prepared on the fix branch

- Removed the retired Render URL from the Flutter API client and made the local Android-emulator default explicit.
- Made CI, production monitor, Android release, iOS compile and Google Play workflows consume the same repository variable, `API_BASE_URL`. Production workflows now fail clearly unless it is an HTTPS API URL ending in `/api/v1`.
- Made `/health/ready` report provider-neutral `APP_GIT_COMMIT`, retaining `RENDER_GIT_COMMIT` only as a backwards-compatible fallback. The Modal deploy workflow now injects the exact workflow commit into its production secret.
- Updated backend regression coverage to ensure the provider-neutral commit value takes precedence.
- CI and device/build verification are still pending for the proposed branch; no successful test/build is claimed here.

## External configuration and release blockers

1. Set the repository-level GitHub Actions variable `API_BASE_URL` to the actual deployed HTTPS API URL ending in `/api/v1`. Do not set it to a guessed host. The production monitor and release gate must verify `/health/live`, `/health/ready`, and `/health/media-ready` against that same host.
2. Reauthorize Google Drive OAuth and replace the production secret `GOOGLE_DRIVE_REFRESH_TOKEN`. The current token returns `invalid_grant`; code changes cannot mint a replacement refresh token.
3. Align the active media backend with the backup source. `modal_app.py` currently forces `modal_volume`; the scheduled GitHub media workflow backs up Google Drive. A Drive archive does not contain Modal Volume files.
4. Confirm the four Android signing secrets use the persistent keystore of the installed app. Their current values were not inspected in this review.
5. Complete a physical Android smoke test: registration/login, consent, camera/gallery, classic processing, salon logo/watermark, before/after, export, logout/re-login and update compatibility.
6. Resolve PR #18's competing migration head and review the schema/feature changes before merge.
7. Keep the documented Python dependency audit exception visible; do not describe the project as having zero vulnerabilities.

## Release decision

**Not production-ready for public customer launch based on current evidence.** Main source can be tested in CI, but the API host is not currently verified, Google Drive OAuth backups are failing, media-store/backup alignment is unresolved, and device/release-signing verification remains open. Do not mark these gates green without fresh evidence.
