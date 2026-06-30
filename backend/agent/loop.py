"""
Agent loop — drives the Claude tool-use loop with policy enforcement.
Every tool call is intercepted by the policy engine before execution.
"""
import time
import uuid
from typing import Any

import anthropic

from agent.mcp_client import mcp_manager
from policy import engine as policy_engine
import policy.store as policy_store

client = anthropic.AsyncAnthropic()
MODEL = "claude-sonnet-4-6"

# conversation_id -> list of log entries
_conversation_logs: dict[str, list[dict]] = {}
# conversation_id -> total input+output tokens used
_token_usage: dict[str, int] = {}
# conversation_id -> message history for Claude
_conversation_history: dict[str, list] = {}
# conversation_id -> pending tool_use_id awaiting approval
_pending_tool_ids: dict[str, str] = {}

_ws_log_broadcast = None  # injected by ws.py


def set_log_broadcast(fn):
    global _ws_log_broadcast
    _ws_log_broadcast = fn


def _log(conversation_id: str, entry: dict):
    _conversation_logs.setdefault(conversation_id, []).append(entry)
    if _ws_log_broadcast:
        import asyncio
        asyncio.create_task(_ws_log_broadcast({"event": "log_event", "data": {**entry, "conversation_id": conversation_id}}))


def get_logs(conversation_id: str | None = None) -> list[dict]:
    if conversation_id:
        return _conversation_logs.get(conversation_id, [])
    all_logs = []
    for cid, logs in _conversation_logs.items():
        for entry in logs:
            all_logs.append({**entry, "conversation_id": cid})
    return all_logs


async def run_agent(user_message: str, conversation_id: str | None = None, history: list | None = None) -> dict:
    if not conversation_id:
        conversation_id = str(uuid.uuid4())[:8]

    # Use server-side history; ignore any history sent from frontend
    messages = list(_conversation_history.get(conversation_id, []))
    messages.append({"role": "user", "content": user_message})
    _log(conversation_id, {"type": "user", "content": user_message, "ts": time.time()})

    tools = mcp_manager.get_tools_for_claude()
    token_usage = _token_usage.get(conversation_id, 0)

    while True:
        response = await client.messages.create(
            model=MODEL,
            max_tokens=4096,
            tools=tools,
            messages=messages,
        )

        # Track token usage
        usage = response.usage.input_tokens + response.usage.output_tokens
        token_usage += usage
        _token_usage[conversation_id] = token_usage

        # Collect text and tool_use blocks
        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(block)

        if response.stop_reason == "end_turn" or not tool_calls:
            final_text = " ".join(text_parts)
            _log(conversation_id, {"type": "assistant", "content": final_text, "ts": time.time()})
            _conversation_history[conversation_id] = messages
            return {
                "conversation_id": conversation_id,
                "response": final_text,
                "messages": [],
            }

        # Append assistant message with all blocks
        messages.append({"role": "assistant", "content": response.content})

        # Process each tool call through policy engine
        tool_results = []
        for tool_block in tool_calls:
            tool_name = tool_block.name
            tool_input = tool_block.input

            verdict_result = policy_engine.evaluate(
                tool_name=tool_name,
                tool_input=tool_input,
                conversation_id=conversation_id,
                token_usage=token_usage,
            )

            _log(conversation_id, {
                "type": "tool_call",
                "tool": tool_name,
                "input": tool_input,
                "verdict": verdict_result.verdict,
                "verdict_reason": verdict_result.reason,
                "ts": time.time(),
            })

            if verdict_result.verdict == "BLOCK":
                content = f"[BLOCKED by policy] {verdict_result.reason}"
                # Return immediately for token_budget blocks — don't let Claude keep responding
                if verdict_result.rule_id and "token" in (verdict_result.reason or "").lower():
                    _conversation_history[conversation_id] = messages
                    return {
                        "conversation_id": conversation_id,
                        "response": f"Blocked: {verdict_result.reason}. This conversation has reached its token limit.",
                        "messages": [],
                    }
            elif verdict_result.verdict == "NEEDS_APPROVAL":
                import re as _re
                _m = _re.search(r"approval ID: ([a-f0-9\-]+)", verdict_result.reason or "")
                approval_id = _m.group(1) if _m else None
                # Append placeholder tool_result so Claude message sequence stays valid
                messages.append({
                    "role": "user",
                    "content": [{"type": "tool_result", "tool_use_id": tool_block.id, "content": "[AWAITING HUMAN APPROVAL]"}],
                })
                _conversation_history[conversation_id] = messages
                _pending_tool_ids[conversation_id] = tool_block.id
                return {
                    "conversation_id": conversation_id,
                    "response": f"Tool '{tool_name}' requires human approval before executing.",
                    "pending_approval": True,
                    "approval_id": approval_id,
                    "messages": [],
                }
            else:
                # ALLOW — execute via MCP
                result = await mcp_manager.call_tool(tool_name, tool_input)
                content = result
                _log(conversation_id, {"type": "tool_result", "tool": tool_name, "result": result, "ts": time.time()})

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block.id,
                "content": content,
            })

        messages.append({"role": "user", "content": tool_results})
