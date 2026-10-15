# MakeupArt V8 Architecture

## Runtime
- FastAPI backend with PostgreSQL and Alembic.
- Flutter Android/iOS client using Dio and secure token storage.
- Render free web service is the endpoint used by the current public Android APK.
- The repository also retains a separate Modal deployment workflow and a Modal media volume; this alternate deployment is not the endpoint used by the current APK.
- Docker Compose + Caddy remains a self-hosted deployment option.

## Authentication
Access JWTs are short-lived and include a unique `jti`. Refresh JWTs are stored server-side as SHA-256 token hashes, rotated on use, and revocable on logout. Admin disabling increments `token_version` so previously issued access tokens are rejected.

## Salon isolation
Every customer, consultation, consent, beauty job, result and media path is checked against the authenticated salon ID. Server media paths are partitioned under `MEDIA_ROOT/salons/<salon_id>/`. Image endpoints require authentication and verify the salon owner for each job.

## Beauty pipeline
1. Authenticate the operator.
2. Require operator consent; when a customer is selected, require active stored customer consent.
3. Validate upload type, bytes, decoded image and pixel count.
4. Normalize the stored input image to remove embedded metadata.
5. Run MediaPipe face landmarks and OpenCV-based enhancement.
6. Apply the classic face-aware cosmetic overlays and bounded skin smoothing.
7. Retry at lower intensity when the image-structure preservation score falls below the configured threshold.
8. Apply the salon watermark and persist job/result metadata.
9. Serve before/after assets through authenticated endpoints.

The structure-preservation score is not biometric identity recognition. Classic processing is not a generative diffusion model. Optional third-party image editing requires separate consent and server-side provider configuration.

## Privacy
Customer deletion removes associated customer records, consent records, consultations, beauty jobs and media. A scheduled cleanup task removes media beyond retention settings and old refresh sessions.

## Operations and disaster recovery

The API exposes liveness/readiness endpoints, uses security response headers and has a production health monitor. GitHub Actions verify the release APK against the configured production endpoint.

**Storage architecture risk:** the live Render API writes image files below `MEDIA_ROOT`; the current media-backup workflow downloads the separate Modal volume `makeupart-v8-media`. There is no evidence that these are the same physical files. Until the live API uses a durable object store and backup/restore targets that same store, recovery of Render-held customer photos is not proven.

The encrypted database backup workflow selects a Supabase database URL secret, while the connected Render workspace also contains a free PostgreSQL instance with a 31 October 2026 expiry. The runtime's actual `DATABASE_URL` target must be verified against the backup source; do not remove database resources before confirming the live connection.

## Mobile release
Android release builds are published through GitHub Releases. The current APK, v8.0.164, passed APK verification and API health checks but used Flutter's debug signing key because Android release-signing secrets are not configured. It is a manual-install APK, not a Play Store release. The in-app update checker prompts for a download and still requires the user to approve Android's install.
