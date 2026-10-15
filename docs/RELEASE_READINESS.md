# MakeupArt V8 release readiness

Status verified against GitHub and the connected Render workspace on 15 October 2026. This checklist distinguishes a published APK from a fully proven production system.

| Area | Current evidence | Status / remaining gate |
|---|---|---|
| Android APK | [Public release v8.0.163](https://github.com/mipox331-netizen/makeupart-v8/releases/tag/v8.0.163); [APK workflow #163 passed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38575779546). | APK is published for manual installation. This is not evidence of Google Play publication or complete end-to-end customer testing. |
| CI | [Latest CI run #515 succeeded](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38575788229). | Backend checks and Flutter analysis/tests passed in CI. Live health checks do not replace sign-up, photo-processing, download and account-isolation testing on a device. |
| Production API | Render service `makeupart-api` is present on the free plan. Monitor run [#138 passed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38694438681); run [#135 timed out](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38685000956), then later monitor checks passed. | Service responds, but free-tier cold starts/outages have occurred. Transient network/gateway failures now retry once; persistent errors still block release. |
| Alternative Modal deployment | The repo keeps a separate Modal deployment path. Deployment run [#131 failed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38545767333) during the previously reported workspace spend-limit issue. | The current APK uses Render, not the Modal endpoint. Do not make Modal the production target without a verified available workspace. |
| Encrypted database backup | [Backup run #22 passed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38673627849). | Encrypted archive creation and archive-readability checks passed. |
| Database restore drill | [Restore drill #29 passed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38673699725). | An isolated restore completed and its schema/migration checks passed. The running Render service's actual database target has not been verified against the Supabase URL selected by the backup workflow; do not yet claim confirmed recovery of the exact live production database. |
| Media backup | [Media backup run #23 failed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38674643154) at the Modal volume download step; [media restore drill #22 was skipped](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38674669332). | **Blocked.** The workflow now retries downloads and emits a safe failure category, but a new successful archive and paired restore have not yet been verified. |
| Photo durability | The API stores files under `MEDIA_ROOT`; the backup job targets Modal's separate volume, not files solely stored on Render's local filesystem. | **Production blocker for real customer photos.** Configure durable object/file storage for the running API and back up that same source, then restore a populated test archive. |
| Database lifecycle | The connected workspace exposes a free Render PostgreSQL resource with an expiry date of 31 October 2026; the backup workflow reads a Supabase URL secret. | Confirm the runtime `DATABASE_URL` and backup URL reference the same live database, and confirm a migration/row-level restore before relying on disaster recovery. Do not delete either resource until the connection target is confirmed. |
| Automatic APK updates | The app checks GitHub Releases and opens the download for a newer version. | Android still requires the user to approve APK installation; silent updates are not provided. |
| Google Play / iOS | No successful Play Console rollout is evidenced; iOS project requires distribution signing. | Store publication and review are not complete. |
| AI and licensing | MediaPipe/OpenCV classic processing runs without a paid API key; optional OpenAI image edits incur provider costs and require explicit external-processing consent. | For the current $0 budget, keep classic mode enabled and paid generation disabled. Complete manual review of third-party licensing before commercial launch. |

## Required production gates

1. Get a successful encrypted media backup and paired restore drill from the actual file store used by the live API.
2. Verify that the API and database backup workflow target the same production database, then restore a populated backup into an isolated database.
3. Validate a full real-device flow: registration, login, gallery/camera selection, consent, photo processing, watermark, before/after, save to phone, logout and account isolation.
4. Complete third-party license review and, if needed, configure Play Console signing and release permissions before claiming store availability.
