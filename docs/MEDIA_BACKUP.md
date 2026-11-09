# MakeupArt V8 — Phone copies and encrypted Google Drive backups

## Phone photo copies

The Android client copies every processed output to the phone's shared MediaStore folder `Pictures/MakeupArtV8`. The latest ten images remain in salon-scoped private app history; older private images are removed only after Gallery confirms publication. The manual **Backup Now** action retries locally retained images.

These are device copies. They remain on the phone after app removal, but cannot recover a lost or factory-reset device. MakeupArt does not upload this MediaStore copy to Google Drive. The phone's Gallery/Photos app may independently sync its own folders according to the device owner's settings.

## Actual production media architecture

The production Modal deployment mounts the persistent Modal Volume `makeupart-v8-media` at `/app/media`. The Modal entrypoint explicitly selects `MEDIA_STORAGE_BACKEND=modal_volume`; customer source photos, processed images and salon logos are written there and committed to that Volume.

**Google Drive is the off-site encrypted backup destination, not the live media filesystem used by the current Modal deployment.** The production media backup must therefore read from the Modal Volume. Reading the Google Drive app-media folder alone is not a valid backup of current production media.

PostgreSQL remains the live relational database for accounts, salons, subscriptions, jobs and payments. Its encrypted database dump is uploaded to the same private Google Drive backup folder by the separate database-backup workflow.

## Daily media backup flow

The GitHub Actions workflow `MakeupArt V8 Encrypted Google Drive Media Backup` runs daily at 02:45 UTC and can be started manually. It:

1. Authenticates to the Modal `main` environment and downloads the complete `makeupart-v8-media` Volume.
2. Rejects unsafe filesystem entries, oversized or empty objects, and files that change while checksums are being calculated.
3. Writes a manifest with every relative media path, byte size and SHA-256 checksum.
4. If the Volume is empty, checks the live PostgreSQL media-reference columns before accepting that empty state.
5. Creates a GPG symmetric AES-256 encrypted archive, decrypts it in an isolated temporary directory and verifies the restored file set and SHA-256 checksums.
6. Uploads the encrypted archive and SHA-256 sidecar to the private Google Drive folder `MakeUpArt V8 Encrypted Backups`. The uploader checks Google Drive's returned size and MD5 metadata.
7. Keeps a temporary encrypted GitHub Actions artifact for 14 days. The paired restore-drill workflow decrypts that artifact and verifies its contents without modifying production storage.

The archive is created from the actual mounted Volume. It does not depend on the legacy Google Drive app-media folder or Supabase Storage.

The separate database workflow runs daily at 02:30 UTC. It creates a PostgreSQL custom-format dump, encrypts it, verifies that it can be decrypted and parsed by `pg_restore`, then uploads it to the same Drive backup folder.

## Required GitHub production environment secrets

The media backup workflow needs:

- `MODAL_TOKEN_ID` or `TOKENID`
- `MODAL_TOKEN_SECRET`, `TOKEN_SECRET` or `TOKENI_SECRET`
- `GOOGLE_DRIVE_CLIENT_ID` or `GDRIVE_CLIENT_ID`
- `GOOGLE_DRIVE_CLIENT_SECRET` or `GDRIVE_CLIENT_SECRET`
- `GOOGLE_DRIVE_REFRESH_TOKEN` or `GDRIVE_REFRESH_TOKEN`
- `BACKUP_ENCRYPTION_PASSPHRASE` — at least 24 characters; keep a separate offline recovery copy
- `SUPABASE_DB_URL`, `SUPABASE_DB_URL_SECRET` or `DATABASE_URL` — only for the live PostgreSQL empty-media safety check

The Modal token must have access to the `main` environment and the named production Volume. Do not commit these values or print them in workflow logs. Google Drive OAuth must belong to the account that owns the private MakeUpArt backup folder.

## Google OAuth refresh-token recovery

The backup workflows use a private Google Drive account through OAuth. If a workflow reports `invalid_grant`, Google has rejected the stored refresh token because it expired or was revoked. For an External OAuth app still in **Testing**, refresh tokens for scopes beyond basic profile/email expire after seven days.

In Google Cloud Console:

1. Open **Google Auth Platform → Audience**.
2. Change **Publishing status** from **Testing** to **In production**.
3. Re-authorize the same Google account that owns the MakeUpArt Drive backups, requesting offline access and explicit consent.
4. Replace the production GitHub environment secret `GOOGLE_DRIVE_REFRESH_TOKEN` (or its existing alias `GDRIVE_REFRESH_TOKEN`) with the newly issued refresh token.
5. Run both media and database backup workflows manually. Confirm each upload step succeeds.

Publishing the OAuth consent screen does not rent storage or create a paid database. Google may still require verification before an app can request sensitive Drive scopes from broad public users; this backup design only needs the owner's account to authorize the app.

## What counts as a real backup

A configured workflow is not proof of a working backup. Production proof requires:

1. A successful Modal Volume download that reports the actual file count and total bytes.
2. Successful encryption, isolated decryption and SHA-256 verification.
3. A successful Google Drive upload with matching size and checksum metadata.
4. A successful paired restore drill.

An empty media inventory is accepted only after the live database check confirms that no photo/logo references point to missing files. A green restore drill based only on a GitHub artifact does not by itself prove that the Google Drive upload succeeded; the Drive upload step must also be green.

Keep the encryption passphrase safely offline. Google Drive quota is finite and shared with the owner's other Google services.
