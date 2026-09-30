# MakeupArt V8 Production Runbook

## 1. Prepare production configuration
From `backend/`, copy `.env.production.example` to `.env.production` and replace every placeholder. Use a strong random `SECRET_KEY`, a strong PostgreSQL password, explicit `CORS_ORIGINS`, and the public API `DOMAIN`.

Never commit `.env.production`.

## 2. Start production stack
From `backend/`:

```bash
docker compose -f docker-compose.production.yml --env-file .env.production up -d --build
```

Caddy terminates HTTPS and proxies traffic to the private backend service. PostgreSQL and media volumes are not published to the host network.

## 3. Verify
Check the API health endpoint through the public domain:

```bash
curl https://YOUR_API_DOMAIN/health/ready
```

Then open the Flutter client with:

```bash
flutter run --dart-define=API_BASE_URL=https://YOUR_API_DOMAIN/api/v1
```

## 4. Backups
Back up PostgreSQL regularly with `pg_dump` from a trusted host or backup job. The database contains users, customers, consent history, consultations, and job metadata.

Media in the `media_prod` volume must be backed up separately or moved to private object storage before large-scale production use.

## 5. Retention
The cleanup service runs once per day. It removes media older than `MEDIA_RETENTION_DAYS` and expired/revoked refresh sessions older than `REFRESH_SESSION_RETENTION_DAYS`.

Do not shorten image retention without checking customer-consent and business-retention requirements.

## 6. Recovery
Database restore should be performed into a stopped or isolated PostgreSQL instance before reconnecting the application. Restore media from the corresponding backup set so job records and image files remain aligned.

## 7. Mobile release
Android and iOS platform projects are bootstrapped by GitHub Actions. Android debug builds are CI-verified when the platform folder exists. Release signing, Play Console/App Store Connect credentials, bundle identifiers, and production API configuration remain deployment-specific secrets.

## 8. Security checklist
- HTTPS is mandatory in production.
- Keep `CORS_ORIGINS` explicit.
- Keep `.env.production` outside Git.
- Review InsightFace `buffalo_l` licensing before commercial deployment.
- Keep media private; expose images through authenticated API routes.
- Review the image retention period and deletion policy with the business/privacy owner.
- Add centralized monitoring and alerting before public launch.
