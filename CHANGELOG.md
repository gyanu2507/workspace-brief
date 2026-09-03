# Changelog

## 0.5.0

Follow-ups, GitHub search, and a `brief` MCP tool.

- A short follow-up ("which PR treats that as missing") glues onto the last question in the session, so memory is actually used for retrieval.
- Remembered facts are extra lookups and ranking terms, not only a footer.
- GitHub issues/PRs go through `/search/issues` (`repo:owner/name is:issue|is:pr`), then fall back to listing the repo if search is empty or fails. 403 still fails fast.
- Answers are grouped bullets (issues / PRs / notes / commits) without a preamble. Equal BM25 scores prefer the newer `updated` stamp.
- MCP exposes a `brief` tool that returns the cited answer, not only the raw search tools.

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
