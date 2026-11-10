# MakeupArt V8 — private GitHub backup storage

This backup path does not require Cloudflare, a credit card, or a paid storage subscription. It uses a **separate private GitHub repository** for encrypted release assets, while Supabase Storage remains the application's private live media store.

## 1. Create the private backup repository

1. Open https://github.com/new.
2. Repository name: \`makeupart-v8-backups\`.
3. Set visibility to **Private**.
4. Initialize it with a README so the repository has a default branch.
5. Create the repository.

Do not use the public \`makeupart-v8\` application repository as the backup destination. The uploader checks the target repository's visibility and refuses to upload unless it is private and separate from the application repository.

## 2. Create a restricted GitHub token

1. Open https://github.com/settings/personal-access-tokens/new.
2. Choose **Fine-grained token**.
3. Set the resource owner to the account that owns \`makeupart-v8-backups\`.
4. Under repository access, choose **Only select repositories** and select \`makeupart-v8-backups\`.
5. Grant **Contents: Read and write**. Metadata read is granted automatically.
6. Create the token and copy it once. Never put it in source code, an issue, or a chat.

Use an expiry date you can manage. Rotate the token before it expires.

## 3. Add GitHub production environment secrets

Open the application repository's **Settings → Environments → production → Environment secrets** and add:

| Secret | Value |
|---|---|
| \`BACKUP_REPOSITORY\` | \`ACCOUNT_NAME/makeupart-v8-backups\` |
| \`BACKUP_REPOSITORY_TOKEN\` | The fine-grained token created above |

Keep the existing secrets:

- \`SUPABASE_DB_URL\` (or the already-used equivalent \`SUPABASE_DB_URL_SECRET\` / \`DATABASE_URL\`)
- \`BACKUP_ENCRYPTION_PASSPHRASE\` — at least 24 characters; use a long, random passphrase and keep a separate offline copy
- \`SUPABASE_SERVICE_ROLE_KEY\` — server-side Supabase key, never the publishable/anon key
- \`SUPABASE_URL\` when it cannot be derived safely from the database URL
- \`SUPABASE_MEDIA_BUCKET\` is optional; defaults to \`makeupart-media\`

No \`R2_*\` secrets or Cloudflare subscription are needed.

## Backup and restore behaviour

- Customer photos are stored in the private \`makeupart-media\` Supabase Storage bucket for live app access.
- The media workflow downloads the private bucket, creates a manifest with file sizes and SHA-256 hashes, and encrypts the archive with GPG AES-256.
- The database workflow creates a PostgreSQL dump, encrypts it with GPG AES-256, and validates it before publishing.
- Each encrypted database or media archive is uploaded as a separate prerelease asset in the private backup repository.
- The uploader verifies the uploaded files by downloading them again and checking SHA-256 before the backup workflow can pass.
- Restore drills download only from the private backup repository and restore the database into an isolated temporary PostgreSQL service. Media restore drills extract into a temporary directory and compare every file to the manifest; production is never overwritten.
- Releases older than 14 days are removed by category. Each release asset must be smaller than GitHub's 2 GiB per-file limit.
- If the private repository or token is missing, invalid, or not private, backup fails closed. A failed upload cannot be marked as a successful restore.

## Free-plan boundaries

- GitHub Free supports private repositories. GitHub documents a per-release asset limit of 1000 files, a per-file size below 2 GiB, and no total-size or bandwidth limit for release assets. The workflow still keeps only 14 days of backups.
- Supabase Free includes 1 GB of file storage and 500 MB of database size per project. This is a limit, not unlimited storage; keep an eye on usage.
- Supabase Free does not provide automatic daily database backups. These GitHub workflows provide a separate encrypted export and restore drill instead.

Official references:
- https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
- https://github.com/pricing
- https://supabase.com/pricing
- https://supabase.com/kb/faqs/platform/free-plan-backups

## Migration note

Photos processed while production was configured as \`local_only\` were not uploaded to the server, so they are not retroactively copied into Supabase. Existing phone Gallery copies remain on the customer's device unless uploaded again. New photos are protected by private Supabase Storage only after the deployment workflow succeeds.
