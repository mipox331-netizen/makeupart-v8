# MakeupArt V8 release readiness

Status checked against the repository and GitHub Actions on 20 October 2026. Passing code checks are kept separate from live deployment evidence.

| Area | Latest evidence | Actual status |
|---|---|---|
| Main-branch fixes | [PR #25](https://github.com/mipox331-netizen/makeupart-v8/pull/25), [PR #24](https://github.com/mipox331-netizen/makeupart-v8/pull/24), and [PR #23](https://github.com/mipox331-netizen/makeupart-v8/pull/23) are merged. Current source includes startup/session recovery, request-ID validation, scoped workflow secrets, Android backup exclusions, private Google Drive storage/restore and extra free Classic looks. | Merged to `main`; this does not prove production is deployed. |
| Flutter checks | [CI run #39406725194](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39406725194) reported Flutter analysis and Flutter tests passed. Its main-push health request raced deployment and returned HTTP 404. | CI has been changed to avoid that parallel health-check race; final backend CI completion still needs confirmation. |
| Production API / Modal deploy | [Modal deploy #39406725317](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39406725317) failed at `modal token info` with `Token not found`. The Modal health URL also returned HTTP 404 when queried by CI. | **Not deployed/verified.** Deployment now validates the actual Modal token per GitHub environment before selecting one. Valid Modal credentials are still required. |
| Android APK | The latest public release is [v8.0.169](https://github.com/mipox331-netizen/makeupart-v8/releases/tag/v8.0.169), published on 15 October 2026, and it targets Render. [Current-main APK run #39406725397](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39406725397) failed because Android signing secrets were incomplete. | No newer verified APK published. All four signing secrets must belong to the same persistent release keystore used for upgrade compatibility. |
| Database backup | [Run #39405500390](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39405500390) failed during secret validation because `BACKUP_ENCRYPTION_PASSPHRASE` was missing. | **No confirmed recent encrypted DB backup.** The passphrase must be at least 24 characters. |
| Media backup / restore | [Media backup run #39405500391](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/39405500391) failed for the same missing passphrase; later restore drills were skipped. | **No confirmed recent media backup/restore drill.** Modal-volume backup is not a verified independent backup of Google Drive. |
| Google Drive media | Private Drive adapter, restore checks, checksums and backfill tool are merged. The Modal workflow now passes OAuth secrets from GitHub's `production` environment to the service. | Implemented in code, **not yet proven active in production**. Test real photo/logo upload and restore after restart before setting `REQUIRE_DURABLE_MEDIA=true`. |
| Database target alignment | Supabase is selected by deployment/backup workflows, but a successful current deploy and restore drill has not proved the runtime and backup URLs point to the same live database. | Confirm the exact runtime/backup target before relying on recovery. |
| Subscription / business-suite PR | [PR #18](https://github.com/mipox331-netizen/makeupart-v8/pull/18) remains unmerged; its `0010_payment_ledger` migration conflicts with `main`'s `0010_nullable_similarity` head. | Do not merge until migration history is sequenced/rebased and Alembic head/upgrade checks pass. |
| AI and budget | Classic makeup uses MediaPipe/OpenCV; paid OpenAI generation remains unprovisioned for the $0 budget. | Do not advertise FaceApp-equivalent generative reference transfer or hairstyle generation as verified features. |
| Play Store / iOS | No successful Play Store rollout or signed iOS distribution is evidenced. | Store availability remains unverified. |

## Exact production gates

1. Configure a valid `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` in a GitHub environment. The deploy workflow now validates tokens per environment rather than trusting non-empty values. Never paste token values into chat or commit them.
2. Set `BACKUP_ENCRYPTION_PASSPHRASE` (unique, at least 24 characters; keep it offline). Re-run DB/media backup and restore drills; verify actual data/file counts and checksums.
3. Set `ANDROID_KEYSTORE_BASE64`, `ANDROID_STORE_PASSWORD`, `ANDROID_KEY_PASSWORD`, and `ANDROID_KEY_ALIAS` together from the persistent signing key. Do not leave a partial set.
4. Set Google Drive OAuth secrets in the `production` environment, deploy, upload a test photo/logo, restart the service and confirm restore. Only then set the GitHub environment variable `REQUIRE_DURABLE_MEDIA=true`.
5. On a real Android device, verify registration, login, consent, processing, watermark, before/after, saving to phone, logout and salon isolation before declaring the new APK production-ready.

Passing code tests does not by itself prove deployment, database recovery, photo durability, store publication or a real-device flow.
