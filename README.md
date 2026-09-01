# workspace-brief

Ask a question about a workspace that actually changes (issues, PRs, commits, notes) and get an answer that cites what it retrieved.

This is not another PDF chatbot. I already have [advanced-rag](https://github.com/gyanu2507/advanced-rag) for that — chunking, rerank, static files. This repo is the other half: a planner, a tool loop, BM25 over the hits, memory that does not swallow every sentence, and a json trace of the whole path.

```
pip install -e ".[dev]"
brief "what changed this quarter and what are the main risks?"
```

That hits the checked-in **Northstar** fixture. No API key. A real GitHub repo:

```
brief --source github --repo owner/name "what landed recently?"
```

`GITHUB_TOKEN` is optional until GitHub rate-limits you. Transient 429/5xx are retried. Tokens are stripped from traces and error strings.

## Share it with other people

A local `brief` command is fine on your laptop. A URL other people can hit is not, unless you lock it down.

On any host that runs Docker:

```
export BRIEF_API_KEY='a long random string'
export BRIEF_ALLOWED_REPOS='owner/name'
export GITHUB_TOKEN='ghp_…'          # fine-grained, read those repos only
export BRIEF_SOURCE=github
export BRIEF_REPO=owner/name
export BRIEF_RATE_LIMIT=60
export BRIEF_TRUST_PROXY=1           # if you sit behind a reverse proxy
docker compose up --build -d
```

Then they call:

```
curl -s "$HOST/brief" \
  -H "content-type: application/json" \
  -H "X-API-Key: $BRIEF_API_KEY" \
  -d '{"question":"what landed recently?"}'
```

`GET /health` stays open so the host can probe it. `/brief` returns 401 without the key. A repo outside `BRIEF_ALLOWED_REPOS` returns 403. The json `trace` field is a filename, not a filesystem path.

MCP for a desktop client (stdio, same tools):

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

## HTTP API (local)

```
pip install -e ".[api]"
brief-api
```

```
curl -s localhost:8000/health
curl -s localhost:8000/brief -H 'content-type: application/json' \
  -d '{"question":"what are the main risks?"}'
```

`POST /brief` takes `question`, optional `source` (`fixture` | `github`), `repo`, and `session`. If you omit `source` / `repo`, the process defaults (`BRIEF_SOURCE`, `BRIEF_REPO`) are used. Interactive docs: `/docs`.

## Docker

```
docker compose up --build
```

The API listens on `:8000`. Memory and traces live in a volume. The process runs as uid 10001, not root.

## Memory

`.brief-memory.sqlite` (or `BRIEF_MEMORY_PATH`)

- short-term: last few turns in the session
- long-term: only if you say `remember that …`. Repeating the same fact is a no-op.

## Grounding

Retrieved bodies are treated as data. If a note tries `ignore previous instructions`, the body is dropped and the title still cites. Empty evidence refuses instead of inventing.

Commits are only listed when the question is about what changed — otherwise they drowned every answer.

Set `GROQ_API_KEY` or `OPENAI_API_KEY` to rewrite the extractive bullets. The rewrite is thrown away if it drops a citation. Tests never need a key.

## Config

| Env | Default | |
| --- | --- | --- |
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

15 gold questions on Northstar. A hit means the cited issue/note actually showed up in evidence, not just in the prose.

Python 3.11+. MIT. See [SECURITY.md](SECURITY.md) if you are putting this on a network.
