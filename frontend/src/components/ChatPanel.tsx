import { useState, useRef, useEffect } from "react";
import { api, ChatResponse } from "../lib/api";

interface Turn {
  role: "user" | "assistant";
  content: string;
  pending_approval?: boolean;
  approvalId?: string;
}

export function ChatPanel() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [convId, setConvId] = useState<string | undefined>();
  const [history, setHistory] = useState<unknown[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  async function send() {
    const msg = input.trim();
    if (!msg || loading) return;
    setInput("");
    setTurns((t) => [...t, { role: "user", content: msg }]);
    setLoading(true);

    try {
      const res: ChatResponse = await api.chat(msg, convId, history);
      setConvId(res.conversation_id);
      setHistory(res.messages);
      setTurns((t) => [
        ...t,
        {
          role: "assistant",
          content: res.response,
          pending_approval: res.pending_approval,
        },
      ]);
    } catch (e) {
      setTurns((t) => [
        ...t,
        { role: "assistant", content: `Error: ${e instanceof Error ? e.message : "unknown"}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-gray-200 bg-white">
        <h2 className="font-semibold text-gray-800">Agent Chat</h2>
        {convId && <p className="text-xs text-gray-400">conv: {convId}</p>}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 bg-gray-50">
        {turns.length === 0 && (
          <p className="text-sm text-gray-400 text-center mt-8">
            Send a message to start a conversation.
          </p>
        )}
        {turns.map((t, i) => (
          <div key={i} className={`flex ${t.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[75%] rounded-xl px-4 py-2 text-sm whitespace-pre-wrap ${
                t.role === "user"
                  ? "bg-blue-600 text-white"
                  : t.pending_approval
                  ? "bg-yellow-50 border border-yellow-300 text-yellow-900"
                  : t.content.startsWith("Error:")
                  ? "bg-red-50 border border-red-200 text-red-800"
                  : "bg-white border border-gray-200 text-gray-800"
              }`}
            >
              {t.pending_approval && (
                <p className="text-xs font-semibold text-yellow-700 mb-1">
                  Awaiting approval
                </p>
              )}
              {t.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-xl px-4 py-2 text-sm text-gray-400">
              thinking…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="px-4 py-3 border-t border-gray-200 bg-white flex gap-2">
        <input
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Type a message…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
          disabled={loading}
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50 hover:bg-blue-700 transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  );
}
