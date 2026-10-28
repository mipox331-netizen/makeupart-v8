# MakeupArt V8 — Current Engineering Status

Status checked: 28 October 2026. This report distinguishes merged source fixes, verified CI, live service evidence, and production gates that remain open.

## Verified source and automated checks

- Current main merge commit: [`460b923`](https://github.com/mipox331-netizen/makeupart-v8/commit/460b923cc62a3b87d4d30a8b6d769826f5879eb0).
- [PR #40](https://github.com/mipox331-netizen/makeupart-v8/pull/40) merged release hardening: stale-source guards, same-commit security/license gates and Java 17 CI.
- [PR #41](https://github.com/mipox331-netizen/makeupart-v8/pull/41) fixed concurrent first-time subscription creation by locking the parent salon row and rechecking, with PostgreSQL concurrency regression coverage.
- [PR #43](https://github.com/mipox331-netizen/makeupart-v8/pull/43) aligned Flutter version metadata to [`8.0.202+202`], changed release numbering to derive the next unused version from published tags, added release-selector shell validation to CI, and corrected the iOS compile-check API target to Render.
- Main CI [#705](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40738076624) passed on merge commit [`460b923`](https://github.com/mipox331-netizen/makeupart-v8/commit/460b923cc62a3b87d4d30a8b6d769826f5879eb0). Backend build/migrations/tests including PostgreSQL concurrency regression, Flutter analysis/tests, and Android debug APK build/artifact upload all passed.
- Python dependency audit [#222](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40738076774) and third-party license inventory [#241](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40738076643) passed for the exact same main commit.
- Render backend deployment [`dep-dbh2mdq9lscs73806vlg`](https://dashboard.render.com/web/srv-dav25so473hc73d7ee0g) is live on backend commit [`c3b7532`](https://github.com/mipox331-netizen/makeupart-v8/commit/c3b7532f3786dde98e4a2209480adfaf56d77dfa). Its configured [`/health/ready`](https://makeupart-api.onrender.com/health/ready) check passed. PR #43 changed the Flutter version and workflows, not the backend service code.

## Current debug APK

- The main-CI build artifact is available from [CI #705](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40738076624).
- The extracted APK was inspected as an Android package and passed ZIP integrity checking. SHA-256: [`5f2b0cb7c04e528f615b76c5200072c84b3659142746361de155572b5914582e`].
- This is a **debug-signed APK**, for controlled testing only. It is not a current-source release APK or a Play Store package.
- The latest public release remains [v8.0.201](https://github.com/mipox331-netizen/makeupart-v8/releases/tag/v8.0.201), from an older source commit and signed by Android Debug.

## Blockers and residual risks

- **Release signing is blocked.** Current-source Android release run [#215](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40738596006) failed at the mandatory signing-secret guard: [`ANDROID_KEYSTORE_BASE64`] is missing. The workflow correctly refused to build or publish using an ephemeral debug key. Configure all four persistent signing secrets from the same keystore as the installed app; do not invent a replacement key.
- **Customer media recovery is not proven.** Google Drive media backup [#53](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40442965971) was rerun on 28 October and failed with [`0 files / 0 bytes`]; restore drill [#55](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40732934379) was skipped. An authorized test upload, Render restart, checksum-verified retrieval, non-empty encrypted backup and isolated restore are still required.
- **Database source agreement is unverified.** Encrypted database backup [#48](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40441672336) and isolated restore [#58](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40441747764) passed on 27 October, but the live Render [`DATABASE_URL`] was not independently matched to the GitHub backup URL.
- **Real-device smoke test remains open.** No evidence yet confirms registration/login, consent reset, camera/gallery, processing, salon logo/watermark, before/after, gallery export, logout/re-login, and update compatibility on a physical Android device.
- **Repository protection is unresolved.** The accessible rulesets endpoint returned an empty list; branch protection could not be read by this integration. An administrator must require CI/security/license checks and restrict direct pushes in GitHub settings.
- **Dependency audit has a documented high-severity exception.** The Python audit ignores [`PYSEC-2026-1805`] due the pinned MediaPipe/protobuf compatibility constraint and the documented unused JSON parser path. This is a residual risk, not a zero-vulnerability claim; test a vision-stack upgrade separately.
- **Generative AI and store release are not verified.** Classic MediaPipe/OpenCV runs without a paid provider key. Generative editing needs server credentials and explicit external-processing consent. Google Play rollout and signed iOS/App Store distribution are not verified.
- **Stale feature PR #18 is not safe to merge as-is.** It has a competing Alembic [`0010`] migration head and requires a separate rebase, migration reconciliation, and review.

## Release decision

**Not fully production-ready for public customer launch.** The live backend, subscription concurrency fix, current-source CI and debug build are verified. Persistent signing, real photo durability/recovery, live-vs-backup database agreement, and physical-device verification remain open. Keep these gates visible and do not mark them green without evidence.
