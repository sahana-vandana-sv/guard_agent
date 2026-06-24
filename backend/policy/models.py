import uuid
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class RuleType(str, Enum):
    block_tool = "block_tool"
    require_approval = "require_approval"
    input_validation = "input_validation"
    token_budget = "token_budget"


class PolicyVerdict(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"


class GuardrailRule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: RuleType
    enabled: bool = True
    # block_tool / require_approval: which tool this applies to ("*" = all)
    tool_name: Optional[str] = None
    # input_validation: field name, regex pattern, and human-readable reason
    field: Optional[str] = None
    pattern: Optional[str] = None
    reason: Optional[str] = None
    # token_budget: max tokens per conversation
    max_tokens: Optional[int] = None
    # approval TTL in seconds (for require_approval rules)
    approval_timeout_seconds: int = 300

    model_config = {"use_enum_values": True}


class EvaluationResult(BaseModel):
    verdict: PolicyVerdict
    rule_id: Optional[str] = None
    reason: str = ""

    model_config = {"use_enum_values": True}


class PendingApproval(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    conversation_id: str
    tool_name: str
    tool_input: dict[str, Any]
    rule_id: str
    created_at: float  # unix timestamp
    approved: Optional[bool] = None
