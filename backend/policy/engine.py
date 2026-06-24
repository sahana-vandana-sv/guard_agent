"""
Policy engine — the heart of the system.
Receives (tool_name, input_args, conversation_id, token_usage) and returns
an EvaluationResult with verdict ALLOW | BLOCK | NEEDS_APPROVAL.

Rules are evaluated in strict priority order:
  1. block_tool      (highest priority — explicit denies)
  2. input_validation
  3. token_budget
  4. require_approval
  5. ALLOW           (default)

This module never touches the LLM or MCP transport layers.
"""
import re
import time
from typing import Any

from policy.models import EvaluationResult, GuardrailRule, PendingApproval, PolicyVerdict, RuleType
import policy.store as store


def evaluate(
    tool_name: str,
    tool_input: dict[str, Any],
    conversation_id: str,
    token_usage: int = 0,
) -> EvaluationResult:
    rules = store.list_rules()
    enabled = [r for r in rules if r.enabled]

    # Sort by priority: block_tool first, then input_validation, token_budget, require_approval
    priority = {
        RuleType.block_tool: 0,
        RuleType.input_validation: 1,
        RuleType.token_budget: 2,
        RuleType.require_approval: 3,
    }
    enabled.sort(key=lambda r: priority.get(r.type, 99))

    for rule in enabled:
        result = _apply_rule(rule, tool_name, tool_input, conversation_id, token_usage)
        if result is not None:
            return result

    return EvaluationResult(verdict=PolicyVerdict.ALLOW, reason="No matching rules — allowed by default")


def _apply_rule(
    rule: GuardrailRule,
    tool_name: str,
    tool_input: dict[str, Any],
    conversation_id: str,
    token_usage: int,
) -> EvaluationResult | None:
    if rule.type == RuleType.block_tool:
        if _matches_tool(rule.tool_name, tool_name):
            return EvaluationResult(
                verdict=PolicyVerdict.BLOCK,
                rule_id=rule.id,
                reason=f"Tool '{tool_name}' is blocked by policy rule {rule.id}",
            )

    elif rule.type == RuleType.input_validation:
        if _matches_tool(rule.tool_name, tool_name) and rule.field and rule.pattern:
            value = str(tool_input.get(rule.field, ""))
            if not re.search(rule.pattern, value):
                return EvaluationResult(
                    verdict=PolicyVerdict.BLOCK,
                    rule_id=rule.id,
                    reason=rule.reason or f"Input validation failed: field '{rule.field}' does not match pattern '{rule.pattern}'",
                )

    elif rule.type == RuleType.token_budget:
        if rule.max_tokens and token_usage >= rule.max_tokens:
            return EvaluationResult(
                verdict=PolicyVerdict.BLOCK,
                rule_id=rule.id,
                reason=f"Token budget exceeded: {token_usage} tokens used, limit is {rule.max_tokens}",
            )

    elif rule.type == RuleType.require_approval:
        if _matches_tool(rule.tool_name, tool_name):
            approval = PendingApproval(
                conversation_id=conversation_id,
                tool_name=tool_name,
                tool_input=tool_input,
                rule_id=rule.id,
                created_at=time.time(),
            )
            store.add_pending_approval(approval)
            return EvaluationResult(
                verdict=PolicyVerdict.NEEDS_APPROVAL,
                rule_id=rule.id,
                reason=f"Tool '{tool_name}' requires human approval (approval ID: {approval.id})",
            )

    return None


def _matches_tool(rule_tool: str | None, tool_name: str) -> bool:
    if not rule_tool or rule_tool == "*":
        return True
    return rule_tool == tool_name
