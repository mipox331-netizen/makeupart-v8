# MakeupArt V8 — Cloudflare R2 encrypted backup

## Free allowance and safety

Cloudflare R2 Standard currently includes 10 GB-month of storage, 1 million Class A operations and 10 million Class B operations per month. R2 does not charge for internet egress. The backup uploader enforces a 9.5 GB ceiling for the MakeupArt backup prefix and removes MakeupArt backup objects older than 14 days before uploading. This is a safety guard, not a guarantee about other buckets or usage on the same Cloudflare account; keep the account's total R2 usage within its free allowance.

Official current pricing: https://developers.cloudflare.com/r2/pricing/

## Create the private R2 bucket

1. Open https://dash.cloudflare.com/ and sign in.
2. Go to **Storage & databases → R2 Object Storage**.
3. Create a Standard bucket named `makeupart-v8-backups` (or another unique name).
4. Keep public access disabled. Do not enable the `r2.dev` public URL or attach a public custom domain.
5. Create an R2 API token restricted to this bucket with **Object Read & Write** permissions. Save its Access Key ID and Secret Access Key once.

## GitHub production environment secrets

Open the repository **Settings → Environments → production → Environment secrets** and add:

| Secret | Value |
|---|---|
| `R2_ACCOUNT_ID` | Cloudflare account ID |
| `R2_ACCESS_KEY_ID` | R2 API token Access Key ID |
| `R2_SECRET_ACCESS_KEY` | R2 API token Secret Access Key |
| `R2_BUCKET_NAME` | The private bucket name, e.g. `makeupart-v8-backups` |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase server-side service-role key (never the anon/publishable key) |

The existing `SUPABASE_DB_URL` and `BACKUP_ENCRYPTION_PASSPHRASE` secrets are also required. `SUPABASE_URL` is optional when the database URL contains a Supabase project reference; `SUPABASE_MEDIA_BUCKET` defaults to `makeupart-media`.

Never put these values in source code, a public issue, or a chat message.

## Backup and restore behaviour

- Live customer media is stored in the private Supabase Storage bucket.
- The media workflow inventories and downloads every object from that bucket, verifies the file sizes, and archives the private paths with a manifest.
- Database and media archives are encrypted locally with GPG AES-256 before upload to R2.
- R2 objects are stored under `makeupart-backups/database/<run-id>-a<attempt>/` and `makeupart-backups/media/<run-id>-a<attempt>/`.
- The uploader verifies object size and SHA-256 metadata after upload, then checks the archive against the sidecar checksum on download.
- Restore drills only run after successful R2 upload and restore into temporary isolated environments. They never overwrite production data.
- Backups older than 14 days are pruned by category. If the MakeupArt prefix would exceed 9.5 GB, a new upload is refused before it is started.

## Important migration note

Changing production from `local_only` to `supabase_storage` protects media processed after the deployment succeeds. Photos previously saved only in a customer's Android Gallery are not automatically copied to the Supabase bucket. The phone Gallery remains a second on-device copy, not an off-site backup.
