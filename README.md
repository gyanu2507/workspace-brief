# workspace-brief

Ask **any** GitHub repository what changed — issues, PRs, commits, notes — and get an answer that cites the records it retrieved.

Works against a live `owner/name` repo (GitHub API) or a bundled offline **sample** workspace for demos and tests. Architecture: planner, tool loop, BM25 over hits, session memory, JSON execution traces. Static document Q&A is a separate project (`corpus-brief`).

```
pip install -e ".[dev]"

# any public (or token-accessible) repo
brief --source github --repo owner/name "what landed recently?"
brief --json --source github --repo owner/name "what are the open risks?"

# offline sample workspace (no API key)
brief --source fixture "what changed this quarter and what are the main risks?"
```

`GITHUB_TOKEN` is optional until GitHub rate-limits you. Live issue/PR lookup uses GitHub's search API (`repo:owner/name is:issue`), then falls back to listing recent items if search returns nothing. Transient 429/5xx are retried. Tokens are stripped from traces and error strings.

Follow-ups in the same `--session` (or `session` on `POST /brief`) reuse the last question. `which PR treats that as missing` after a checkout question still finds the promo PR. `remember that …` also feeds retrieval, not only a footer.

## HTTP API

```
pip install -e ".[api]"
brief-api
```

```
curl -s localhost:8000/health
curl -s localhost:8000/ready
curl -s localhost:8000/brief -H 'content-type: application/json' \
  -d '{"question":"what are the main risks?"}'
```

`POST /brief` takes `question`, optional `source` (`fixture` | `github`), `repo`, and `session`. Defaults come from `BRIEF_SOURCE` / `BRIEF_REPO`. Interactive docs: `/docs`.

## Hosting it

A local `brief` command is fine on a laptop. A URL other people can hit is not, unless you lock it down.

On any host that runs Docker:

```
export BRIEF_ENV=production
export BRIEF_API_KEY='a long random string'   # 16+ characters
export BRIEF_ALLOWED_REPOS='owner/name'
export GITHUB_TOKEN='ghp_…'                   # fine-grained, those repos only
export BRIEF_SOURCE=github
export BRIEF_REPO=owner/name
export BRIEF_RATE_LIMIT=60
export BRIEF_TRUST_PROXY=1                    # behind a reverse proxy
docker compose up --build -d
```

`BRIEF_ENV=production` refuses to start without `BRIEF_API_KEY`, and refuses GitHub mode without an allowlist.

```
curl -s "$HOST/brief" \
  -H "content-type: application/json" \
  -H "X-API-Key: $BRIEF_API_KEY" \
  -d '{"question":"what landed recently?"}'
```

`GET /health` stays open so the host can probe it. `GET /ready` checks that the memory store is writable. `/brief` returns 401 without the key. A repo outside `BRIEF_ALLOWED_REPOS` returns 403. The JSON `trace` field is a filename, not a filesystem path.

MCP for a desktop client (stdio). `brief` is the one-shot tool. The search tools are still there if the client wants to walk the workspace itself:

```json
{
  "command": "python",
  "args": ["-m", "workspace_brief.mcp_server"],
  "env": {
    "BRIEF_SOURCE": "github",
    "BRIEF_REPO": "owner/name",
    "GITHUB_TOKEN": "ghp_…"
  }
}
```

## Docker

```
docker compose up --build
```

The API listens on `:8000`. Memory and traces live in a volume. The process runs as uid 10001, not root, and the image health-checks `/health`.

## Memory

`.brief-memory.sqlite` (or `BRIEF_MEMORY_PATH`)

- short-term: last few turns in the session
- long-term: only if you say `remember that …`. Repeating the same fact is a no-op.
- WAL mode so concurrent `/brief` calls do not lock each other out

## Grounding

Retrieved bodies are treated as data. If a note tries `ignore previous instructions`, the body is dropped and the title still cites. Empty evidence refuses instead of inventing.

Commits are only listed when the question is about what changed — otherwise they drowned every answer.

Set `GROQ_API_KEY` or `OPENAI_API_KEY` to rewrite the extractive bullets. The rewrite is thrown away if it drops a citation. Tests never need a key.

## Config

| Env | Default | |
| --- | --- | --- |
| `BRIEF_ENV` | `development` | `production` requires an API key |
| `GITHUB_TOKEN` / `GH_TOKEN` | unset | GitHub auth |
| `BRIEF_SOURCE` | `fixture` | `fixture` or `github` |
| `BRIEF_REPO` | unset | `owner/name` |
| `BRIEF_API_KEY` | unset | if set, `/brief` requires it |
| `BRIEF_ALLOWED_REPOS` | unset | comma-separated allowlist |
| `BRIEF_CORS_ORIGINS` | unset | comma-separated, or `*` |
| `BRIEF_RATE_LIMIT` | `60` | `/brief` per IP per minute; `0` disables |
| `BRIEF_TRUST_PROXY` | unset | honor `X-Forwarded-For` |
| `BRIEF_GITHUB_TIMEOUT` | `25` | seconds |
| `BRIEF_GITHUB_RETRIES` | `3` | 429 / 5xx |
| `BRIEF_MEMORY_PATH` | `.brief-memory.sqlite` | |
| `BRIEF_TRACE_DIR` | `traces` | |
| `BRIEF_LOG_LEVEL` | `INFO` | |
| `BRIEF_API_HOST` / `BRIEF_API_PORT` | `0.0.0.0` / `8000` | |
| `GROQ_API_KEY` / `OPENAI_API_KEY` | unset | optional rewrite |

## Eval

```
pytest
```

Gold questions run against the bundled sample workspace. A hit means the cited issue/note actually showed up in evidence, not just in the prose.

Python 3.11+. MIT. See [SECURITY.md](SECURITY.md) before putting this on a network.
