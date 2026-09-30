# Implementation Plan

## Phase 1: repository foundation
- Verify the backend skeleton and fix dependency/runtime mismatches
- Standardize environment configuration and secrets handling
- Verify database connectivity, Alembic configuration, and app bootstrap

## Phase 2: authentication and authorization
- Review salon registration, owner creation, login, token refresh, and role checks
- Add salon isolation at the data-access layer
- Add tests for duplicate email, inactive user, and invalid credentials

## Phase 3: salon and customer workflows
- Add customer records, consultation tracking, and watermark metadata
- Add salon-scoped API endpoints and tests for cross-salon enforcement

## Phase 4: beauty processing and identity guard
- Implement MediaPipe Face Mesh landmark detection and OpenCV skin smoothing
- Use InsightFace embeddings to measure identity similarity and enforce the configured threshold
- Keep shade classification explicitly based on request-provided input until an image-based, evaluated approach is approved
- Verify model and dataset licensing before commercial deployment

## Phase 5: mobile app
- Create the Flutter app skeleton and core routing/auth structure
- Add salon-oriented UI screens for camera, consultation, gallery, and settings
- Integrate API client patterns with Dio and secure storage

## Phase 6: verification and delivery
- Run backend pytest coverage
- Validate docker compose startup and migration behavior
- Attempt Flutter analysis/test if the toolchain is available
- Produce the final status report and document known limitations

## Constraints
- No fake endpoints or placeholder implementations are acceptable
- Any AI limitations in this environment must be documented honestly
- If Flutter is not available in the container, the mobile project must still be scaffolded and marked as not verified
