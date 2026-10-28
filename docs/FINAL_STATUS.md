# MakeupArt V8 — Current Engineering Status

Status checked: 27 October 2026. This report separates verified source checks from production behaviors that still lack evidence.

## Verified

- Current `main`: [`ac9921fbc7367c2c311026c7361c489a4be7eff4`](https://github.com/mipox331-netizen/makeupart-v8/commit/ac9921fbc7367c2c311026c7361c489a4be7eff4).
- Main CI [#678 passed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40121282729) for that commit on 24 October.
- Production monitor [#701 passed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40563215368) on 27 October, reporting healthy liveness/readiness; it does not log the currently deployed source SHA.
- Encrypted database backup [#48](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40441672336) and isolated restore drill [#58](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40441747764) passed on 27 October.
- PRs [#38](https://github.com/mipox331-netizen/makeupart-v8/pull/38) and [#39](https://github.com/mipox331-netizen/makeupart-v8/pull/39) are merged. Their source changes cover Gallery publication confirmation/history deduplication and upload response validation before media/job/quota completion. Their PR CI runs passed.

## Blockers and residual risks

- **Public APK is stale and debug-signed.** Latest public artifact is [v8.0.201](https://github.com/mipox331-netizen/makeupart-v8/releases/tag/v8.0.201), built from `3a666d4ff610c30fcc6342a71204cba2b288ada1` on 23 October. Release run [#201](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39967233385) explicitly reports missing `ANDROID_KEYSTORE_BASE64` and the Android Debug signing certificate. It is not Play Store-ready and may not update previously installed copies signed with another key.
- **Latest-source release hardening is proposed, not merged.** PR [#40](https://github.com/mipox331-netizen/makeupart-v8/pull/40) guards against stale CI commits publishing APKs and gates releases on same-commit dependency-security and license checks. Its CI/security/license runs are the remaining PR checks.
- **Photo/logo recovery is not proven.** Media backup [#53 failed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40442965971) on 27 October because Google Drive inventory was empty (0 files / 0 bytes); media restore drill [#53 was skipped](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40442985353).
- **Database source agreement is unverified.** The database backup/restore workflow passes, but the live Render `DATABASE_URL` has not been independently matched to the backup URL.
- **Device smoke test is missing.** No evidence in the repository proves complete latest-source registration/login, consent, camera/gallery, image processing, salon logo/watermark, before/after, gallery export and update compatibility on a physical Android device.
- **Branch protection is not reverified.** The previous audit recorded `main` as unprotected; current branch protection could not be read through the connected GitHub integration.
- **Dependency security exception remains.** `PYSEC-2026-1805` is explicitly excluded from the Python audit because of MediaPipe/protobuf compatibility constraints and a documented unused code path. Treat it as residual risk until the vision stack can be upgraded and retested.
- **Generative AI is not verified enabled.** Classic MediaPipe/OpenCV processing is the available no-provider mode. Generative editing needs provider credentials and consent; no paid provider or zero-cost production model is confirmed.
- **Distribution claims remain limited.** No successful Play Store rollout or signed iOS/App Store release is verified.

## Release decision

**Not yet production-ready for a full public launch.** Source CI and database restore mechanics have passed, but a fresh keystore-signed APK, same-commit release gates, durable customer-media recovery, database-source agreement and real-device smoke tests remain unresolved. Keep each gate open until its evidence is recorded.
