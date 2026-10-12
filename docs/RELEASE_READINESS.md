# MakeupArt V8 release readiness

Status verified against GitHub on 12 October 2026. This page deliberately separates a published artifact from store distribution and separates code configuration from real production evidence.

| Area | Current evidence | Status / remaining gate |
|---|---|---|
| Android APK | Public GitHub Release [v8.0.139](https://github.com/mipox331-netizen/makeupart-v8/releases/tag/v8.0.139); APK workflow #139 passed and verifies the signed APK. | **Available.** [Direct APK download](https://github.com/mipox331-netizen/makeupart-v8/releases/download/v8.0.139/MakeupArt-V8.apk). The in-app checker prompts users to download a newer release; Android still requires confirmation to install it. |
| Backend production | Modal deploy workflow #104 passed; API readiness is checked by deployment. | **Deployed.** This does not replace ongoing monitoring or backup/restore tests. |
| Google Play | The workflow previously skipped the upload when `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` was empty, which could make the workflow look successful without publishing. It now fails explicitly if the Play service-account secret is missing or invalid. | **Not verified as published.** Run the Google Play workflow on the `internal` track after a Play Console app exists and a service account with release access is configured. Review/rollout status must be confirmed in Play Console. |
| iOS / App Store | iOS project files exist and an unsigned macOS compile workflow is configured. | **Build check only.** An unsigned `.app` artifact is not a user-installable IPA and is not an App Store submission. Distribution still needs the app's registered Bundle ID, Apple Developer membership, signing certificate/profile, and App Store Connect access. |
| Production monitoring | A GitHub Actions check is configured every 15 minutes for `/health/live` and `/health/ready`. | **Basic monitor configured.** A failing check becomes a failed Actions run; notification delivery depends on GitHub account/repository notification settings. No SMS/pager incident service is configured. |
| Database backups | Daily encrypted PostgreSQL dump workflow is configured; the archive is GPG AES-256 encrypted and uploaded as a GitHub Actions artifact for 14 days. | **Not operational until secrets are configured and a successful artifact is verified.** Requires a production DB URL secret plus `BACKUP_ENCRYPTION_PASSPHRASE` (at least 24 characters, kept offline). Restore has not yet been tested against a clean staging database. |
| Image/media backups | Customer media is stored separately in the Modal media volume. A database dump does not include those files. | **Not backed up by the database workflow.** An independent private object-storage destination and credentials are still needed for recoverable media backups. |
| Generative makeup | Current processing uses MediaPipe + OpenCV image enhancement; it does not generate a new makeup look. | **Not implemented.** Requires a commercially licensed model/provider, consent/retention design, identity-preservation checks, cost controls and real output validation. |
| InsightFace | Production code loads the pretrained `buffalo_l` model. InsightFace's published terms distinguish MIT source code from pretrained models supplied for non-commercial research by default. | **Commercial release blocker until licensed or replaced.** See [AI capabilities and licensing](AI_CAPABILITIES_AND_LICENSES.md). |
| Repository license | No root-level `LICENSE` file is currently present. | **Owner decision required** before communicating reuse rights or accepting outside contributions. |

## Required secrets (names only; do not put values in chat or source)

- Google Play: `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` plus the four Android signing secrets already used by the release workflow.
- Encrypted database backup: a production database URL (`SUPABASE_DB_URL`, `SUPABASE_DB_URL_SECRET` or `DATABASE_URL`) and `BACKUP_ENCRYPTION_PASSPHRASE`.
- Store certificates, passwords and provider keys belong in GitHub Secrets / the production environment only.

A CI green result confirms the checks that actually ran; it does not mean Google Play accepted the app, Apple signed an IPA, an external backup can be restored, a generative model exists, or model rights have been granted.
