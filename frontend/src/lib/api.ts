const BASE = "http://localhost:8000";

export interface Message {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  conversation_id: string;
  response: string;
  pending_approval?: boolean;
  messages: unknown[];
}

export interface Rule {
  id: string;
  type: "block_tool" | "require_approval" | "input_validation" | "token_budget";
  enabled: boolean;
  tool_name?: string;
  field?: string;
  pattern?: string;
  reason?: string;
  max_tokens?: number;
  approval_timeout_seconds: number;
}

export interface LogEntry {
  conversation_id: string;
  type: "user" | "assistant" | "tool_call" | "tool_result";
  content?: string;
  tool?: string;
  input?: Record<string, unknown>;
  result?: string;
  verdict?: "ALLOW" | "BLOCK" | "NEEDS_APPROVAL";
  verdict_reason?: string;
  ts: number;
}

export const api = {
  async chat(message: string, conversationId?: string, history?: unknown[]): Promise<ChatResponse> {
    const res = await fetch(`${BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, conversation_id: conversationId, history: history ?? [] }),
    });
    if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
    return res.json();
  },

  async getRules(): Promise<Rule[]> {
    const res = await fetch(`${BASE}/rules`);
    if (!res.ok) throw new Error("Failed to fetch rules");
    return res.json();
  },

  async createRule(rule: Omit<Rule, "id" | "approval_timeout_seconds">): Promise<Rule> {
    const res = await fetch(`${BASE}/rules`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(rule),
    });
    if (!res.ok) throw new Error("Failed to create rule");
    return res.json();
  },

  async updateRule(id: string, patch: Partial<Rule>): Promise<Rule> {
    const res = await fetch(`${BASE}/rules/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!res.ok) throw new Error("Failed to update rule");
    return res.json();
  },

  async deleteRule(id: string): Promise<void> {
    const res = await fetch(`${BASE}/rules/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete rule");
  },

  async approveToolCall(approvalId: string, approved: boolean): Promise<void> {
    const res = await fetch(`${BASE}/rules/${approvalId}/approve?approved=${approved}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to resolve approval");
  },

  async getLogs(conversationId?: string): Promise<LogEntry[]> {
    const url = conversationId ? `${BASE}/logs?conversation_id=${conversationId}` : `${BASE}/logs`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch logs");
    return res.json();
  },
};
