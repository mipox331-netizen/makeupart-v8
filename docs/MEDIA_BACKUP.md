# MakeupArt V8 — Google Drive media storage and encrypted backups

## Chosen storage layout

Google Drive is the primary private storage for salon photos, before/after images and salon logos. The backend is configured with `MEDIA_STORAGE_BACKEND=google_drive` and `REQUIRE_DURABLE_MEDIA=true`; it refuses to silently save customer media only on Render's temporary disk when Drive credentials are missing.

PostgreSQL remains the live relational database for accounts, salons, subscriptions, jobs and payments. Google Drive is file storage, not a SQL database, so it cannot replace the live PostgreSQL connection. The current deployment workflow can keep the existing PostgreSQL URL while setting media storage to Google Drive; it does not configure Supabase Storage or send a Supabase service-role key to the app.

## What is stored in Drive

- The app stores private media beneath the app-owned folder marked `makeupart_root=v1`.
- Encrypted media snapshots are saved in `MakeUpArt V8 Encrypted Backups`.
- Encrypted PostgreSQL custom-format dumps are saved in the same backup folder.
- Backup objects are encrypted with GPG symmetric AES-256 before upload. Only encrypted archives and SHA-256 sidecars are sent to Drive.
- GitHub Actions also keeps a temporary copy for the automatic isolated restore drill (14 days); the Drive copy is the longer-lived backup.

The Google Drive free account quota is finite and shared with other Google services. This design avoids a hosted media-storage trial expiring, but it does not make storage unlimited. Keep an eye on Drive quota, and keep the encryption passphrase safely offline.

## Required GitHub production environment secrets

The deployment and backup workflows accept either the canonical name or the legacy alias:

- `GOOGLE_DRIVE_CLIENT_ID` or `GDRIVE_CLIENT_ID`
- `GOOGLE_DRIVE_CLIENT_SECRET` or `GDRIVE_CLIENT_SECRET`
- `GOOGLE_DRIVE_REFRESH_TOKEN` or `GDRIVE_REFRESH_TOKEN`
- `BACKUP_ENCRYPTION_PASSPHRASE` — at least 24 characters; keep a separate offline recovery copy.
- `SUPABASE_DB_URL`, `SUPABASE_DB_URL_SECRET` or `DATABASE_URL` — only for the live PostgreSQL database and the empty-media safety check.
- `RENDER_API_KEY` or `RENDER_API_TOKEN` — needed for the GitHub deployment workflow to update the Render service and trigger a deployment.

Do not commit these values or print them in workflow logs. The OAuth refresh token must belong to the Google account that owns the MakeUpArt Drive folders and must have permission to manage the app-created Drive files.

## Backup schedule and verification

The media workflow runs daily at 02:45 UTC and can also be started manually. It inventories the private Drive media root, paginates the full file list, rejects duplicate/unsafe path indexes, downloads every file, and checks the stored size and MD5 before creating a SHA-256 manifest. An empty Drive inventory is accepted only after the database check confirms there are no photo/logo references pointing to missing media.

The database workflow runs daily at 02:30 UTC and after a successful database migration. It creates a PostgreSQL custom-format dump, encrypts it, verifies that it can be decrypted and parsed by `pg_restore`, then uploads it to Drive.

The media and database restore-drill workflows independently decrypt GitHub's temporary artifact and verify that the media archive can be unpacked or the SQL dump can be restored into an isolated disposable PostgreSQL instance. These drills never write to the production database or production Drive.

## Production proof still required

A configured workflow is not proof that Google OAuth currently works in production. The first successful run must confirm all three:
1. Media objects are actually present in the private Drive root and have non-zero bytes.
2. Encrypted media and database archives are uploaded to the private Drive backup folder and their checksum verification passes.
3. The paired isolated restore drills pass.

A green empty-media check only proves that no existing database row points to missing media; it does not prove the app has completed a real salon-photo upload. Use an authorized test portrait and logo before using real customer data.
