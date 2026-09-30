# Implementation Plan

## Delivered
- Repository foundation, Docker Compose, environment handling, PostgreSQL and Alembic.
- Salon registration, JWT access authentication, rotating/revocable refresh sessions, role checks and salon isolation.
- Customer and consultation workflows with active consent enforcement.
- Consent records with grant/revoke and optional expiry.
- Beauty processing with MediaPipe, InsightFace identity guard and bounded OpenCV enhancement.
- Secure upload validation, size/pixel limits and salon-scoped media storage.
- Authenticated before/after image delivery.
- Flutter registration, login, session restoration, automatic token refresh, gallery/camera selection and consent-gated beauty processing.
- Backend pytest plus Flutter analyzer/widget CI.

## Production hardening still required
- HTTPS and production secret management.
- Private object storage with backup/retention controls.
- Rate limiting, monitoring, alerting and structured audit logs.
- Validated image-based shade estimation and documented model/license review.
- Optional asynchronous worker queue for longer-running AI inference.

## Constraints
- No fake AI result generation is used.
- The current beauty effect is classical enhancement rather than generative makeup.
- Production privacy and model licensing decisions must be completed before public launch.
