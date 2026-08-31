# workspace-brief

Ask a question about a workspace that actually changes (issues, PRs, commits, notes) and get an answer that cites what it retrieved.

This is not another PDF chatbot. I already have [advanced-rag](https://github.com/gyanu2507/advanced-rag) for that — chunking, rerank, static files. This repo is the other half: a planner, a tool loop, memory that does not swallow every sentence, and a json trace of the whole path.

```
pip install -e ".[dev]"
brief "what changed this quarter and what are the main risks?"
```

That hits the checked-in **Northstar** fixture, a fake billing app with a promo 500, a Stripe webhook stampede, and a p95 goal that is blocked on the crash. No API key.

A real GitHub repo:

```
brief --source github --repo gyanu2507/advanced-rag "what landed recently?"
```

`GITHUB_TOKEN` is optional; you only need it if you get rate-limited.

stderr prints `trace: traces/<time>.json`. That file has the rewrite, sub-questions, tool calls, evidence snippets, memory, and citations — so you can see why it said what it said.

## Memory

`.brief-memory.sqlite`

- short-term: last few turns in the session
- long-term: only if you say `remember that …` (priority project, ignore X, …). Repeating the same fact is a no-op.

## Eval

```
pytest
```

8 gold questions on Northstar. A hit means the cited issue/note actually showed up in evidence, not just in the prose. **8/8** on this workspace.

## Layout

```
src/workspace_brief/
  cli.py        argparse entry
  planner.py    keyword splits; no model required
  agent.py      plan → tools (cap 8) → cite
  fixture.py    Northstar + token-overlap ranking
  github.py     issues / pulls / commits
  memory.py     sqlite
  trace.py      json dump
fixtures/northstar/
evals/gold.json
```

Python 3.11+. The synthesizer is still extractive (bullets + citations). If I wire Groq/OpenAI later it should only rewrite those bullets, not invent ids.
