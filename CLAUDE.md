# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

A guarded AI agent platform. Claude (the LLM) talks to MCP servers to use tools. A policy engine sits between the LLM's tool-call decisions and the MCP server's execution — every tool call is intercepted and evaluated against live guardrail rules before it runs. The dashboard lets admins create/toggle rules; changes propagate to the running agent via WebSocket without restart.

## Running the Project

### Backend

```bash
cd backend
cp .env.example .env        # fill in ANTHROPIC_API_KEY and EXA_API_KEY
pip install -r requirements.txt
ANTHROPIC_API_KEY=... EXA_API_KEY=... uvicorn main:app --port 8000 --reload
```

Verify MCP tool discovery is working:
```bash
curl http://localhost:8000/health
# Should show 7 tools: 5 from email-server + 2 from exa-search
```

### Custom MCP Server (standalone test)

```bash
cd mcp_servers/email_server
python server.py                              # runs as stdio — waits for MCP protocol input
npx @modelcontextprotocol/inspector python server.py   # interactive inspector UI
```

### Frontend (not yet built)

```bash
cd frontend
npm install && npm run dev    # http://localhost:5173
```

## Architecture

### The Enforcement Seam

```
User → Claude (proposes tool call) → policy/engine.py → MCP server (executes)
```

Claude's tool-call is a **proposal**. The policy engine is the enforcer — it runs outside the LLM's trust boundary and cannot be overridden by natural language. It only sees `(tool_name, input_args)` and returns `ALLOW | BLOCK | NEEDS_APPROVAL`.

### Policy Engine Priority Order (`policy/engine.py`)

Rules are evaluated in this fixed order — first match wins:
1. `block_tool` — hard deny
2. `input_validation` — deny if input field fails regex
3. `token_budget` — deny if conversation token count exceeded
4. `require_approval` — pause for human sign-off

### Live Rule Propagation

`policy/store.py` holds rules in memory. When a rule is upserted/deleted via the REST API, `store.py` calls the broadcast function (injected at startup in `main.py` lifespan) which pushes a WebSocket event to all connected dashboard clients. The agent loop reads from the same in-memory store — so the change is immediate, no restart needed.

### MCP Server Config (`backend/mcp_config.json`)

Adding a new MCP server here and calling `mcp_manager.reload_servers()` is all that's needed — tool discovery is fully dynamic, nothing hardcoded. Env var values in `"env"` blocks are resolved from OS environment by name (e.g. `"EXA_API_KEY": "EXA_API_KEY"` reads `os.environ["EXA_API_KEY"]`).

### Agent Loop (`agent/loop.py`)

The loop holds conversation history as a list of messages mutated in place. When a tool call returns `NEEDS_APPROVAL`, the loop returns early with `pending_approval: true` — the frontend must poll or listen for the approval WebSocket event and resume the conversation after the human acts.

### WebSocket Events (`api/ws.py`)

All clients share `_connections: set[WebSocket]`. Events pushed by the backend:
- `rule_update` / `rule_delete` — rule changed in dashboard
- `log_event` — agent took an action (tool called, verdict, result)
- `approval_needed` / `approval_resolved` — human approval workflow

## Key Constraints

- **No hardcoded tool lists** — tools come exclusively from MCP server `list_tools()` responses
- **Policy engine is a separate module** — `policy/` has no imports from `agent/` or `api/`
- **Dashboard changes must work without restart** — enforced via the shared in-memory store + WebSocket broadcast pattern
