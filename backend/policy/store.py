import asyncio
import time
from typing import Any, Callable, Optional

from policy.models import GuardrailRule, PendingApproval

_rules: dict[str, GuardrailRule] = {}
_pending_approvals: dict[str, PendingApproval] = {}
_ws_broadcast: Optional[Callable] = None  # injected by ws.py at startup


def set_broadcast_fn(fn: Callable):
    global _ws_broadcast
    _ws_broadcast = fn


def _broadcast(event: str, data: Any):
    if _ws_broadcast:
        asyncio.create_task(_ws_broadcast({"event": event, "data": data}))


# --- Rules ---

def list_rules() -> list[GuardrailRule]:
    return list(_rules.values())


def get_rule(rule_id: str) -> Optional[GuardrailRule]:
    return _rules.get(rule_id)


def upsert_rule(rule: GuardrailRule) -> GuardrailRule:
    _rules[rule.id] = rule
    _broadcast("rule_update", rule.model_dump())
    return rule


def delete_rule(rule_id: str) -> bool:
    if rule_id in _rules:
        del _rules[rule_id]
        _broadcast("rule_delete", {"id": rule_id})
        return True
    return False


# --- Pending approvals ---

def add_pending_approval(approval: PendingApproval) -> PendingApproval:
    _pending_approvals[approval.id] = approval
    _broadcast("approval_needed", approval.model_dump())
    return approval


def resolve_approval(approval_id: str, approved: bool) -> Optional[PendingApproval]:
    approval = _pending_approvals.get(approval_id)
    if approval:
        approval.approved = approved
        del _pending_approvals[approval_id]
        _broadcast("approval_resolved", {"id": approval_id, "approved": approved})
    return approval


def get_pending_approval(approval_id: str) -> Optional[PendingApproval]:
    return _pending_approvals.get(approval_id)


def expire_pending_approvals():
    """Call periodically to auto-deny approvals past their TTL."""
    now = time.time()
    expired = [
        a for a in _pending_approvals.values()
        if now - a.created_at > 300  # default 5 min; ideally use rule's timeout
    ]
    for a in expired:
        resolve_approval(a.id, approved=False)
