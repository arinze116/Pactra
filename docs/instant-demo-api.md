# Instant demo API

The instant demo uses Pactra's existing opaque cookie session and synchronizer
CSRF conventions. Production responses use the global structured error
envelope and include request IDs. Session tokens are never returned in JSON.

Production deployment `28634c13082a61b5c53e75528eacf2263ea1fd5e`
serves these contracts at <https://pactra-nine.vercel.app>. Production browser
acceptance verified Secure, HttpOnly, SameSite=Lax demo cookies, refresh
restoration, reset, exit, and preservation of a separate normal session.

## `POST /api/demo/sessions`

Creates one isolated temporary principal and seeded workspace.

- Authentication: none.
- Browser protection: same-origin `Origin` or `Referer` required.
- Rate limits: per client and shared global bucket.
- Success: `201 Created` and separate demo session/CSRF cookies.
- Request body: none.

Response:

```json
{
  "user": {
    "id": "uuid",
    "email": "demo-random@demo.pactra.invalid",
    "display_name": "Northstar Studio",
    "is_demo": true,
    "demo_expires_at": "2026-11-10T15:00:00Z"
  },
  "message": "Northstar Studio demo workspace is ready."
}
```

Errors:

- `403 ORIGIN_REQUIRED` or `ORIGIN_MISMATCH`;
- `429 RATE_LIMITED`;
- `503 DEMO_CAPACITY_REACHED`.

## `GET /api/demo/session`

Returns the active demo lifecycle state.

```json
{
  "active": true,
  "expires_at": "2026-11-10T15:00:00Z",
  "seed_version": 1
}
```

Errors:

- `401 DEMO_SESSION_EXPIRED` for invalid, revoked, or expired demo cookies;
- `404 DEMO_NOT_FOUND` when the active principal is a normal account.

## `POST /api/demo/reset`

Restores only the authenticated demo principal's workspace.

Required headers:

```text
Origin: <configured same origin>
X-CSRF-Token: <token returned by session/auth responses>
```

Request:

```json
{
  "idempotency_key": "demo-reset-unique-value"
}
```

Response:

```json
{
  "reset": true,
  "replayed": false,
  "wallet": {
    "currency": "USD",
    "available_cents": 82500,
    "reserved_cents": 14000,
    "posted_cents": 96500,
    "sandbox_generation": 2
  },
  "transaction_ids": {
    "completed": "uuid",
    "pending_approval": "uuid",
    "rejected": "uuid",
    "blocked": "uuid"
  }
}
```

Errors:

- `403 DEMO_REQUIRED` or `CSRF_INVALID`;
- `409 TRANSACTION_IN_PROGRESS`;
- `410 DEMO_SESSION_EXPIRED`;
- `429 RATE_LIMITED` or `DEMO_RESOURCE_LIMIT`.

An ambiguous client response should be retried with the same idempotency key.

## `POST /api/demo/exit`

Revokes the active demo and returns `204 No Content`. It clears only
`pactra_demo_session` and `pactra_demo_csrf`. A separate normal session is not
revoked.

Errors:

- `403 DEMO_REQUIRED` or `CSRF_INVALID`;
- `401 DEMO_SESSION_EXPIRED` if the demo already expired.

## Session discovery

`GET /api/auth/session` now returns:

```json
{
  "user": null,
  "demo_expired": false
}
```

If both cookies exist, a valid demo is the active browser context. If the demo
has expired, the endpoint clears its cookies and then attempts to restore the
normal session. This endpoint is the frontend's sole session authority and
prevents guest-action flicker.

## Demo restrictions on existing APIs

- `/api/transactions`: only `internal_sandbox` is accepted.
- provider retry, approval, and reconciliation paths reject provider-backed
  demo rows at the service boundary.
- `/api/integrations/paypal/status`: returns an unconfigured, credential-free
  response for demo principals.
- `/api/auth/change-password`, `/api/wallet/topups`, and `/api/wallet/reset`:
  return `403 DEMO_RESTRICTED`.
- settings routes are omitted from demo navigation and protected by the
  frontend normal-account route guard.
