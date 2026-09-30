# MakeupArt V8 Architecture

## Runtime
- FastAPI API with PostgreSQL and Alembic.
- Flutter mobile client with Dio and secure token storage.
- Docker Compose for development and production.
- Caddy reverse proxy for production HTTPS.

## Authentication
Access JWTs are short-lived and include a unique `jti`. Refresh JWTs are stored server-side as SHA-256 token hashes, rotated on use, and revocable on logout.

## Salon isolation
Every customer, consultation, consent, beauty job, result and media path is checked against the authenticated salon ID. Media paths are physically partitioned under `MEDIA_ROOT/salons/<salon_id>/`.

## Beauty pipeline
1. Authenticate operator.
2. Confirm operator consent.
3. Resolve optional customer and require active stored customer consent.
4. Validate upload type, bytes, decoded image and pixel count.
5. Normalize the stored input image to remove embedded metadata.
6. Run MediaPipe face landmarks and OpenCV enhancement.
7. Measure identity similarity with InsightFace.
8. Retry at lower intensity when the similarity guard fails.
9. Persist job/result metadata.
10. Serve before/after assets only through authenticated endpoints.

## Privacy
Customer deletion removes customer records, consent records, consultations, beauty jobs and associated media. A daily cleanup service removes data beyond the configured retention period and old refresh sessions.

## Operations
Production uses a non-root backend container, DB connection pooling, liveness/readiness checks, security response headers, private media volumes, Caddy HTTPS termination, and a documented PostgreSQL backup helper.

## Mobile release
Android and iOS platform projects are checked into the repository. Android debug APKs are built in CI; release signing remains deployment-specific.
