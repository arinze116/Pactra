# Oracle and Vercel deployment

These assets intentionally stop short of public activation until a controlled
Pactra API hostname resolves to this VPS and has a valid TLS certificate.

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

## Vercel frontend

Use `frontend` as the project root, `npm ci` as the install command,
`npm run build` as the build command, and `dist` as the output directory. Copy
`deploy/vercel.json.example` to `frontend/vercel.json`, replace the verified API
hostname, and leave `VITE_API_URL` blank so browser requests remain same-origin.

After deployment, verify registration, CSRF-protected mutations, cookies,
receipts, persistence, and cross-user isolation through the public Vercel URL.
