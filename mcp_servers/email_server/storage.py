import uuid
from datetime import datetime
from typing import Optional

drafts: dict[str, dict] = {}
sent: list[dict] = []
pending_sends: dict[str, dict] = {}


def create_draft(to: str, subject: str, body: str, channel: Optional[str] = None) -> dict:
    draft_id = str(uuid.uuid4())[:8]
    draft = {
        "id": draft_id,
        "to": to,
        "subject": subject,
        "body": body,
        "channel": channel,
        "created_at": datetime.utcnow().isoformat(),
        "status": "draft",
    }
    drafts[draft_id] = draft
    return draft


def get_draft(draft_id: str) -> Optional[dict]:
    return drafts.get(draft_id)


def mark_sent(draft_id: str) -> Optional[dict]:
    draft = drafts.pop(draft_id, None)
    if draft:
        draft["status"] = "sent"
        draft["sent_at"] = datetime.utcnow().isoformat()
        sent.append(draft)
    return draft


def cancel_draft(draft_id: str) -> Optional[dict]:
    draft = drafts.pop(draft_id, None)
    if draft:
        draft["status"] = "cancelled"
    return draft


def list_all_drafts() -> list[dict]:
    return list(drafts.values())
