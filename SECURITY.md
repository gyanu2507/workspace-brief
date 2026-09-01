# Security

Report a vulnerability privately to viratmayank2507@gmail.com. Do not open a public issue for secrets or injection bypasses.

A process that other people can reach is not the same as a local CLI.

- Set `BRIEF_API_KEY` before publishing a URL. `/brief` then requires `X-API-Key` or `Authorization: Bearer`.
- Set `BRIEF_ALLOWED_REPOS=owner/name` so the GitHub token cannot be used as an open proxy.
- Prefer a fine-grained GitHub token with read access to those repos only.
- `GROQ_API_KEY` / `OPENAI_API_KEY` are optional. If set, they live only on the server.
- Traces on disk are for the operator. The API returns a filename, not a path, and strips tokens from the json.
