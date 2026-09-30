# MakeupArt V8 Architecture

## Overview
MakeupArt V8 is a salon-first beauty AI platform that preserves recognizable identity while applying bounded enhancement.

## Runtime components

### Backend
- FastAPI with PostgreSQL 16, SQLAlchemy 2 and Alembic.
- JWT access tokens plus server-tracked, rotating refresh sessions.
- Salon-scoped authorization and authenticated media delivery.
- Consent records and consent enforcement before AI processing.
- Local media storage for the MVP.

### Mobile app
- Flutter Material 3 application.
- Dio API client with automatic access-token refresh.
- flutter_secure_storage for token persistence.
- image_picker for gallery and camera input.

## Security and privacy
- Access tokens are short lived; refresh tokens are rotated and revocable.
- Stored refresh tokens are represented by SHA-256 hashes in the database.
- All domain access is checked against the authenticated user's salon.
- Beauty processing requires explicit operator consent confirmation.
- Customer-linked processing additionally requires an active stored consent record when configured.
- Uploads are restricted by media type, byte limit, successful decode, and pixel limit.
- Stored media paths are constrained to MEDIA_ROOT.
- Production rejects wildcard CORS.

## Beauty pipeline
1. Authenticate the operator.
2. Confirm client consent.
3. Optionally resolve a salon customer and require active stored consent.
4. Validate and store the input image.
5. Run the provider with a managed output directory.
6. Detect face landmarks and apply bounded OpenCV enhancement.
7. Measure identity similarity with InsightFace embeddings.
8. Reject results below the configured identity threshold.
9. Persist job/result metadata and expose media through authenticated endpoints.

## Deployment
The MVP uses Docker Compose with PostgreSQL and a mounted media volume. Production should add HTTPS, private object storage, rate limiting, monitoring, backup/restore, and a documented image-retention policy.
