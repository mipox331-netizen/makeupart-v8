# MakeupArt V8 release readiness

Status verified against GitHub Actions and the connected Render workspace on 15 October 2026. This checklist distinguishes a published APK from a fully proven production system.

| Area | Current evidence | Status / remaining gate |
|---|---|---|
| Android APK | [Public release v8.0.164](https://github.com/mipox331-netizen/makeupart-v8/releases/tag/v8.0.164); [APK workflow #164 passed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38699306152). SHA-256: `b048bd80ba5611c1ee9a78eb716d331736ed3495268ab7e2f2d93f8a6389cbba`. | Published for manual installation. The workflow reports no Android release-signing secrets and uses Flutter's debug signing key; this is not a Play Store-ready APK. |
| Flutter and live API checks | APK workflow passed Flutter analysis/tests, `/health/live`, `/health/ready`, APK build and verification. [CI #515 passed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38575788229) before the latest ops-only edits. | Latest operational commits have fresh CI runs queued/running. A green APK workflow still does not replace full real-device customer-flow tests. |
| Production API | Render `makeupart-api` is present on the free plan. [Monitor #140 passed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38699306251); [monitor #135 timed out](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38685000956), and subsequent checks passed. | Transient cold starts have happened. Health/release checks retry transient network/gateway failures once; persistent errors still block release. |
| Alternative Modal deployment | [Modal deploy #131 failed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38545767333) during the previously reported workspace spend-limit issue. | Current APK uses Render, not Modal. Do not switch it back without restoring and verifying that path. |
| Encrypted database backup | [Backup #22 passed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38673627849). | Archive creation and readability checks passed. |
| Database restore drill | [Restore #29 passed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38673699725). | Isolated restore completed. The live Render `DATABASE_URL` target has not been verified against the Supabase URL used by the backup workflow, so recovery of the exact live production database remains unproven. |
| Modal media backup workflow | [Backup #25 failed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38699417171); [restore drill #24 was skipped](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38699465088). | Still separate from the Render API; it does not back up Render-local files. |
| Google Drive media adapter | Private Drive OAuth adapter and endpoint integration added on branch; uses `drive.file` scope and keeps objects non-public. | **Implemented in code, not yet configured in production.** Add the three Google OAuth values to Render, test a real upload plus cold-start restore, then set `REQUIRE_DURABLE_MEDIA=true`. |
| Photo durability | The Render service metadata shows no persistent disk; local `MEDIA_ROOT` is not a durable source. | **Not yet proven in production.** Existing local-only photos need a one-time backfill if their files are still accessible. |
| Database lifecycle | Render workspace also exposes a free PostgreSQL resource expiring 31 October 2026; backup workflow reads a Supabase database URL secret. | Confirm runtime `DATABASE_URL` and backup URL refer to the same live DB. Do not remove either database resource before the runtime connection is verified. |
| Automatic APK updates | App checks GitHub Releases and opens the download for newer versions. | Android still requires user approval to install; silent install is not available. |
| Google Play / iOS | No successful Play Console rollout or signed iOS IPA is evidenced. | Configure release signing/Play Console permissions and Apple signing before claiming store availability. |
| AI and licensing | MediaPipe/OpenCV classic processing runs without a paid API key; optional OpenAI image edits incur provider costs and require explicit external-processing consent. | With the current $0 budget, keep classic mode enabled and paid generation disabled. Complete manual third-party license review before commercial launch. |

## Required production gates

1. Configure the private Google Drive OAuth variables on the live API, perform a real photo upload, restart/redeploy the service, and verify that the before/after images and salon logo restore from the same private Drive folder. Backfill any still-accessible older local images before they disappear.
2. Verify the live API database target matches the backup URL; restore a populated test backup into an isolated database and compare row counts/checksums.
3. Validate on a real Android device: registration, login, camera/gallery selection, consent, processing, watermark, before/after, save to phone, logout and salon isolation.
4. Configure Android release signing before a Play Console release; complete third-party license review and check the rollout state before claiming store availability.
