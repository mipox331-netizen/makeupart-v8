# MakeupArt V8 Production Runbook

Last checked: 23 October 2026.

## 1. Active services and deployment source

The Android client targets the Render API at:

`https://makeupart-api.onrender.com/api/v1`

Supabase is the intended PostgreSQL database. The current `main` source at audit time is commit `8b2aee9269628e58089a89cf3486bb385932179f`. Production monitor [#508](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39906865481) returned `alive` and `ready`, but that monitor did not identify the running source commit. A health check proves reachability/readiness only; it does not prove that the most recent source was deployed.

The public Android APK is [v8.0.195](https://github.com/mipox331-netizen/makeupart-v8/releases/tag/v8.0.195), built from commit `6ac6233cb1ef1e5e88c3d4009f9c26618c37a9d9`. Its workflow fell back to Flutter's debug signing key because the persistent signing keystore secret was absent. This is for manual sideloading only and can fail to update an older copy signed with a different key. The APK workflow is being hardened to wait for the live Render API to report the expected backend SHA before packaging a new build.

The old Modal deployment workflow is not the active hosting path while its free credits are exhausted. Do not regard Modal deploy success, a public APK, or a Render health check as proof that they all use the same current backend and Supabase database.

## 2. Required Render environment

Open Render Dashboard → service `makeupart-api` → Environment. Configure values without putting secrets in source control or chat:

- `DATABASE_URL`: connection string for the intended Supabase PostgreSQL database.
- `SECRET_KEY`: high-entropy secret of at least 32 characters.
- `ENVIRONMENT=production`.
- `CORS_ORIGINS`: explicit trusted origins; never use `*` in production.
- `GOOGLE_DRIVE_CLIENT_ID`, `GOOGLE_DRIVE_CLIENT_SECRET`, and `GOOGLE_DRIVE_REFRESH_TOKEN`: OAuth credentials for the private media folder.
- `REQUIRE_DURABLE_MEDIA=true` only after Google Drive is configured and the upload/restart/restore flow succeeds. The backend now fails closed in production if durable media is missing, regardless of a false legacy flag.

Use a Google OAuth client with the narrow `drive.file` scope. Keep the media folder private. The Google account and applicable Workspace administrators can access customer images, so obtain appropriate customer/salon authorization and disclose this storage arrangement in the privacy notice. Google OAuth apps left in External / Testing mode may issue refresh tokens that expire after seven days; follow Google's current OAuth guidance before relying on unattended uploads.

## 3. Verify durable customer media

The latest encrypted media backup [#48](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39893692218) failed deliberately because Google Drive returned an empty inventory (0 files / 0 bytes). Its restore drill was skipped. Do not override that failure or call it a successful backup.

Required proof:
1. Use a test portrait and/or salon logo for which you have permission.
2. Upload/process it through the live app; confirm a successful API response.
3. Confirm both input and watermarked output exist in the private Drive folder.
4. Restart the Render service and download/open both images again; verify checksums.
5. Rerun encrypted media backup and its isolated restore drill. Both must pass with a non-zero file count and matching checksums.

Existing files that were only on a lost ephemeral filesystem cannot be recreated by code. The backfill script can upload only local media that still exists and is accessible.

## 4. Database backup and restore

As of 23 October, encrypted database backup [#44](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39892512971) and isolated restore drill [#54](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39892567266) passed. The workflow writes an encrypted PostgreSQL export and a checksum to a GitHub Actions artifact with a limited retention period. Keep the encryption passphrase safe offline, separate from the artifact.

The GitHub `production` environment must contain a database URL that points to the same Supabase database used by the running Render API, along with the unique `BACKUP_ENCRYPTION_PASSPHRASE` (at least 24 characters) and any required workflow secrets. Render environment variables and GitHub Actions environment secrets are separate and must be managed separately.

A successful archive restore verifies that the selected backup can be decrypted and restored; it does not prove the backup came from the live database. Confirm source agreement and keep recurring backups running.

## 5. Android release and updates

The latest public APK is [v8.0.195](https://github.com/mipox331-netizen/makeupart-v8/releases/download/v8.0.195/MakeupArt-V8.apk). It was built with the debug signing key and from an older source commit; treat it as sideload-only.

For subsequent releases that must update an already-installed app, configure these four GitHub `production` environment secrets from the same persistent keystore:

- `ANDROID_KEYSTORE_BASE64`
- `ANDROID_STORE_PASSWORD`
- `ANDROID_KEY_PASSWORD`
- `ANDROID_KEY_ALIAS`

Do not replace or regenerate the key for routine updates. The new workflow should only publish after the live API reports the expected backend commit, `/health/live` is `alive`, `/health/ready` is `ready`, Flutter analysis/tests pass, and the APK signature is verified. Then install on a real Android device and test sign-in, processing, watermark, export and sign-out. The app can prompt users for a newer APK, but Android still requires the user to approve installation.

No successful Google Play rollout or signed iOS/App Store distribution is verified.

## 6. Admin, authentication and subscription operations

The platform admin dashboard can list platform users, block/unblock non-admin users, list salon subscriptions, activate plans for a number of days, and suspend subscriptions. Blocking an account invalidates its refresh sessions and stale access tokens. Admin access depends on the server-side `PLATFORM_ADMIN_EMAILS` allowlist; public registration is prohibited from claiming a reserved platform-admin address.

New salons start on the free plan with the configured processing quota. Generative image editing is an optional paid-provider feature and remains off until server-side credentials, schema checks, explicit external-processing consent and provider cost controls are ready. The existing MediaPipe/OpenCV Classic pipeline is the intended no-provider mode for a $0 budget.

## 7. Privacy, licensing and repository controls

- Keep customer media private and serve it through authenticated salon-scoped endpoints.
- Do not disable consent resets or salon isolation to work around processing failures.
- Review retention and deletion behavior before production changes.
- The GitHub `main` branch was observed without branch protection. Configure required CI/security/license checks and prevent unreviewed direct pushes.
- The repository is public while its `LICENSE` declares original project code proprietary. Decide whether to make source private, considering that private-repository release assets and user download/update links require a compatible distribution plan.
- Review `docs/THIRD_PARTY_LICENSE_AUDIT.md` and all model/asset terms before making a commercial-clearance claim.

## 8. Monitoring and incident response

The scheduled monitor checks Render liveness/readiness every 15 minutes and retries transient cold-start/gateway responses. GitHub Actions reporting does not constitute independent SMS/pager alerting. During an incident, correlate the API response's `X-Request-ID` with server logs; do not log access/refresh tokens, customer images, or provider secrets.
