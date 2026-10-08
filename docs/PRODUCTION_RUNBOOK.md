# MakeupArt V8 Production Runbook

## 1. Primary production path

The live production backend runs on Modal and uses Supabase PostgreSQL.

Production API:
`https://mipox331-netizen--makeupart-v8-api-fastapi-app.modal.run`

Deploys are driven by GitHub Actions through `.github/workflows/modal-deploy.yml`.

The deployment gate:
1. Validates Modal credentials.
2. Validates the Supabase PostgreSQL connection.
3. Provisions the Modal production secret.
4. Deploys FastAPI.
5. Runs Alembic migrations.
6. Confirms the migration head.
7. Verifies MediaPipe + InsightFace runtime.
8. Verifies `/health/ready`.

## 2. Required production secrets

Store these in the GitHub production environment / repository secrets as appropriate:

- `MODAL_TOKEN_ID`
- `MODAL_TOKEN_SECRET`
- `SUPABASE_DB_URL` or `SUPABASE_DB_URL_SECRET`
- `SUPABASE_SECRET_KEY` / supported Supabase secret
- `SUPABASE_ANON_KEY`
- `SUPABASE_SECRET` / service-role key
- `PLATFORM_ADMIN_EMAILS`

`PLATFORM_ADMIN_EMAILS` is a comma-separated allow-list of the e-mail addresses that are allowed into the project admin area.

Never commit secret values.

## 3. User access and subscriptions

Every new salon starts on the permanent `free` plan with a monthly AI-processing quota of 25 jobs.

The project admin can:
- view all registered users across salons;
- see active vs blocked users;
- block or unblock an individual user;
- suspend or reactivate a salon subscription;
- activate Free, Basic, Pro or Enterprise plans.

Blocking a user sets `is_active=false` and is enforced at the authenticated API boundary, so an already-issued access token stops working immediately.

A suspended paid subscription is prevented from AI processing until reactivated. The user's account data is retained.

## 4. Health verification

Check the public API:

```bash
curl https://mipox331-netizen--makeupart-v8-api-fastapi-app.modal.run/health/ready
```

## 5. Mobile production build

Android release builds use:

```text
https://mipox331-netizen--makeupart-v8-api-fastapi-app.modal.run/api/v1
```

The APK workflow runs Flutter dependency resolution, analysis, tests, release build verification, artifact upload, and public GitHub Release publication.

## 6. Self-hosted alternative

The repository still includes `backend/docker-compose.production.yml` with PostgreSQL, private media, and Caddy HTTPS termination for a self-hosted deployment.

Use that path only when deliberately hosting outside Modal/Supabase.

## 7. Security checklist

- HTTPS is mandatory in production.
- Keep `CORS_ORIGINS` explicit.
- Keep production secrets outside Git.
- Keep media private and serve it only through authenticated API routes.
- Review InsightFace `buffalo_l` licensing before commercial deployment.
- Review retention/deletion policies before public launch.
