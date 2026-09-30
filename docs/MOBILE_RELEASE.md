# Mobile Release Notes

## Android
The repository now contains the generated Android project under `makeup_art_v8/android/`. CI builds a debug APK to verify the generated project and plugin integration.

For a production release, replace the generated debug signing configuration with a real keystore and configure signing credentials outside Git.

## iOS
The repository contains the generated iOS project under `makeup_art_v8/ios/` with camera and photo-library usage descriptions.

iOS release builds require a macOS/Xcode environment and App Store signing credentials. Keep provisioning profiles, certificates and App Store Connect secrets outside the repository.

## API endpoint
Development can override the backend endpoint with:

```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1
```

Production builds should point to the HTTPS API domain from `API_BASE_URL`.
