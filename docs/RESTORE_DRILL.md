# Encrypted PostgreSQL backup restore drill

## Purpose

This manual workflow downloads an existing encrypted database backup artifact, verifies its SHA-256 checksum, decrypts it, restores it to a fresh disposable PostgreSQL 17 service inside the GitHub Actions job, and checks the Alembic head and required schema tables.

**Safety boundary:** the workflow has no `SUPABASE_DB_URL`, `SUPABASE_DB_URL_SECRET`, or `DATABASE_URL` environment variable and never connects to production. The temporary database is created for this one job and removed when the job finishes. The decrypted dump and passphrase file are removed in the cleanup step.

## Run the drill

1. Open **Actions → MakeupArt V8 Encrypted Database Restore Drill → Run workflow**.
2. Enter a successful run ID from **MakeupArt V8 Encrypted Production Database Backup**. The current verified backup run at the time this workflow was introduced is `38251453670`, provided its artifact has not expired.
3. Run the workflow and inspect the final verification step.

A pass means the chosen artifact's checksum matches, GPG can decrypt it, `pg_restore` can restore it to a blank PostgreSQL database, the revision is `0009_reconcile_refresh_sessions`, all 11 required tables exist, and subscriptions have no orphan salon references. If `users`, `salons` and `subscriptions` are all empty, the workflow reports a valid **empty-database restore** but explicitly does not claim row-data recovery was tested. A populated backup must restore all three core tables with data; partial core data fails the drill.

## What this does not prove

This verifies a PostgreSQL logical database backup only. It does not restore or verify customer images stored in the separate Modal media volume, and it is not a full disaster recovery drill for the live application. Media needs a separate private off-host backup and its own restore test. Run this drill regularly and after backup-format, schema or PostgreSQL-version changes.

The artifact must still exist within the GitHub Actions retention window, and `BACKUP_ENCRYPTION_PASSPHRASE` must be available in the `production` GitHub environment. Keep the passphrase recovery copy offline; never place it in workflow inputs, logs or source code.
