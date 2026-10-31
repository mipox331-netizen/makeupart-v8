# Android release signing

The public release workflow intentionally refuses to sign with an ephemeral debug key.

## Important compatibility check

A newly generated upload key is safe only when this application has not previously been published with a different upload certificate, or when Google Play App Signing is enabled and you are deliberately replacing the upload key. If the app has already been published, recover the original keystore instead. Do not create a new identity just to make CI green.

## Generate a new key in a Codespace

From the repository root, run this only after confirming the compatibility check above:

\`\`\`bash
MAKEUPART_ALLOW_NEW_UPLOAD_KEY=YES bash scripts/generate_android_release_signing.sh
\`\`\`

The script uses the installed JDK and OpenSSL, generates a 3072-bit RSA JKS key, validates its alias, and saves everything outside the repository under:

\`\`\`text
$HOME/.config/makeupart-v8/android-release/
\`\`\`

It creates a local file named \`github-production-secrets.txt\` containing the four values required by the release workflow. The file is created with owner-only permissions; do not commit it, send it in chat, or upload it as an Actions artifact.

## Configure GitHub

Open **GitHub → Settings → Environments → production → Environment secrets** and set:

- \`ANDROID_KEYSTORE_BASE64\`
- \`ANDROID_KEY_ALIAS\`
- \`ANDROID_STORE_PASSWORD\`
- \`ANDROID_KEY_PASSWORD\`

The current workflow logs confirm that the last three secrets are already present; \`ANDROID_KEYSTORE_BASE64\` is the missing value on the latest release attempt. Recheck the secrets before changing them.

Keep an encrypted offline copy of the JKS and its passwords. Loss of the key can prevent future APK updates unless Google Play App Signing allows an upload-key reset.

## Release verification

After all four secrets are present, the Android release workflow still requires:
- a successful CI, security audit and license inventory for the exact main commit;
- a healthy production API and durable media backend;
- successful Flutter analysis/tests and APK signing verification.

A debug APK is for internal testing, not a production release.
