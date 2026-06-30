# guard_agent

A policy-enforced AI agent platform. Claude (the LLM) talks to MCP servers to use tools. A policy engine sits between the LLM's tool-call decisions and the MCP server's execution — every tool call is intercepted and evaluated against live guardrail rules before it runs. The dashboard lets admins create/toggle rules; changes propagate to the running agent via WebSocket without restart.

## Architecture

```
User → Claude (proposes tool call) → Policy Engine → MCP Server (executes)
```

The policy engine is the enforcer — it runs outside the LLM's trust boundary and cannot be overridden by natural language.

## Running the App

Run each in a separate terminal tab.

### Terminal 1 — Backend

```bash
cd backend
source venv/bin/activate
uvicorn main:app --port 8000 --reload --reload-dir . --reload-exclude venv
```

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

### Terminal 3 — MCP Email Server (optional)

Only needed for standalone testing with the MCP inspector. The backend launches it automatically via stdio — you do not need to run this separately for normal use.

```bash
cd mcp_servers/email_server
npx @modelcontextprotocol/inspector python server.py
```

This starts the inspector proxy and the email server together. Open `http://localhost:6274` to browse and call the 5 email tools interactively.

> Do not run `python server.py` directly — it is a stdio process that waits silently for MCP protocol input and will appear to hang.

## URLs

| Service | URL |
|---|---|
| Frontend dashboard | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |

## Verify Backend is Up

```bash
# Should show 7 tools: 5 from email-server + 2 from exa-search
curl http://localhost:8000/health

# List active guardrail rules
curl http://localhost:8000/rules
```

## Guardrail Rule Types

| Type | What it does |
|---|---|
| `block_tool` | Hard deny — tool never runs |
| `require_approval` | Pauses and waits for human approval |
| `input_validation` | Blocks if an input field fails a regex check |
| `token_budget` | Blocks if conversation token count exceeds limit |

Rules are evaluated in the order above — first match wins.

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in:

```
ANTHROPIC_API_KEY=...
EXA_API_KEY=...
```
