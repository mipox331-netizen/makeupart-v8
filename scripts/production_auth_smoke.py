"""Deployment smoke test for real production registration/login, with synthetic data cleanup.

Only the random synthetic account created by this script is removed. No existing
production user or salon is touched. Never print credentials or API tokens.
"""
from __future__ import annotations

import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

import psycopg2

API_ROOT = "https://mipox331-netizen--makeupart-v8-api-fastapi-app.modal.run/api/v1"
RUN_ID = os.environ.get("GITHUB_RUN_ID", "manual")
EMAIL = f"production-smoke-{RUN_ID}-{uuid.uuid4().hex[:10]}@example.com"
PASSWORD = "Smoke-" + secrets.token_urlsafe(22)
REQUEST_ID = ""
failure: str | None = None


def api_request(path: str, *, method: str = "GET", payload=None, headers=None):
    data = payload
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    if isinstance(payload, dict):
        data = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API_ROOT + path, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = response.read()
            status = response.status
            response_headers = response.headers
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        status = exc.code
        response_headers = exc.headers
    try:
        body = json.loads(raw.decode("utf-8")) if raw else {}
    except (UnicodeDecodeError, json.JSONDecodeError):
        body = {}
    request_id = response_headers.get("X-Request-ID", "")
    if isinstance(body, dict):
        request_id = body.get("request_id") or request_id
    return status, body, request_id


def save_request_id(request_id: str) -> None:
    if not request_id:
        return
    env_file = os.environ.get("GITHUB_ENV")
    if env_file:
        with open(env_file, "a", encoding="utf-8") as handle:
            handle.write(f"PROD_SMOKE_REQUEST_ID={request_id}\n")


try:
    print("Checking production registration endpoint with a synthetic account.")
    status, body, REQUEST_ID = api_request(
        "/auth/register",
        method="POST",
        payload={
            "salon_name": "MakeupArt Production Smoke Test",
            "owner_full_name": "Production Smoke Test",
            "email": EMAIL,
            "password": PASSWORD,
        },
    )
    save_request_id(REQUEST_ID)
    if status != 201:
        detail = body.get("detail") if isinstance(body, dict) else None
        if status >= 500:
            failure = f"Production registration failed with HTTP {status}; request_id={REQUEST_ID or 'unavailable'}."
        else:
            failure = f"Production registration returned HTTP {status}; safe detail={str(detail)[:180]!r}."
    else:
        print("Production registration returned HTTP 201.")
        print("Checking production login.")
        form = urllib.parse.urlencode({"username": EMAIL, "password": PASSWORD}).encode("utf-8")
        status, body, REQUEST_ID = api_request(
            "/auth/login",
            method="POST",
            payload=form,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        save_request_id(REQUEST_ID)
        token = body.get("access_token") if isinstance(body, dict) else None
        if status != 200 or not token:
            failure = f"Production login failed with HTTP {status}; request_id={REQUEST_ID or 'unavailable'}."
        else:
            print("Production login returned HTTP 200.")
            status, body, REQUEST_ID = api_request(
                "/subscriptions/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            save_request_id(REQUEST_ID)
            if status != 200 or not isinstance(body, dict):
                failure = f"Authenticated subscription check failed with HTTP {status}; request_id={REQUEST_ID or 'unavailable'}."
            else:
                print(
                    "Production registration/login/subscription smoke test passed "
                    f"(plan={body.get('plan')!r}, status={body.get('status')!r})."
                )
except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
    failure = f"Production auth smoke test could not complete ({type(exc).__name__}); no credentials were logged."
finally:
    try:
        database_url = os.environ.get("SUPABASE_DB_URL", "").strip()
        if not database_url:
            raise RuntimeError("database cleanup connection unavailable")
        with psycopg2.connect(database_url, connect_timeout=10) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM users WHERE email = %s", (EMAIL.lower(),))
                deleted_users = cursor.rowcount
                cursor.execute("DELETE FROM salons WHERE email = %s", (EMAIL.lower(),))
                deleted_salons = cursor.rowcount
        print(
            "Synthetic smoke data cleanup complete "
            f"(users_removed={deleted_users}, salons_removed={deleted_salons})."
        )
    except Exception as exc:
        failure = failure or (
            "Production auth smoke test could not confirm cleanup of its synthetic account "
            f"({type(exc).__name__}); review the deployment job before retrying."
        )

if failure:
    print(failure, file=sys.stderr)
    raise SystemExit(1)
