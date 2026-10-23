# MakeupArt V8 — Current Engineering Status

Status checked: 23 October 2026. This document separates verified checks from unproven production behavior.

## Verified

- Current main commit at audit start: [`8b2aee9269628e58089a89cf3486bb385932179f`](https://github.com/mipox331-netizen/makeupart-v8/commit/8b2aee9269628e58089a89cf3486bb385932179f).
- Main CI [#604 passed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39814335892) on that commit.
- Production monitor [#508 passed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39906865481): `/health/live` reported `alive` and `/health/ready` reported `ready` for the Render API at the probe time.
- Encrypted database backup [#44 passed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39892512971), and isolated restore drill [#54 passed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39892567266).
- Source includes FastAPI/PostgreSQL/Alembic, salon-scoped authentication and media, login rate limiting and token revocation, consent checks, client records, classic MediaPipe/OpenCV beauty effects, before/after output, salon watermarks, Gallery export, recent-image handling, subscriptions and platform-admin operations.
- The Classic pipeline runs without a paid external image-provider key. Generative editing is optional, requires server-side provider access and separate external-processing consent, and is not verified as enabled.

## Not yet proven / blockers

- **Current APK:** [v8.0.195](https://github.com/mipox331-netizen/makeupart-v8/releases/tag/v8.0.195) is the latest public artifact. It was built from commit `6ac6233`, not the latest main commit, and used Flutter's debug signing key because `ANDROID_KEYSTORE_BASE64` was absent. Android workflow [#196](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39814335881) skipped the APK build job after classifying the latest backend change; a green workflow did not mean a new APK was produced.
- **Photo/logo recovery:** encrypted media backup [#48 failed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39893692218) because the private Google Drive inventory had 0 files / 0 bytes. Its restore drill was skipped. Durable customer-media backup and restart recovery are not proven.
- **Runtime source identity:** the scheduled monitor proved health/readiness but did not report the current Render commit, so health does not prove that the latest repository commit is deployed.
- **Database source agreement:** the encrypted backup and restore drill passed, but the live Render `DATABASE_URL` has not been independently confirmed to be the same database URL used by GitHub backup.
- **Real-device operation:** no successful end-to-end device smoke test is recorded for registration, login, photo processing, logo/watermark, gallery export, update compatibility and logout on the latest source.
- **Android signing/Play Store:** no persistent release keystore was present in the latest public build, and no successful Google Play rollout is verified. No signed iOS/App Store release is verified.
- **Branch protection and licensing:** `main` is not branch-protected; this repository is public while its original-source license is proprietary. Review both the branch settings and intended distribution model.
- **Commercial AI:** no free production-ready generative model was activated; do not advertise Classic effects as FaceApp-equivalent reference-image transfer.

## Current fixes being prepared

The production-readiness branch adds `RENDER_GIT_COMMIT` to the ready health response, tests that behavior, and changes the Android release workflow to wait for the live API to report the exact expected backend commit before building/publishing. This prevents the previous “green but skipped APK” ambiguity and guards against packaging against a stale backend. Documentation has been aligned with current workflow evidence.

## Release decision

**Not yet production-ready for a full public launch.** The source checks and database restore mechanics are healthy, but photo/logo durability, current-source APK build, persistent signing, database-source agreement, and real-device smoke test remain release gates. Do not mark a gate complete until its corresponding evidence is available.
