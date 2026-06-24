import json
from typing import Any

from fastapi import WebSocket

_connections: set[WebSocket] = set()


async def broadcast(message: dict[str, Any]):
    dead = set()
    for ws in _connections:
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            dead.add(ws)
    _connections.difference_update(dead)


async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    _connections.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        _connections.discard(websocket)
