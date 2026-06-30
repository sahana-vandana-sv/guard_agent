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


_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|rules?|constraints?|policies?)",
    r"(bypass|override|disable|forget|disregard)\s+(the\s+)?(policy|guardrail|rules?|restrictions?|filter)",
    r"you\s+are\s+now\s+(in\s+)?(developer|admin|sudo|unrestricted|jailbreak)\s+mode",
    r"act\s+as\s+(if\s+)?(you\s+(have\s+no|are\s+without)\s+(rules?|restrictions?|policies?))",
    r"pretend\s+(you\s+)?(have\s+no|there\s+are\s+no)\s+(rules?|restrictions?|guardrails?)",
    r"do\s+not\s+(enforce|apply|check|follow)\s+(the\s+)?(policy|rules?|guardrails?)",
    r"system\s*:\s*(ignore|override|bypass)",
    r"<\s*system\s*>.*?(ignore|override|bypass)",
]

_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE | re.DOTALL)


def _check_prompt_injection(tool_input: dict[str, Any]) -> EvaluationResult | None:
    """Scan all string fields for prompt injection attempts. Runs before all rules."""
    def _extract_strings(obj, depth=0):
        if depth > 5:
            return
        if isinstance(obj, str):
            yield obj
        elif isinstance(obj, dict):
            for v in obj.values():
                yield from _extract_strings(v, depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                yield from _extract_strings(item, depth + 1)

    for text in _extract_strings(tool_input):
        if _INJECTION_RE.search(text):
            return EvaluationResult(
                verdict=PolicyVerdict.BLOCK,
                reason=f"Prompt injection attempt detected in tool input. The policy engine cannot be overridden via tool arguments.",
            )
    return None


def evaluate(
    tool_name: str,
    tool_input: dict[str, Any],
    conversation_id: str,
    token_usage: int = 0,
) -> EvaluationResult:
    # Prompt injection check — always runs first, not configurable
    injection = _check_prompt_injection(tool_input)
    if injection:
        return injection

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
