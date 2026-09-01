# workspace-brief

Ask a question about a workspace that actually changes (issues, PRs, commits, notes) and get an answer that cites what it retrieved.

This is not another PDF chatbot. I already have [advanced-rag](https://github.com/gyanu2507/advanced-rag) for that — chunking, rerank, static files. This repo is the other half: a planner, a tool loop, BM25 over the hits, memory that does not swallow every sentence, and a json trace of the whole path.

```
pip install -e ".[dev]"
brief "what changed this quarter and what are the main risks?"
```

That hits the checked-in **Northstar** fixture, a fake billing app with a promo 500, a Stripe webhook stampede, and a p95 goal that is blocked on the crash. No API key.

A real GitHub repo:

```
brief --source github --repo gyanu2507/advanced-rag "what landed recently?"
```

`GITHUB_TOKEN` is optional; you only need it if you get rate-limited. Transient 429/5xx are retried.

stderr prints `trace: traces/<time>.json`. That file has the rewrite, sub-questions, tool calls, evidence snippets, memory, and citations — so you can see why it said what it said. Tokens in traces and error strings are stripped before they hit disk.

## HTTP API

```
pip install -e ".[api]"
brief-api
# or: uvicorn workspace_brief.api:app --host 0.0.0.0 --port 8000
```

```
curl -s localhost:8000/health
curl -s localhost:8000/brief -H 'content-type: application/json' \
  -d '{"question":"what are the main risks?"}'
```

`POST /brief` takes `question`, optional `source` (`fixture` | `github`), `repo`, and `session`. Live GitHub without `repo` is a 400.

## Docker

```
docker compose up --build
```

The API listens on `:8000`. Memory and traces live in a volume. Copy `.env.example` and export `GITHUB_TOKEN` if you want `--source github` without getting throttled.

## Memory

`.brief-memory.sqlite` (or `BRIEF_MEMORY_PATH`)

- short-term: last few turns in the session
- long-term: only if you say `remember that …` (priority project, ignore X, …). Repeating the same fact is a no-op.

## Grounding

Retrieved bodies are treated as data. If a note tries `ignore previous instructions`, the body is dropped and the title still cites. Empty evidence refuses instead of inventing.

Commits are only listed when the question is about what changed — otherwise they drowned every answer.

Set `GROQ_API_KEY` or `OPENAI_API_KEY` to rewrite the extractive bullets. The rewrite is thrown away if it drops a citation. Tests never need a key.

## MCP

Same tools over stdio. Speaks MCP `Content-Length` framing; a single JSON line still works for smoke tests.

```
python -m workspace_brief.mcp_server
```

`BRIEF_SOURCE=github BRIEF_REPO=owner/name` if you want live GitHub instead of the fixture.

## Config

| Env | Default | |
| --- | --- | --- |
| `GITHUB_TOKEN` / `GH_TOKEN` | unset | GitHub auth |
| `BRIEF_SOURCE` | `fixture` | `fixture` or `github` |
| `BRIEF_REPO` | unset | `owner/name` |
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

## Layout

```
src/workspace_brief/
  cli.py         argparse entry
  api.py         FastAPI /health and /brief
  config.py      env
  planner.py     keyword splits; no model required
  retrieve.py    BM25 over fetched records
  agent.py       plan → tools (cap 8) → cite
  llm.py         optional rewrite; keeps citations or bails
  fixture.py     Northstar
  github.py      issues / pulls / commits, retries
  redact.py      tokens out of traces and errors
  memory.py      sqlite
  trace.py       json dump
  mcp_server.py  stdio MCP
fixtures/northstar/
evals/gold.json
```

Python 3.11+. MIT.
