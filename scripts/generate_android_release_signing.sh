#!/usr/bin/env bash
set -euo pipefail
umask 077

if [[ "${MAKEUPART_ALLOW_NEW_UPLOAD_KEY:-}" != "YES" ]]; then
  cat >&2 <<'EOF'
A NEW Android upload key changes the APK signing identity.
Do not generate one if this app is already published unless Google Play App Signing
is enabled and you are deliberately replacing the upload key.

After confirming that a new upload key is appropriate, run:
  MAKEUPART_ALLOW_NEW_UPLOAD_KEY=YES bash scripts/generate_android_release_signing.sh
EOF
  exit 2
fi

for command in keytool openssl base64; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Missing required command: $command (install a JDK and OpenSSL in this Codespace)." >&2
    exit 1
  }
done

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SIGNING_DIR="${HOME}/.config/makeupart-v8/android-release"
KEYSTORE="${SIGNING_DIR}/upload-keystore.jks"
SECRETS_FILE="${SIGNING_DIR}/github-production-secrets.txt"
mkdir -p "$SIGNING_DIR"
chmod 700 "$SIGNING_DIR"

if [[ -e "$KEYSTORE" || -e "$SECRETS_FILE" ]]; then
  echo "Signing material already exists under ${SIGNING_DIR}; refusing to overwrite it." >&2
  exit 1
fi

ALIAS="makeupart-v8-release"
PASSWORD="$(openssl rand -hex 32)"
TEMP_KEYSTORE="${KEYSTORE}.tmp"

cleanup() {
  unset PASSWORD
  rm -f "$TEMP_KEYSTORE"
}
trap cleanup EXIT

keytool -genkeypair \
  -noprompt \
  -keystore "$TEMP_KEYSTORE" \
  -storetype JKS \
  -alias "$ALIAS" \
  -keyalg RSA \
  -keysize 3072 \
  -validity 10000 \
  -dname "CN=MakeupArt V8, OU=Android Release, O=MakeupArt" \
  -storepass "$PASSWORD" \
  -keypass "$PASSWORD" >/dev/null 2>&1

keytool -list \
  -keystore "$TEMP_KEYSTORE" \
  -storetype JKS \
  -storepass "$PASSWORD" \
  -alias "$ALIAS" >/dev/null

mv "$TEMP_KEYSTORE" "$KEYSTORE"
chmod 600 "$KEYSTORE"

BASE64_VALUE="$(base64 < "$KEYSTORE" | tr -d '\r\n')"
[[ -n "$BASE64_VALUE" ]] || {
  echo "Could not encode the Android keystore." >&2
  exit 1
}

{
  printf 'ANDROID_KEYSTORE_BASE64=%s\n' "$BASE64_VALUE"
  printf 'ANDROID_KEY_ALIAS=%s\n' "$ALIAS"
  printf 'ANDROID_STORE_PASSWORD=%s\n' "$PASSWORD"
  printf 'ANDROID_KEY_PASSWORD=%s\n' "$PASSWORD"
} > "$SECRETS_FILE"
chmod 600 "$SECRETS_FILE"
unset BASE64_VALUE PASSWORD

echo "Android release keystore generated and validated."
echo "Keystore: $KEYSTORE"
echo "GitHub production secrets file: $SECRETS_FILE"
echo "Copy each value from that local file into GitHub > Settings > Environments > production > Environment secrets."
echo "Do not commit or upload the keystore or secrets file; keep a second encrypted offline backup."
