# Security

Report a vulnerability privately to viratmayank2507@gmail.com. Do not open a public issue for secrets or injection bypasses.

A process that other people can reach is not the same as a local CLI.

## Production

Set `BRIEF_ENV=production` before publishing a URL. The process then refuses to start unless:

- `BRIEF_API_KEY` is set and at least 16 characters. `/brief` requires `X-API-Key` or `Authorization: Bearer`.
- `BRIEF_ALLOWED_REPOS=owner/name` when `BRIEF_SOURCE=github`, so the GitHub token cannot be used as an open proxy.

Also:

- Prefer a fine-grained GitHub token with read access to those repos only.
- Sit behind TLS. Set `BRIEF_TRUST_PROXY=1` only when a trusted reverse proxy sets `X-Forwarded-For`.
- `GROQ_API_KEY` / `OPENAI_API_KEY` are optional. If set, they live only on the server.
- Traces on disk are for the operator. The API returns a filename, not a path, and strips tokens from the JSON.
- Upstream GitHub errors are returned as a generic 502 in production. Details stay in the server log.
