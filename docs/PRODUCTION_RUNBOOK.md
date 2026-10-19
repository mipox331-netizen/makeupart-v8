# MakeupArt V8 Production Runbook

## 1. Current Android endpoint and deployment paths

The published Android APK v8.0.164 is configured to call the Render API:

`https://makeupart-api.onrender.com/api/v1`

The connected deployment record identifies `makeupart-api` on Render's free plan. Cold starts and transient gateway timeouts have occurred, so a green health check is not a guarantee that every user flow works continuously.

**Important storage and database boundary:** the APK's API endpoint being Render does not prove that the running service uses the same database URL selected by the backup workflow, and it does not make local `MEDIA_ROOT` files durable. Verify the runtime database target before relying on a database restore, and do not rely on local media files for customer-photo retention unless persistent/object storage is attached and its restore is tested.

The repository also retains a separate Modal deployment path. That path is **not** the endpoint configured in the published APK. Use it only after the Modal deployment, database connection, and media volume are deliberately restored and verified. Its API URL is:

`https://mipox331-netizen--makeupart-v8-api-fastapi-app.modal.run`

Deploys for the Modal alternative are driven by GitHub Actions through `.github/workflows/modal-deploy.yml`. The deployment gate validates Modal/database credentials, provisions the production secret, deploys FastAPI, applies Alembic migrations, verifies the migration head and required tables, checks the MediaPipe + OpenCV image-preservation runtime, and verifies `/health/ready`.

## 2. Required secrets for the Modal deployment path

Store these in GitHub repository secrets or the `production` environment as appropriate:

- `MODAL_TOKEN_ID`
- `MODAL_TOKEN_SECRET`
- `SUPABASE_DB_URL` or `SUPABASE_DB_URL_SECRET`
- `SUPABASE_SECRET_KEY` / supported Supabase secret
- `SUPABASE_ANON_KEY`
- `SUPABASE_SECRET` / service-role key
- `PLATFORM_ADMIN_EMAILS`

`PLATFORM_ADMIN_EMAILS` is a comma-separated allow-list of email addresses allowed into project administration.

Never commit secret values or paste them into chat.

### Google Drive private media storage

The API has an optional private Google Drive adapter for salon logos and customer before/after photos. It uses the Google account owner's OAuth refresh token (not a service account), the `drive.file` scope, and a private folder created by the app. It does not create public sharing links.

Enable the Google Drive API in Google Cloud, create an OAuth client, and grant the app the `https://www.googleapis.com/auth/drive.file` scope with offline access. Use the [Google OAuth 2.0 Playground](https://developers.google.com/oauthplayground/) with your own OAuth client credentials to authorize the account and obtain a refresh token. Do not paste credentials into chat or commit them to Git.

Set these environment variables on the live Render `makeupart-api` service:

- `GOOGLE_DRIVE_CLIENT_ID`
- `GOOGLE_DRIVE_CLIENT_SECRET`
- `GOOGLE_DRIVE_REFRESH_TOKEN`
- `REQUIRE_DURABLE_MEDIA=true` (only after OAuth is configured and an upload/restore has passed)

The example environment leaves `REQUIRE_DURABLE_MEDIA=false` so setup does not unexpectedly disable photo processing. Once the OAuth values are configured, test a new image upload and restore after a service restart, then enable required mode. If Drive authentication or persistence fails, processing returns a storage error rather than treating a local-only save as durable. Existing photos that are available only on an earlier Render filesystem are not automatically backfilled by this adapter.

Keep the Drive folder private. OAuth-created files belong to the authenticated user and consume that account's Drive storage quota. Google OAuth apps left in External / Testing mode may issue refresh tokens that expire after seven days; configure the consent screen for the intended long-term deployment before relying on unattended uploads. See [Google's OAuth refresh-token guidance](https://developers.google.com/identity/protocols/oauth2).

## 3. Monitoring

`.github/workflows/production-monitor.yml` checks `/health/live` and `/health/ready` every 15 minutes and can also be run manually. A failure produces a failed GitHub Actions run; delivery of notifications depends on GitHub notification settings. It is a basic availability check, not a full APM, uptime SLA, SMS or pager service.

## 4. Encrypted database backups

`.github/workflows/production-database-backup.yml` is configured for a daily 02:30 UTC PostgreSQL dump and a manual run. It encrypts the custom-format dump with GPG AES-256, verifies that the encrypted archive can be decrypted/listed, and uploads the encrypted archive and checksum as a GitHub Actions artifact retained for 14 days.

Before the first run, add `BACKUP_ENCRYPTION_PASSPHRASE` as a GitHub secret in the production environment. Use a unique high-entropy value of at least 24 characters and keep a recovery copy offline. The workflow accepts `SUPABASE_DB_URL`, `SUPABASE_DB_URL_SECRET` or `DATABASE_URL` already configured as a secret. If either the database URL or encryption passphrase is missing, the workflow fails rather than claiming that a backup was made.

The artifact is an encrypted database export; it is not proof of recoverability until a restore to a clean staging database has been tested. To inspect an archive after authorized download, decrypt it with the same offline passphrase and use `pg_restore --list` to check its contents.

**Important:** database exports do not include image files. The Modal `makeupart-v8-media` volume and the new Google Drive adapter are separate. The Google Drive adapter must be configured and cold-start restore tested before treating the live Render photos as durable; database dump success alone is not a complete disaster-recovery plan.

Supabase Free projects do not receive the Pro/Team/Enterprise daily-backup feature and should maintain their own exports. See [Supabase database backups](https://supabase.com/docs/guides/platform/backups).

## 5. User access and subscriptions

Every new salon starts on the permanent `free` plan with a monthly AI-processing quota of 25 jobs.

The project admin can view registered users across salons, see active vs blocked users, block/unblock users, suspend/reactivate salon subscriptions and activate plans. Blocking a user sets `is_active=false` and is enforced at the authenticated API boundary. A suspended paid subscription is prevented from AI processing until reactivated; account data is retained.

## 6. Mobile production builds

The Android APK is available from the public [GitHub Releases page](https://github.com/mipox331-netizen/makeupart-v8/releases). The in-app update checker prompts users to download a new APK, but Android requires them to confirm installation.

The Google Play workflow requires `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` and Android signing secrets. Start on internal testing and verify publication in Play Console; the repository currently has no verified successful Play Store release.

The iOS compile workflow creates an unsigned build artifact only. App Store distribution still requires Apple account enrollment and signing/App Store Connect configuration.

## 7. Self-hosted alternative

The repository contains `backend/docker-compose.production.yml` with PostgreSQL, private media and Caddy HTTPS termination for a self-hosted deployment. Use that path only when deliberately hosting outside Modal/Supabase. The shell helper at `backend/ops/backup_postgres.sh` targets that self-hosted Compose database; it does not back up the production Supabase database or Modal media volume.

## 8. Security and commercial-readiness checklist

- HTTPS is mandatory in production.
- Keep `CORS_ORIGINS` explicit and secrets outside Git.
- Keep customer media private and serve it only through authenticated API routes.
- Keep consent, retention and deletion controls in place.
- The InsightFace `buffalo_l` pretrained model/runtime has been removed, and the MediaPipe/OpenCV replacement was verified in production deployment run [38257623154](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38257623154). The OpenCV score measures image-structure preservation, not biometric identity recognition.
- The current OpenCV filter is not generative makeup. Do not advertise the generative feature as available until it is implemented and validated.
- The root proprietary source notice and automated Python/Flutter dependency license inventory are now in the repository. Review the reports and remaining native, OS, container, and asset/model license terms before claiming full commercial clearance. See [Third-party license audit](THIRD_PARTY_LICENSE_AUDIT.md).
