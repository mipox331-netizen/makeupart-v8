# MOOG 343 / MR AI dashboard access

The platform-admin dashboard is already implemented in MakeupArt V8. This entry point provides a private way to open it without exposing the admin route in the normal salon workflow.

## Open the dashboard

1. Open the MakeupArt sign-in screen, or the salon editor.
2. Tap the **MOOG 343** branding.
3. Enter the single admin passphrase. The eye icon shows or hides the text.
4. After server verification, the app refreshes the session and opens the existing platform-admin dashboard.

The dashboard continues to use the existing platform-admin APIs for users, salon subscriptions, verified payment records and account status.

## Server configuration

Set these variables in the API host's secure environment (Render Environment page), not in Flutter or Git:

- `PLATFORM_ADMIN_EMAILS`: exactly one active platform-admin account email for this password-only entry.
- `ADMIN_PORTAL_PASSPHRASE`: a new, unique passphrase with at least 12 UTF-8 characters.

Do not reuse a password that has been pasted into a chat, committed to Git, or used for another account. The repository examples intentionally leave this value empty. When it is empty or shorter than 12 characters, the endpoint returns HTTP 503 and does not issue a session.

## Security controls

- The secret exists only in the backend environment and is represented as a masked secret setting.
- The app contains no embedded admin password and sends the entered passphrase only to the HTTPS API.
- The backend uses a constant-time secret comparison.
- Five failed attempts trigger the existing 15-minute login lockout.
- Successful access is issued as the normal short-lived access / rotating refresh session.
- A passphrase alone cannot promote a normal salon owner. Exactly one active account must also be present in `PLATFORM_ADMIN_EMAILS`.
- The existing admin APIs continue checking `require_platform_admin`; hiding the route is not the authorization boundary.

## Endpoint

`POST /api/v1/auth/admin-portal/login`

Request JSON:

```json
{"passphrase":"<entered passphrase>"}
```

Response: the standard access and refresh token pair. The app stores those tokens in platform secure storage and lets the normal session gate load the admin dashboard.
