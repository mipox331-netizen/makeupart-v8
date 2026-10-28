# Mobile Release Notes

Status checked: 28 October 2026 against GitHub Actions and the connected Render workspace.

## Version and APK state

- Flutter manifest is now [`8.0.202+202`], merged in [PR #43](https://github.com/mipox331-netizen/makeupart-v8/pull/43).
- The Android release workflow selects the next unused [`v8.0.N`] from published release tags rather than consuming GitHub Actions run numbers. The current CI workflow extracts that selector from [`.github/workflows/android-apk.yml`](https://github.com/mipox331-netizen/makeupart-v8/blob/main/.github/workflows/android-apk.yml) and runs [`bash -n`] on it.
- Latest public release remains [MakeupArt V8 v8.0.201](https://github.com/mipox331-netizen/makeupart-v8/releases/tag/v8.0.201), published 23 October. It was built from older source and signed by Android Debug. It is for sideload testing, not Play Store release, and may not update an installation signed with a different certificate.
- Main CI [#705](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40738076624) passed on current merge commit [`460b923`](https://github.com/mipox331-netizen/makeupart-v8/commit/460b923cc62a3b87d4d30a8b6d769826f5879eb0). It includes backend tests/migrations, Flutter analysis/tests, the version-selector shell check and Android debug APK build/artifact upload.
- The verified debug APK from this run has SHA-256 [`5f2b0cb7c04e528f615b76c5200072c84b3659142746361de155572b5914582e`]. It is **debug-signed**, for testing only.
- Current-source release workflow [#215](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40738596006) failed safely because [`ANDROID_KEYSTORE_BASE64`] was missing. It did not build or publish a release APK.

## Required signing configuration

Configure the following GitHub [`production`] environment secrets from the same persistent keystore as the installed release:

- [`ANDROID_KEYSTORE_BASE64`]
- [`ANDROID_STORE_PASSWORD`]
- [`ANDROID_KEY_PASSWORD`]
- [`ANDROID_KEY_ALIAS`]

Never generate a replacement signing key merely to make an update workflow pass. Preserve the signing-secret guard, exact-source CI/security/license gates, backend source/revision and readiness checks, certificate verification, and final current-main check.

## Active API and deployment

The mobile client and release workflows target:

[`https://makeupart-api.onrender.com/api/v1`](https://makeupart-api.onrender.com/api/v1)

Render backend deployment [`dep-dbh2mdq9lscs73806vlg`](https://dashboard.render.com/web/srv-dav25so473hc73d7ee0g) is live on backend commit [`c3b7532`](https://github.com/mipox331-netizen/makeupart-v8/commit/c3b7532f3786dde98e4a2209480adfaf56d77dfa); its configured [`/health/ready`](https://makeupart-api.onrender.com/health/ready) check passed. This does not prove customer-media durability.

## Google Drive media durability

The active media workflow backs up the app's private Google Drive media root, not the old Modal volume. Backup [#53](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40442965971) failed again on 28 October with [`0 files / 0 bytes`]; restore drill [#55](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40732934379) was skipped. OAuth connectivity and [`/health/ready`](https://makeupart-api.onrender.com/health/ready) do not prove customer media is durable.

Before using real customer photographs, upload an authorized test portrait and salon logo through the live app, verify both objects in private Drive, restart Render, retrieve both with matching checksums, then run a non-empty encrypted backup and isolated restore drill.

## Database recovery

Encrypted PostgreSQL backup [#48](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40441672336) and isolated restore drill [#58](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/40441747764) passed on 27 October. The live Render database URL and GitHub backup URL still need independent confirmation that they target the same Supabase database.

## Google Play and iOS

No successful Google Play rollout is verified. Play publication needs the persistent release key, Play Console credentials and a confirmed successful rollout. The iOS compile workflow builds an unsigned artifact only; App Store distribution still requires Apple signing, provisioning and App Store Connect configuration.

## AI scope and cost

Classic MediaPipe/OpenCV processing runs without a paid image-generation key. It is not equivalent to a diffusion-based FaceApp-style reference-image transfer. Generative editing stays disabled until provider credentials, explicit external-processing consent, safety controls and budget are approved. For a $0 operating budget, keep Classic as the default.
