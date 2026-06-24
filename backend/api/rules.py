from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from policy.models import GuardrailRule, RuleType
import policy.store as store

router = APIRouter(prefix="/rules", tags=["rules"])


class CreateRuleRequest(BaseModel):
    type: RuleType
    tool_name: Optional[str] = None
    field: Optional[str] = None
    pattern: Optional[str] = None
    reason: Optional[str] = None
    max_tokens: Optional[int] = None
    approval_timeout_seconds: int = 300


class UpdateRuleRequest(BaseModel):
    enabled: Optional[bool] = None
    tool_name: Optional[str] = None
    field: Optional[str] = None
    pattern: Optional[str] = None
    reason: Optional[str] = None
    max_tokens: Optional[int] = None


@router.get("")
def list_rules():
    return [r.model_dump() for r in store.list_rules()]


@router.post("", status_code=201)
def create_rule(req: CreateRuleRequest):
    rule = GuardrailRule(**req.model_dump())
    store.upsert_rule(rule)
    return rule.model_dump()


@router.patch("/{rule_id}")
def update_rule(rule_id: str, req: UpdateRuleRequest):
    rule = store.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    updated = rule.model_copy(update={k: v for k, v in req.model_dump().items() if v is not None})
    store.upsert_rule(updated)
    return updated.model_dump()


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: str):
    if not store.delete_rule(rule_id):
        raise HTTPException(status_code=404, detail="Rule not found")


@router.post("/{approval_id}/approve")
def approve_tool(approval_id: str, approved: bool = True):
    result = store.resolve_approval(approval_id, approved)
    if not result:
        raise HTTPException(status_code=404, detail="Pending approval not found")
    return {"id": approval_id, "approved": approved}
