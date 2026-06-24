import { useState, useEffect, useCallback } from "react";
import { api, Rule } from "../lib/api";
import { useWsEvent } from "../lib/ws";

const RULE_TYPES = ["block_tool", "require_approval", "input_validation", "token_budget"] as const;

const TYPE_LABELS: Record<string, string> = {
  block_tool: "Block Tool",
  require_approval: "Require Approval",
  input_validation: "Input Validation",
  token_budget: "Token Budget",
};

const TYPE_COLORS: Record<string, string> = {
  block_tool: "bg-red-100 text-red-700",
  require_approval: "bg-yellow-100 text-yellow-700",
  input_validation: "bg-blue-100 text-blue-700",
  token_budget: "bg-purple-100 text-purple-700",
};

export function RulesPanel() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<Partial<Rule>>({ type: "block_tool", enabled: true });
  const [saving, setSaving] = useState(false);

  const fetchRules = useCallback(async () => {
    const data = await api.getRules();
    setRules(data);
  }, []);

  useEffect(() => { fetchRules(); }, [fetchRules]);

  useWsEvent((evt) => {
    if (evt.event === "rule_update") {
      console.log("[Rules] WS rule_update:", evt.data);
      setRules((prev) => {
        const idx = prev.findIndex((r) => r.id === (evt.data as Rule).id);
        if (idx >= 0) {
          const next = [...prev];
          next[idx] = evt.data as Rule;
          return next;
        }
        return [...prev, evt.data as Rule];
      });
    } else if (evt.event === "rule_delete") {
      console.log("[Rules] WS rule_delete:", evt.data.id);
      setRules((prev) => prev.filter((r) => r.id !== evt.data.id));
    }
  });

  async function toggle(rule: Rule) {
    await api.updateRule(rule.id, { enabled: !rule.enabled });
  }

  async function remove(id: string) {
    await api.deleteRule(id);
  }

  async function submit() {
    if (!form.type) return;
    setSaving(true);
    try {
      await api.createRule(form as Omit<Rule, "id" | "approval_timeout_seconds">);
      setForm({ type: "block_tool", enabled: true });
      setShowForm(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-gray-200 bg-white flex items-center justify-between">
        <h2 className="font-semibold text-gray-800">Guardrail Rules</h2>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="text-sm bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700 transition-colors"
        >
          {showForm ? "Cancel" : "+ New Rule"}
        </button>
      </div>

      {showForm && (
        <div className="px-4 py-3 border-b border-gray-200 bg-blue-50 space-y-2">
          <div className="flex gap-2">
            <select
              className="flex-1 border border-gray-300 rounded px-2 py-1.5 text-sm"
              value={form.type}
              onChange={(e) => setForm({ type: e.target.value as Rule["type"], enabled: true })}
            >
              {RULE_TYPES.map((t) => (
                <option key={t} value={t}>{TYPE_LABELS[t]}</option>
              ))}
            </select>
          </div>

          {(form.type === "block_tool" || form.type === "require_approval") && (
            <input
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
              placeholder="Tool name (e.g. send_email or * for all)"
              value={form.tool_name ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, tool_name: e.target.value }))}
            />
          )}

          {form.type === "input_validation" && (
            <>
              <input
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
                placeholder="Tool name (e.g. draft_email)"
                value={form.tool_name ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, tool_name: e.target.value }))}
              />
              <input
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
                placeholder="Field name (e.g. to)"
                value={form.field ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, field: e.target.value }))}
              />
              <input
                className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
                placeholder="Regex pattern (e.g. .*@company\.com$)"
                value={form.pattern ?? ""}
                onChange={(e) => setForm((f) => ({ ...f, pattern: e.target.value }))}
              />
            </>
          )}

          {form.type === "token_budget" && (
            <input
              type="number"
              className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
              placeholder="Max tokens per conversation (e.g. 2000)"
              value={form.max_tokens ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, max_tokens: parseInt(e.target.value) }))}
            />
          )}

          <input
            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm"
            placeholder="Reason / description (optional)"
            value={form.reason ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))}
          />

          <button
            onClick={submit}
            disabled={saving}
            className="w-full bg-blue-600 text-white rounded px-3 py-1.5 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saving ? "Saving…" : "Save Rule"}
          </button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2 bg-gray-50">
        {rules.length === 0 && (
          <p className="text-sm text-gray-400 text-center mt-8">No rules yet. Add one above.</p>
        )}
        {rules.map((rule) => (
          <div
            key={rule.id}
            className={`bg-white border rounded-lg px-4 py-3 flex items-start gap-3 ${
              rule.enabled ? "border-gray-200" : "border-gray-100 opacity-60"
            }`}
          >
            <button
              onClick={() => toggle(rule)}
              className={`mt-0.5 w-10 h-5 rounded-full transition-colors flex-shrink-0 ${
                rule.enabled ? "bg-green-500" : "bg-gray-300"
              }`}
              title={rule.enabled ? "Disable" : "Enable"}
            >
              <span
                className={`block w-4 h-4 bg-white rounded-full shadow transition-transform mx-0.5 ${
                  rule.enabled ? "translate-x-5" : "translate-x-0"
                }`}
              />
            </button>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${TYPE_COLORS[rule.type]}`}>
                  {TYPE_LABELS[rule.type]}
                </span>
                {rule.tool_name && (
                  <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-700">
                    {rule.tool_name}
                  </code>
                )}
                {rule.field && (
                  <span className="text-xs text-gray-500">
                    field: <code className="bg-gray-100 px-1 rounded">{rule.field}</code>
                  </span>
                )}
              </div>
              {rule.pattern && (
                <p className="text-xs text-gray-500 mt-1">pattern: <code>{rule.pattern}</code></p>
              )}
              {rule.max_tokens && (
                <p className="text-xs text-gray-500 mt-1">max tokens: {rule.max_tokens}</p>
              )}
              {rule.reason && (
                <p className="text-xs text-gray-400 mt-1">{rule.reason}</p>
              )}
              <p className="text-xs text-gray-300 mt-1">id: {rule.id}</p>
            </div>

            <button
              onClick={() => remove(rule.id)}
              className="text-gray-300 hover:text-red-500 transition-colors text-lg leading-none flex-shrink-0"
              title="Delete rule"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
