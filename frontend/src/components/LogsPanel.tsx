import { useState, useEffect, useRef, useCallback } from "react";
import { api, LogEntry } from "../lib/api";
import { useWsEvent } from "../lib/ws";

const VERDICT_COLORS: Record<string, string> = {
  ALLOW: "text-green-600",
  BLOCK: "text-red-600",
  NEEDS_APPROVAL: "text-yellow-600",
};

function fmt(ts: number) {
  return new Date(ts * 1000).toLocaleTimeString();
}

export function LogsPanel() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  const fetchLogs = useCallback(async () => {
    const data = await api.getLogs();
    setLogs(data);
  }, []);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  useWsEvent((evt) => {
    if (evt.event === "log_event") {
      console.log("[Logs] WS log_event:", evt.data);
      setLogs((prev) => [...prev, evt.data as LogEntry]);
    }
  });

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-gray-200 bg-white flex items-center justify-between">
        <h2 className="font-semibold text-gray-800">Activity Log</h2>
        <button
          onClick={fetchLogs}
          className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
        >
          Refresh
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-1.5 bg-gray-50 font-mono text-xs">
        {logs.length === 0 && (
          <p className="text-gray-400 text-center mt-8 font-sans text-sm">
            No activity yet. Send a chat message.
          </p>
        )}
        {logs.map((log, i) => (
          <div key={i} className="flex gap-2 items-start">
            <span className="text-gray-300 flex-shrink-0 w-20">{fmt(log.ts)}</span>

            {log.type === "user" && (
              <span className="text-blue-600">
                <span className="text-gray-400">[user]</span> {log.content}
              </span>
            )}

            {log.type === "assistant" && (
              <span className="text-gray-700">
                <span className="text-gray-400">[assistant]</span> {log.content?.slice(0, 120)}
                {(log.content?.length ?? 0) > 120 ? "…" : ""}
              </span>
            )}

            {log.type === "tool_call" && (
              <span>
                <span className="text-gray-400">[tool_call]</span>{" "}
                <span className="text-purple-700">{log.tool}</span>{" "}
                <span className={VERDICT_COLORS[log.verdict ?? ""] ?? "text-gray-500"}>
                  {log.verdict}
                </span>
                {log.verdict === "BLOCK" && (
                  <span className="text-gray-400"> — {log.verdict_reason}</span>
                )}
              </span>
            )}

            {log.type === "tool_result" && (
              <span className="text-gray-500">
                <span className="text-gray-400">[result]</span>{" "}
                <span className="text-purple-600">{log.tool}</span>{" "}
                {log.result?.slice(0, 100)}
                {(log.result?.length ?? 0) > 100 ? "…" : ""}
              </span>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
