# MakeupArt V8 Architecture

## Overview
MakeupArt V8 is a salon-first beauty AI platform that keeps the user’s identity recognizable while applying non-destructive enhancement. The system is organized around a secure backend, a local-first mobile client, and a modular beauty pipeline that can later swap AI providers without rewriting the application.

## Runtime components

### Backend
- FastAPI application in `backend/app`
- PostgreSQL 16 persistence with SQLAlchemy 2 and Alembic migrations
- JWT-based auth with salon-scoped access control
- Job-driven beauty processing pipeline
- Background worker model for AI inference and validation

### Mobile app
- Flutter application under `makeup_art_v8/`
- Riverpod for state and dependency injection
- go_router for navigation
- dio for API communication
- flutter_secure_storage for JWT persistence

## Domain model
- Users belong to a salon and have roles: owner, admin, staff
- Salons own their customers, jobs, results, consultations, and branding
- Customers store identity and privacy consent metadata
- Beauty jobs encapsulate image processing work and progress state
- Beauty results store before/after references and validation metrics
- Consultations record final looks selected for a customer
- Watermarks are generated per salon branding configuration

## Security and privacy
- All user data is isolated by salon ID
- API access derives salon ownership from the authenticated session
- Explicit consent is required before any AI processing is accepted
- Local/on-device processing is preferred to minimize external uploads
- Secrets are kept in `.env` and never committed to source control

## Beauty pipeline
1. Capture or upload an image
2. Validate consent and salon ownership
3. Create beauty job in the database
4. Worker loads provider and image data
5. Run face detection and skin-tone analysis
6. Apply makeup adjustments with bounded intensity levels
7. Run identity guard similarity check
8. Reduce intensity if guard fails and reprocess
9. Return result plus metadata and before/after asset references

## Identity guard rule
The system measures similarity between the original and processed image with an embedding-based comparison. If similarity drops below the threshold, the engine reduces intensity and retries. If the threshold cannot be satisfied, it fails the job with a clear error instead of improving a misleading result.

## Data isolation rules
- A salon may only read or modify records belonging to its own salon
- Cross-salon access is rejected with 404/403 responses
- Staff cannot alter salon branding or delete the owner account

## Deployment
The backend is containerized with Docker and is expected to run with PostgreSQL in `docker-compose.yml`. The API is exposed on port 8000 and includes a `/health` endpoint.
