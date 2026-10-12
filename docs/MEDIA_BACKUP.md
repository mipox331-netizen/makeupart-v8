# Encrypted production media backup and restore drill

## What runs

The **MakeupArt V8 Encrypted Production Media Backup** workflow backs up the named Modal volume `makeupart-v8-media` separately from PostgreSQL. It runs daily at 02:45 UTC, after a successful Modal production deployment, and on manual dispatch.

The workflow downloads the volume to a short-lived GitHub Actions runner, refuses symbolic links and fails safely if the source volume exceeds 3 GiB, then builds a file manifest containing relative paths, sizes and SHA-256 checksums. It packages the media directory plus the manifest, encrypts the archive with GPG symmetric AES-256 using `BACKUP_ENCRYPTION_PASSPHRASE`, decrypts and verifies a copy, and uploads only the encrypted archive and its checksum as an Actions artifact. Artifact retention is 14 days.

An automatically triggered **MakeupArt V8 Encrypted Media Restore Drill** downloads the matching artifact, verifies its SHA-256 checksum, decrypts it and restores it into a temporary directory. It re-hashes every restored file and compares the file list, sizes and checksums with the encrypted manifest. The drill never writes back to the production Modal volume.

Unencrypted staging content and temporary passphrase/decryption files are removed from the ephemeral runner in cleanup steps. The GPG passphrase must remain in GitHub Secrets / the `production` environment and should also have an offline recovery copy. Never place it in source code, workflow inputs or logs.

## Current verified evidence (12 October 2026)

- [Encrypted media backup run 38272705211](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38272705211): succeeded.
- [Isolated media restore drill 38272747093](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38272747093): succeeded.
- The source volume contained **0 files and 0 bytes**. These runs verify the encryption/archive/checksum/restore mechanics for an empty volume. They do **not** prove recovery of actual customer photos.

When real production photos exist, the next successful scheduled backup will include them and the paired restore drill will verify every archived file. If the media volume is larger than 3 GiB, the workflow fails rather than uploading a partial archive; use a larger/resumable backup destination before increasing that operational limit.

## Retention and limitations

Encrypted artifacts expire after 14 days. This provides a short-term off-volume recovery window, not indefinite archival. Keep a separate offline passphrase recovery copy and monitor the scheduled backup and restore runs. This workflow covers media files only; PostgreSQL records use the separate encrypted database backup and restore workflows.

A successful empty-volume drill is not evidence that customer-photo recovery has been tested. The first populated-media restore should be reviewed from the workflow output before treating the media disaster-recovery gate as complete.
