# Changelog

## 0.4.0

Production hardening for a hosted API.

- `BRIEF_ENV=production` requires `BRIEF_API_KEY` (16+ chars) and, for GitHub, `BRIEF_ALLOWED_REPOS`.
- `GET /ready` checks the SQLite memory store. `/health` stays a cheap liveness probe.
- Request IDs, `X-Content-Type-Options`, and `Retry-After` on 429.
- SQLite WAL and busy timeout for concurrent `/brief` calls.
- Trace filenames include a unique suffix so two requests in the same second do not collide.
- GitHub 502s no longer leak upstream text in production.
- CLI `--json` and `--version`. MCP `serverInfo.version` follows the package.
- Docker image health-check and `--proxy-headers`.
