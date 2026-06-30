# Architecture Decisions

## 1. Conversation history stored server-side, not passed from frontend

**Problem:** On the second chat message, the frontend was sending back `res.messages` (the full Anthropic SDK message history including `tool_use` and `tool_result` blocks). These objects are not cleanly JSON-serializable, causing a malformed request body that surfaced as a CORS/fetch error.

**Decision:** Store conversation history server-side in `agent/loop.py` keyed by `conversation_id`. The frontend only sends the `conversation_id` on follow-up messages — the backend looks up the history from `_conversation_history[conversation_id]`.

**Why:** The frontend has no business owning message history. It's an internal Claude API concern. Keeping it server-side also means history survives page refreshes as long as the backend is running.

**Files changed:**
- `backend/agent/loop.py` — added `_conversation_history` dict, load from it on each turn, persist after each response
- `frontend/src/components/ChatPanel.tsx` — removed `history` state, no longer sends messages back to backend

---

## 2. CORS — explicit method list instead of wildcard

**Problem:** `allow_methods=["*"]` with `allow_credentials=True` caused PATCH requests to be blocked by browser preflight. The wildcard does not expand correctly when credentials are enabled (Starlette/FastAPI known behavior).

**Decision:** List methods explicitly: `["GET", "POST", "PATCH", "DELETE", "OPTIONS"]`.

**Files changed:**
- `backend/main.py`

---

## 3. Single WebSocket connection via React Context

**Problem:** Each component calling `useWebSocket()` independently created its own WebSocket connection. React StrictMode double-mounts components in dev, causing a race where the first connection was closed before the second opened ("WebSocket closed before established").

**Decision:** One WS connection opened at `App` root via `useWebSocketProvider()`, exposed via `WsContext`. Child components subscribe via `useWsEvent()` — no new connections.

**Files changed:**
- `frontend/src/lib/ws.ts`
- `frontend/src/main.tsx` — removed StrictMode
- `frontend/src/App.tsx` — wraps app in `WsContext.Provider`
- `frontend/src/components/RulesPanel.tsx`, `LogsPanel.tsx` — use `useWsEvent`

---

## 4. Optimistic UI updates for rule toggle and delete

**Problem:** Toggle and delete relied solely on the WebSocket `rule_update` / `rule_delete` event to update local state. If WS was slow or disconnected, the UI appeared frozen after clicking.

**Decision:** Update local React state immediately (optimistic update), fire the API call in the background, and revert on failure.

**Files changed:**
- `frontend/src/components/RulesPanel.tsx`
