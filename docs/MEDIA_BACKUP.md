# Encrypted production Google Drive media backup and restore drill

Status checked: 28 October 2026.

## What the active workflow backs up

The active workflow [`.github/workflows/production-media-backup.yml`](https://github.com/mipox331-netizen/makeupart-v8/blob/main/.github/workflows/production-media-backup.yml) backs up objects in the app's **private Google Drive media root**. It does not snapshot the old Modal volume and does not automatically back up files that exist only on Render's local/ephemeral filesystem.

It runs daily at 02:45 UTC, on manual dispatch, and when this workflow file changes on `main`. The encrypted archive is uploaded as a GitHub Actions artifact with a 14-day retention period.

## Required GitHub production secrets

The workflow reads these from the GitHub `production` environment. Values must never be printed in logs or committed.

- `GOOGLE_DRIVE_CLIENT_ID` or the established alias `GDRIVE_CLIENT_ID`.
- `GOOGLE_DRIVE_CLIENT_SECRET` or `GDRIVE_CLIENT_SECRET`.
- `GOOGLE_DRIVE_REFRESH_TOKEN` or `GDRIVE_REFRESH_TOKEN`.
- `BACKUP_ENCRYPTION_PASSPHRASE`, at least 24 characters, with an offline recovery copy.

The live Render service has separate environment variables. Configuring GitHub Actions does not configure the Render runtime automatically.

## Integrity and safety behavior

The workflow refreshes a Google OAuth access token, finds exactly one non-trashed folder indexed with private app property `makeupart_root=v1`, then enumerates files directly inside it using pagination. Each object must have a valid, unique `makeupart_path` index. The workflow fails closed for a missing/ambiguous root, invalid or unsafe paths, duplicate paths, empty objects, unsupported Google Workspace files, incomplete downloads, checksum mismatch, files larger than 512 MiB, or a total archive above 3 GiB. It does not log media IDs, private paths, OAuth tokens or image contents.

It builds a manifest with each relative path, size, SHA-256 and MD5. Files and manifest are packed into a deterministic tar archive and encrypted with GPG symmetric AES-256. Before uploading, the workflow decrypts a copy into isolated temporary storage and compares the restored file set, byte counts and SHA-256 values with the manifest. Only the encrypted archive and its SHA-256 sidecar are uploaded. Temporary decrypted media and passphrase files are removed from the runner.

The paired workflow [`.github/workflows/production-media-restore-drill.yml`](https://github.com/mipox331-netizen/makeupart-v8/blob/main/.github/workflows/production-media-restore-drill.yml) runs after a successful backup or manually against a selected successful run. It verifies the artifact, decrypts it and checks its contents in temporary storage. It does not modify production Google Drive.

## Latest observed result

- [Media backup run #53](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40442965971) was rerun on 28 October and failed because the private Drive inventory contained **0 files / 0 bytes**.
- [Media restore drill run #55](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40732934379) was skipped because no successful non-empty backup artifact exists.

This means the workflow reached the private Drive inventory, but no media objects were available to back up. The empty archive is deliberately not treated as success. A successful OAuth request, a green API health check, or a successful database backup does not prove that salon photos and logos can be restored.

## Required proof before using real customer media

1. Use an explicitly authorized test salon/client/photo; do not upload a real customer's image without consent.
2. Upload a test portrait and salon logo through the live app. Confirm both are present under the private Drive root and have the expected app-private path indexes.
3. Restart Render. Retrieve both images through the authenticated app/API and compare SHA-256 checksums against the originals.
4. Rerun media backup; it must complete with a non-zero file count and total bytes.
5. Run the paired isolated restore drill and verify its file list, sizes and checksums.
6. Keep the encryption passphrase separately offline. Artifacts expire after 14 days and are not indefinite archival.

Until this sequence succeeds, customer-photo/logo durability and recovery remain **unverified**.
