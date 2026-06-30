import asyncio
import json
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

import storage
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

app = Server("email-messaging-server")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="draft_email",
            description="Create a draft email. Does not send it yet.",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body content"},
                },
                "required": ["to", "subject", "body"],
            },
        ),
        types.Tool(
            name="send_email",
            description="Send a previously created email draft by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "draft_id": {"type": "string", "description": "Draft ID to send"},
                },
                "required": ["draft_id"],
            },
        ),
        types.Tool(
            name="list_drafts",
            description="List all email drafts currently saved.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="send_slack_message",
            description="Send a message to a Slack channel (simulated, no real Slack message sent).",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "Slack channel name (without #)"},
                    "message": {"type": "string", "description": "Message content"},
                },
                "required": ["channel", "message"],
            },
        ),
        types.Tool(
            name="cancel_message",
            description="Cancel a pending draft or scheduled message by its ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "draft_id": {"type": "string", "description": "Draft ID to cancel"},
                },
                "required": ["draft_id"],
            },
        ),
        types.Tool(
            name="smart_digest",
            description="Returns all drafts ranked by urgency score based on subject/body keywords. Highlights time-sensitive emails that need attention first.",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "draft_email":
        draft = storage.create_draft(
            to=arguments["to"],
            subject=arguments["subject"],
            body=arguments["body"],
        )
        text = f"Draft created with ID {draft['id']}. To: {draft['to']}, Subject: {draft['subject']}"

    elif name == "send_email":
        draft_id = arguments["draft_id"]
        draft = storage.get_draft(draft_id)
        if not draft:
            text = f"Error: No draft found with ID {draft_id}"
        else:
            sent = storage.mark_sent(draft_id)
            text = f"Email sent to {sent['to']} with subject '{sent['subject']}' (simulated)"

    elif name == "list_drafts":
        all_drafts = storage.list_all_drafts()
        if not all_drafts:
            text = "No drafts found."
        else:
            lines = [f"- [{d['id']}] To: {d['to']} | Subject: {d['subject']} | Status: {d['status']}" for d in all_drafts]
            text = "\n".join(lines)

    elif name == "send_slack_message":
        channel = arguments["channel"]
        message = arguments["message"]
        draft = storage.create_draft(to=channel, subject="Slack message", body=message, channel=channel)
        storage.mark_sent(draft["id"])
        text = f"Slack message sent to #{channel}: '{message}' (simulated)"

    elif name == "cancel_message":
        draft_id = arguments["draft_id"]
        cancelled = storage.cancel_draft(draft_id)
        if not cancelled:
            text = f"Error: No draft found with ID {draft_id}"
        else:
            text = f"Draft {draft_id} cancelled successfully."

    elif name == "smart_digest":
        all_drafts = storage.list_all_drafts()
        if not all_drafts:
            text = "No drafts to digest."
        else:
            URGENT_KEYWORDS = ["urgent", "asap", "immediately", "deadline", "critical", "important", "action required", "overdue", "follow up", "reminder"]
            def score(draft):
                text_blob = (draft.get("subject", "") + " " + draft.get("body", "")).lower()
                return sum(2 if kw in text_blob else 0 for kw in URGENT_KEYWORDS[:3]) + \
                       sum(1 if kw in text_blob else 0 for kw in URGENT_KEYWORDS[3:])

            ranked = sorted(all_drafts, key=score, reverse=True)
            lines = ["📋 SMART DIGEST — Drafts ranked by urgency:\n"]
            for i, d in enumerate(ranked, 1):
                s = score(d)
                priority = "🔴 HIGH" if s >= 4 else "🟡 MEDIUM" if s >= 2 else "🟢 LOW"
                lines.append(f"{i}. [{priority}] [{d['id']}] To: {d['to']}")
                lines.append(f"   Subject: {d['subject']}")
                lines.append(f"   Status: {d['status']} | Urgency score: {s}")
                lines.append("")
            text = "\n".join(lines)

    else:
        text = f"Error: Unknown tool '{name}'"

    return [types.TextContent(type="text", text=text)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
