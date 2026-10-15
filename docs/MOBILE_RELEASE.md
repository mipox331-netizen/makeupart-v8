# Mobile Release Notes

Status verified against GitHub and the connected Render workspace on 15 October 2026.

## Android APK

The latest published Android artifact is [MakeupArt V8 v8.0.164](https://github.com/mipox331-netizen/makeupart-v8/releases/tag/v8.0.164).

[Download MakeupArt-V8.apk](https://github.com/mipox331-netizen/makeupart-v8/releases/download/v8.0.164/MakeupArt-V8.apk).

The APK SHA-256 is `b048bd80ba5611c1ee9a78eb716d331736ed3495268ab7e2f2d93f8a6389cbba`. The [Android workflow #164 succeeded](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38699306152), including Flutter analysis/tests, API liveness/readiness, APK build, APK verification and publication.

**Signing limit:** the workflow explicitly said Android release-signing secrets are not configured and used Flutter's debug signing key. This APK is intended for manual installation, not Google Play publication.

The APK is configured to use the Render endpoint:

```text
https://makeupart-api.onrender.com/api/v1
```

The app checks GitHub Releases and prompts when a newer version is published. The user must still open the download and approve Android's installation prompt; updates do not install silently.

## Production API and deployment paths

The connected Render workspace shows the `makeupart-api` web service on the free plan. The most recent production monitor [#140 passed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38699306251), while earlier monitor [#135 timed out](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38685000956) during a startup/cold-start check. Health checks in the monitor and Android release workflow now retry transient network/gateway failures once; persistent errors still block release.

The repository retains a separate Modal deployment and media-volume backup workflow. These are **not** the endpoint/storage used by the current APK. The Modal deployment has previously failed on a workspace spend-limit issue. Do not switch the APK back to Modal until that workspace and deployment path are intentionally restored and verified.

## Media durability — production blocker

The API stores uploaded and processed files below its configured `MEDIA_ROOT`. The media-backup workflow tries to download the separate Modal volume `makeupart-v8-media`; it does not back up files stored only on the Render service's local filesystem. The latest [media-backup run #25 failed](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38699417171), and its paired [restore drill #24 was skipped](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38699465088).

Before relying on the app for real customer photographs, connect the live API to a durable object store and back up that same source, then verify a populated backup restore.

## Database and backups

The latest encrypted PostgreSQL backup [#22](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38673627849) and isolated restore drill [#29](https://github.com/mipox331-netizen/makeupart-v8/actions/runs/38673699725) passed. The backup workflow uses a Supabase database URL secret; the connected Render workspace also contains a free PostgreSQL resource expiring on 31 October 2026. The runtime Render service's actual `DATABASE_URL` target has not been exposed by the available service metadata, so verify that the runtime and backup workflow point to the same production database before declaring customer-row recovery complete.

## Google Play Store

No successful Google Play publication is verified. The current APK uses the debug signing key. Play publication needs a proper release keystore/signing secrets and a configured Play Console service account. Confirm the release track and rollout in Play Console before announcing store availability.

## iOS / App Store

The repository contains the iOS Flutter/Xcode project, but an unsigned build is not a distributable IPA. App Store distribution still needs valid Apple Developer signing, provisioning and App Store Connect configuration.

## AI engines

Classic MediaPipe/OpenCV processing runs without an external image-generation API key. It provides face-landmark-aware local cosmetics and image enhancement, not a diffusion-based FaceApp-equivalent makeover. The optional OpenAI image-edit path is disabled without server-side credentials and can incur per-use costs. For the current $0 operating constraint, keep classic mode as the default and do not enable paid generation without deliberate budget approval.
