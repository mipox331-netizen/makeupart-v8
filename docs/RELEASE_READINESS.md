# MakeupArt V8 release readiness

Status verified against GitHub on 12 October 2026. This page separates published artifacts from store distribution and code configuration from production evidence.

| Area | Current evidence | Status / remaining gate |
|---|---|---|
| Android APK | Public GitHub Release [v8.0.139](https://github.com/mipox331-netizen/makeupart-v8/releases/tag/v8.0.139); APK workflow #139 passed and verifies the signed APK. | **Available.** [Direct APK download](https://github.com/mipox331-netizen/makeupart-v8/releases/download/v8.0.139/MakeupArt-V8.apk). Android still asks the user to confirm an update installation. Mobile changes after v8.0.139 must complete the release workflow before appearing in the public APK. |
| Backend production | [Modal deploy run 38257623154](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38257623154) completed successfully on source commit `83ac871220e99071072d77aee841c5566a61f0a6`; runtime, media-volume, API readiness, registration/login/free-subscription smoke tests passed. | **Deployed.** Continue monitoring and disaster-recovery testing. |
| CI | [Run 38257623191](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38257623191) passed on the same source commit. | **Green for the checks run.** This does not certify external services, commercial license approval or customer data recovery. |
| Third-party license inventory | The [inventory workflow](../.github/workflows/third-party-license-inventory.yml) generates Python package license/notice data and Flutter/Dart dependency license details. | **Automated inventory added; manual review remains.** Review unknown/ambiguous entries and native Android/iOS, operating-system, container-base and bundled asset/model licenses before claiming complete commercial clearance. |
| Repository source license | Root [LICENSE](../LICENSE) declares original project materials proprietary and all rights reserved. | **Repository reuse notice added.** Third-party terms still apply; this is not the end-user agreement for the app or hosted service. |
| Database backup/restore | Encrypted backup artifact run [38251453670](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38251453670). Isolated restore drill [38257496915](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38257496915) passed checksum, decryption, PostgreSQL restore, schema and migration checks. | **Archive/schema restore verified, real row-data recovery not yet verified.** The selected backup contains no `users`, `salons` or `subscriptions` rows. Repeat with a populated backup before claiming recovery of real application data. |
| Image/media backups | Customer media is stored separately in the Modal media volume and is excluded from the PostgreSQL dump. | **Not independently backed up.** A private off-host destination and a tested media restore are still required. |
| Production monitoring | GitHub Actions checks `/health/live` and `/health/ready` every 15 minutes. | **Basic monitor configured.** Independent SMS/pager alerting is not configured. |
| Google Play | Release workflow validates its service-account secret and builds a signed AAB. | **Store publication not verified.** Needs a Play Console app, correct service-account access and confirmation of publication status in Play Console. |
| iOS / App Store | iOS project files and an unsigned build check exist. | **Build check only.** No signed IPA, TestFlight build or App Store submission is verified. |
| Generative makeup | Current processing uses MediaPipe + OpenCV image enhancement. | **Not implemented.** Do not market the current feature as generative makeup. |

## Required GitHub/production secrets

- Google Play: `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` plus the Android signing secrets used by the release workflow.
- Encrypted database backup: a valid production database URL secret and `BACKUP_ENCRYPTION_PASSPHRASE` (minimum 24 characters, with a recovery copy stored offline).
- Provider keys, certificates and passwords belong only in GitHub Secrets / the production environment. Never paste secret values into chat or source code.

A successful CI/deploy or empty-database restore is not proof of full commercial license approval, Google Play publication, iOS distribution, media backup or real application-row recovery. See [Third-party license audit](THIRD_PARTY_LICENSE_AUDIT.md).
