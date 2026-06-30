import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()


from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from api.chat import router as chat_router
from api.rules import router as rules_router
from api.approvals import router as approvals_router
from api.ws import broadcast, ws_endpoint
from agent.loop import set_log_broadcast
from agent.mcp_client import mcp_manager
import policy.store as policy_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Wire broadcast functions so store and loop can push WS events
    policy_store.set_broadcast_fn(broadcast)
    set_log_broadcast(broadcast)

    # Start MCP server connections and discover tools
    await mcp_manager.start()

    # Periodically expire stale pending approvals
    async def _expiry_loop():
        while True:
            await asyncio.sleep(60)
            policy_store.expire_pending_approvals()

    task = asyncio.create_task(_expiry_loop())

    yield

    task.cancel()
    await mcp_manager.shutdown()


app = FastAPI(title="Guard Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=0,
)

app.include_router(chat_router)
app.include_router(rules_router)
app.include_router(approvals_router)


@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    await ws_endpoint(websocket)


@app.get("/health")
def health():
    tools = mcp_manager.get_tools_for_claude()
    return {"status": "ok", "tools_discovered": len(tools), "tools": [t["name"] for t in tools]}
