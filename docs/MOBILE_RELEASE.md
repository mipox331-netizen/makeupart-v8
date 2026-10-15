# Mobile Release Notes

Status verified against GitHub and the connected Render workspace on 15 October 2026.

## Android APK

The latest published Android artifact is [MakeupArt V8 v8.0.163](https://github.com/mipox331-netizen/makeupart-v8/releases/tag/v8.0.163), built by [successful APK workflow run #163](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38575779546).

[Download MakeupArt-V8.apk](https://github.com/mipox331-netizen/makeupart-v8/releases/download/v8.0.163/MakeupArt-V8.apk).

The APK is configured to use the current Render endpoint:

```text
https://makeupart-api.onrender.com/api/v1
```

The app checks GitHub Releases and prompts when a newer version is published. The user must still open the download and approve Android's installation prompt; updates do not install silently.

## Production API and deployment paths

The Render service `makeupart-api` exists in the connected workspace, uses the `main` branch and is on the free plan. Recent readiness requests returned HTTP 200, but a production monitor run also timed out during a cold start. The monitor and Android release workflows now retry transient network/gateway failures once; a persistent error still blocks release.

The repository also retains a separate Modal deployment workflow and a Modal media-volume backup workflow. These are **not the endpoint used by the current APK**. A Modal workspace spend-limit issue previously blocked its deployment. Do not switch the APK back to Modal until that workspace and deployment path are intentionally restored and verified.

## Media durability — production blocker

The API stores uploaded and processed files below its configured `MEDIA_ROOT`. The automated media-backup workflow currently tries to download the separate Modal volume `makeupart-v8-media`; it does not back up files kept only on the Render service's local filesystem. The latest media-backup run failed before an archive was created, and its paired restore drill was skipped.

Before relying on this service for real customer photographs, the running API's storage path must be tied to a durable, backed-up location (for example, a verified object-storage bucket), and a populated backup must pass a restore drill. Do not treat an empty-volume drill or the current Modal backup workflow as evidence that Render-stored customer images can be recovered.

## Database and backups

The latest automated encrypted PostgreSQL backup and isolated restore drill both passed. The backup workflow uses a Supabase database URL secret; the connected Render workspace also contains a free PostgreSQL resource expiring on 31 October 2026. The runtime Render service's actual `DATABASE_URL` target has not been exposed by the available metadata, so verify that the runtime and backup workflow point to the same production database before declaring customer-row disaster recovery complete.

## Google Play Store

No successful Google Play publication is verified. The Play release workflow requires the service-account and signing secrets. A successful workflow alone would not prove public availability; confirm the release track and rollout in Play Console.

## iOS / App Store

The repository contains the iOS Flutter/Xcode project, but an unsigned build is not a distributable IPA. App Store distribution still needs valid Apple Developer signing, provisioning and App Store Connect configuration.

## AI engines

Classic MediaPipe/OpenCV processing runs without an external image-generation API key. It provides face-landmark-aware local cosmetics and image enhancement, not a diffusion-based FaceApp-equivalent makeover. The optional OpenAI image-edit path is disabled without server-side credentials and can incur per-use costs. For the current $0 operating constraint, keep classic mode as the default and do not enable paid generation without deliberate budget approval.
