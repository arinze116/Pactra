# Oracle and Vercel deployment

Pactra is publicly deployed at <https://pactra-nine.vercel.app>. The production
Vercel rewrite uses `https://node1.taild90918.ts.net` as its trusted HTTPS
upstream because Oracle's public security list blocks direct TCP 80/443 access.

## Oracle runtime

1. Keep PostgreSQL on its default loopback listeners and use the dedicated
   `pactra` operating-system/database role pair with peer authentication.
2. Install a release at `/opt/pactra/current`, including a private virtualenv.
3. Generate `/etc/pactra/secret-key` with cryptographically secure random data,
   owned by `pactra:pactra` and mode `0600`.
4. Install `pactra.env.oracle-baseline` as `/etc/pactra/pactra.env`, mode `0600`.
   Replace the localhost origins only after the real HTTPS origins are known.
5. Back up PostgreSQL, then install the two systemd units. The API unit runs
   `alembic upgrade head` before Uvicorn starts on `127.0.0.1:8010`.
6. Start the API first, verify `/api/ready`, then start the worker. The worker
   holds a PostgreSQL advisory lock so only one process reconciles payouts.

Do not add the Nginx site until its placeholders have been replaced. Install it
as a new Pactra site; never edit the existing Clavis virtual host.

The current fallback does not modify Nginx. Tailscale Funnel terminates public
HTTPS and proxies to `http://127.0.0.1:8010`. Verify it with:

```bash
sudo tailscale funnel status
curl --fail https://node1.taild90918.ts.net/api/ready
```

Disable only Pactra's Funnel route with
`sudo tailscale funnel --https=443 off`. Do not reset or reconfigure the base
Tailscale connection.

## Vercel frontend

The linked Vercel project is `pactra`. Use `frontend` as the upload root,
`npm ci` as the install command, `npm run build` as the build command, Node 22,
and `dist` as the output directory. `frontend/vercel.json` contains the active
rewrite. Leave `VITE_API_URL` absent so browser requests remain same-origin.

After deployment, verify registration, CSRF-protected mutations, cookies,
receipts, persistence, and cross-user isolation through the public Vercel URL.
