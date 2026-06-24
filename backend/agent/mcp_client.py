"""
MCP Client — manages connections to multiple MCP servers and provides
live tool discovery. Tool lists are never hardcoded; they are fetched
from each server at runtime and merged into a single registry.
"""
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


CONFIG_PATH = Path(__file__).parent.parent / "mcp_config.json"


class MCPClientManager:
    def __init__(self):
        # tool_name -> {schema, server_name}
        self._tool_registry: dict[str, dict] = {}
        # server_name -> ClientSession
        self._sessions: dict[str, ClientSession] = {}
        self._contexts: list = []

    async def start(self):
        config = self._load_config()
        for server_cfg in config.get("servers", []):
            await self._connect_server(server_cfg)

    def _load_config(self) -> dict:
        with open(CONFIG_PATH) as f:
            return json.load(f)

    async def _connect_server(self, cfg: dict):
        name = cfg["name"]
        transport = cfg.get("transport", "stdio")

        if transport == "stdio":
            cmd = cfg["command"]
            args = cfg.get("args", [])
            env = {**os.environ, **cfg.get("env", {})}
            params = StdioServerParameters(command=cmd, args=args, env=env)
            ctx = stdio_client(params)
            read, write = await ctx.__aenter__()
            session = ClientSession(read, write)
            await session.__aenter__()
            await session.initialize()
            self._sessions[name] = session
            self._contexts.append((ctx, session))
        # SSE transport can be added here for remote servers

        await self._discover_tools(name)

    async def _discover_tools(self, server_name: str):
        session = self._sessions.get(server_name)
        if not session:
            return
        result = await session.list_tools()
        for tool in result.tools:
            self._tool_registry[tool.name] = {
                "server": server_name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema or {},
            }

    async def reload_servers(self):
        """Re-read config and discover tools from any newly added servers."""
        config = self._load_config()
        for server_cfg in config.get("servers", []):
            name = server_cfg["name"]
            if name not in self._sessions:
                await self._connect_server(server_cfg)
        # Re-discover tools from all existing servers
        for name in list(self._sessions.keys()):
            await self._discover_tools(name)

    def get_tools_for_claude(self) -> list[dict]:
        """Return tools in the format Claude's API expects."""
        tools = []
        for tool_name, info in self._tool_registry.items():
            tools.append({
                "name": tool_name,
                "description": info["description"],
                "input_schema": info["input_schema"],
            })
        return tools

    async def call_tool(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        info = self._tool_registry.get(tool_name)
        if not info:
            return f"Error: Tool '{tool_name}' not found in registry"
        server_name = info["server"]
        session = self._sessions.get(server_name)
        if not session:
            return f"Error: Server '{server_name}' not connected"
        try:
            result = await session.call_tool(tool_name, tool_input)
            parts = [c.text for c in result.content if hasattr(c, "text")]
            return "\n".join(parts) if parts else "(no output)"
        except Exception as e:
            return f"Error calling tool '{tool_name}': {e}"

    async def shutdown(self):
        for ctx, session in self._contexts:
            try:
                await session.__aexit__(None, None, None)
                await ctx.__aexit__(None, None, None)
            except Exception:
                pass


# Singleton used across the app
mcp_manager = MCPClientManager()
