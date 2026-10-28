# MakeupArt V8 Production Runbook

Last checked: 28 October 2026.

## 1. Active services and deployed source

The Flutter Android app and release workflows target the Render API:

[`https://makeupart-api.onrender.com/api/v1`](https://makeupart-api.onrender.com/api/v1)

Current application/release source is merge commit [`460b923`](https://github.com/mipox331-netizen/makeupart-v8/commit/460b923cc62a3b87d4d30a8b6d769826f5879eb0). Main CI [#705](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40738076624), dependency audit [#222](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40738076774) and license inventory [#241](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40738076643) all passed on that exact merge SHA. CI includes backend tests/migrations, Flutter analysis/tests, the release-version selector shell check and an Android debug APK build.

Render deployment [`dep-dbh2mdq9lscs73806vlg`](https://dashboard.render.com/web/srv-dav25so473hc73d7ee0g) is live on backend commit [`c3b7532`](https://github.com/mipox331-netizen/makeupart-v8/commit/c3b7532f3786dde98e4a2209480adfaf56d77dfa) and its configured [`/health/ready`](https://makeupart-api.onrender.com/health/ready) check passed on 28 October. The current main commit adds app version and release-workflow changes; it does not change backend runtime code. Health readiness proves availability, not customer-media durability or database backup target parity.

Modal is not the current production host. Do not point mobile builds back to the historical Modal URL.

## 2. Android release and update compatibility

The Flutter manifest declares [`8.0.202+202`]. The Android release workflow selects the next unused version from published [`v8.0.N`] tags, not GitHub Actions run numbers. CI extracts the version-selector step and validates its Bash syntax to prevent a broken selector from silently passing tests.

The latest public APK remains [v8.0.201](https://github.com/mipox331-netizen/makeupart-v8/releases/tag/v8.0.201), published on 23 October and signed by Android Debug. It is older than current source and may not update an app signed with another key. Current-source release workflow [#215](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40738596006) failed closed because [`ANDROID_KEYSTORE_BASE64`] is missing.

For update-compatible releases configure these GitHub [`production`] environment secrets from the **same persistent keystore** used for the installed release:

- [`ANDROID_KEYSTORE_BASE64`]
- [`ANDROID_STORE_PASSWORD`]
- [`ANDROID_KEY_PASSWORD`]
- [`ANDROID_KEY_ALIAS`]

Do not bypass the signing guard or replace the key just to make a workflow green. Release also requires exact-source CI/security/license checks, live API liveness/readiness and expected backend commit, certificate verification, and the last-minute current-main check.

## 3. Google Drive customer media and restore

The active workflow [`.github/workflows/production-media-backup.yml`](https://github.com/mipox331-netizen/makeupart-v8/blob/main/.github/workflows/production-media-backup.yml) backs up the app's private Google Drive media root—not the old Modal volume. It requires [`GOOGLE_DRIVE_CLIENT_ID`], [`GOOGLE_DRIVE_CLIENT_SECRET`], [`GOOGLE_DRIVE_REFRESH_TOKEN`] (or established [`GDRIVE_*`] aliases) and [`BACKUP_ENCRYPTION_PASSPHRASE`] of at least 24 characters in GitHub's [`production`] environment. Render environment values are separate from GitHub Actions secrets.

Backup [#53](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40442965971) failed again on 28 October with **0 files / 0 bytes** in the private Drive inventory. Restore drill [#55](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40732934379) was skipped. Do not call customer-media backup complete.

To close this gate, use an authorized test salon and a test portrait/logo; upload through the live app; confirm both in private Drive; restart Render; retrieve both and compare SHA-256 checksums; then rerun backup and its isolated restore drill with a non-zero file count. The restore workflow must not modify production files during the drill.

## 4. Database backup and restore

Encrypted PostgreSQL backup [#48](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40441672336) and isolated restore drill [#58](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40441747764) passed on 27 October. They verify the URL supplied to the backup workflow; they do not independently prove that the live Render database was the backup source.

Verify that Render's runtime [`DATABASE_URL`] and the GitHub [`production`] backup URL point to the same Supabase project, without pasting full URLs/passwords into chat, source code or logs. Retain encrypted artifacts and checksums; store the passphrase separately offline.

## 5. Security, authentication and app operations

- Backend uses FastAPI/PostgreSQL/Alembic, salon-scoped records/media, refresh-session revocation, consent enforcement, quota controls and a platform-admin allowlist.
- PR #41 fixed concurrent first-use subscription creation by locking the parent salon row and rechecking the subscription. PostgreSQL concurrency regression and the backend test suite passed in CI.
- Python dependency audit has a documented exception for [`PYSEC-2026-1805`] under the pinned MediaPipe/protobuf constraint and the stated unused JSON parser path. Treat this as residual dependency risk, not as zero vulnerabilities.
- Classic MediaPipe/OpenCV is the no-provider mode. Generative processing requires configured external provider access and explicit consent; it is not confirmed enabled.
- Before launch, test registration/login, consent resets, salon isolation, camera/gallery, image processing, logo/watermark, before/after, gallery export and update compatibility on a physical Android device.

## 6. Repository and commercial release controls

The connected integration could not read [`main`] branch protection; the accessible repository rulesets endpoint returned an empty list. An administrator should require CI, dependency-security and license checks before merge and restrict direct pushes in GitHub settings. Do not claim Google Play or App Store publication without verifiable rollout/build evidence. Review the proprietary project license and all third-party asset/model terms before commercial distribution.

## 7. Monitoring and incident response

The scheduled monitor checks Render liveness/readiness every 15 minutes. A green health monitor is not proof of successful photo upload or restore and does not provide independent SMS/pager alerting. During an incident, correlate [`X-Request-ID`] with server logs; never log access/refresh tokens, customer photos or provider secrets.
