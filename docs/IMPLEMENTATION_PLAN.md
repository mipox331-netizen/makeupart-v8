# Implementation Plan

## Delivered
- Repository, environment configuration, Docker Compose, PostgreSQL and Alembic.
- Authentication, refresh rotation/revocation and salon isolation.
- Customer, consent and consultation workflows.
- Beauty processing, identity-guard retry logic and protected media delivery.
- Secure image validation and metadata normalization.
- Job history and privacy deletion.
- Flutter registration/login, token refresh, client selection, consent, camera/gallery and result viewing.
- Android/iOS platform scaffolding and mobile CI.
- Production Compose/Caddy stack, health checks, cleanup and backup tooling.

## Deployment work that remains environment-specific
- Put production secrets into the deployment secret manager.
- Point DNS at the production host and let Caddy obtain certificates.
- Configure real Android signing and Play Console credentials.
- Configure Apple signing, provisioning and App Store Connect credentials.
- Establish monitoring, alerting and an off-host backup policy.
- Review InsightFace model licensing before commercial launch.

## Constraints
- The current beauty effect is classical image enhancement, not a generative makeup model.
- Shade estimation is still request-driven and should be evaluated before commercial claims.
