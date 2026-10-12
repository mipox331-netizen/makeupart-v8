# MakeupArt V8 Production Runbook

## 1. Primary production path

The live production backend runs on Modal with Supabase PostgreSQL.

Production API:
`https://mipox331-netizen--makeupart-v8-api-fastapi-app.modal.run`

Deploys are driven by GitHub Actions through `.github/workflows/modal-deploy.yml`.

The deployment gate validates Modal/database credentials, provisions the production secret, deploys FastAPI, applies Alembic migrations, verifies the migration head and required tables, checks the MediaPipe + OpenCV image-preservation runtime, and verifies `/health/ready`.

## 2. Required production secrets

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

## 3. Monitoring

`.github/workflows/production-monitor.yml` checks `/health/live` and `/health/ready` every 15 minutes and can also be run manually. A failure produces a failed GitHub Actions run; delivery of notifications depends on GitHub notification settings. It is a basic availability check, not a full APM, uptime SLA, SMS or pager service.

## 4. Encrypted database backups

`.github/workflows/production-database-backup.yml` is configured for a daily 02:30 UTC PostgreSQL dump and a manual run. It encrypts the custom-format dump with GPG AES-256, verifies that the encrypted archive can be decrypted/listed, and uploads the encrypted archive and checksum as a GitHub Actions artifact retained for 14 days.

Before the first run, add `BACKUP_ENCRYPTION_PASSPHRASE` as a GitHub secret in the production environment. Use a unique high-entropy value of at least 24 characters and keep a recovery copy offline. The workflow accepts `SUPABASE_DB_URL`, `SUPABASE_DB_URL_SECRET` or `DATABASE_URL` already configured as a secret. If either the database URL or encryption passphrase is missing, the workflow fails rather than claiming that a backup was made.

The artifact is an encrypted database export; it is not proof of recoverability until a restore to a clean staging database has been tested. To inspect an archive after authorized download, decrypt it with the same offline passphrase and use `pg_restore --list` to check its contents.

**Important:** database exports do not include image files stored in the Modal `makeupart-v8-media` volume. A separate, private off-host media backup destination and credentials are still required. Do not treat the database workflow as a complete disaster-recovery plan.

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
