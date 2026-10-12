# Mobile Release Notes

## Android APK

The current public release is [v8.0.145](https://github.com/mipox331-netizen/makeupart-v8/releases/tag/v8.0.145), with direct download at [MakeupArt-V8.apk](https://github.com/mipox331-netizen/makeupart-v8/releases/download/v8.0.145/MakeupArt-V8.apk).

The release workflow runs dependency resolution, Flutter analysis/tests, a release build, APK signature verification and publication as a GitHub Release. The current APK includes an update checker that reads the latest public GitHub Release and prompts the user when a newer version exists. It opens the browser/download destination; Android still requires the user to confirm installing the downloaded APK. Updates do not download or install silently.

## Google Play Store

The Google Play release workflow builds a signed Android App Bundle and can target `internal`, `closed`, or `production`. It now fails explicitly if `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` is missing or invalid instead of silently treating an omitted upload as a completed release.

Before running it, configure the service-account JSON secret with Play Console release permissions and the Android signing secrets in GitHub. Start with the **internal** track. A successful GitHub workflow is not enough: confirm that the release appears in Play Console, complete any testing/review requirements, and verify the track's rollout state before announcing Play Store availability.

No successful Play Store publication is currently verified.

## iOS / App Store

The repository has the iOS Flutter/Xcode project and a Podfile. The iOS workflow compiles an unsigned release build to verify the toolchain; its artifact is not a distributable IPA.

App Store distribution still needs a registered and available bundle identifier, an Apple Developer Program membership, signing certificate/provisioning profile and App Store Connect configuration. Keep private keys, certificates, provisioning profiles and API credentials out of Git.

## Production API endpoint

Android/iOS production builds use:

```text
https://mipox331-netizen--makeupart-v8-api-fastapi-app.modal.run/api/v1
```

## Operational release checks

The restricted InsightFace pretrained model/runtime has been removed and the MediaPipe/OpenCV replacement is deployed. Before commercial launch, review the generated third-party dependency license inventories, test database row recovery using a populated backup, and set up a separate off-host backup/restore process for media stored in the Modal volume. See [Release Readiness](RELEASE_READINESS.md), [AI capabilities and licensing](AI_CAPABILITIES_AND_LICENSES.md), and [Third-party license audit](THIRD_PARTY_LICENSE_AUDIT.md).
