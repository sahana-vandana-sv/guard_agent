import { useState, useMemo } from "react";
import { ChatPanel } from "./components/ChatPanel";
import { RulesPanel } from "./components/RulesPanel";
import { LogsPanel } from "./components/LogsPanel";
import { WsContext, useWebSocketProvider } from "./lib/ws";

type Tab = "chat" | "rules" | "logs";

const TABS: { id: Tab; label: string }[] = [
  { id: "chat", label: "Chat" },
  { id: "rules", label: "Rules" },
  { id: "logs", label: "Logs" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("chat");
  const ws = useWebSocketProvider();
  const wsCtx = useMemo(() => ({ subscribe: ws.subscribe }), [ws.subscribe]);

  return (
    <WsContext.Provider value={wsCtx}>
    <div className="h-screen flex flex-col bg-gray-100">
      {/* Header */}
      <header className="bg-gray-900 text-white px-6 py-3 flex items-center gap-4 flex-shrink-0">
        <div>
          <h1 className="text-base font-bold tracking-tight">Guard Agent</h1>
          <p className="text-xs text-gray-400">Policy-enforced AI agent dashboard</p>
        </div>
        <nav className="ml-auto flex gap-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                tab === t.id
                  ? "bg-blue-600 text-white"
                  : "text-gray-300 hover:text-white hover:bg-gray-700"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      {/* Main content */}
      <main className="flex-1 overflow-hidden">
        <div className={`h-full ${tab === "chat" ? "block" : "hidden"}`}>
          <ChatPanel />
        </div>
        <div className={`h-full ${tab === "rules" ? "block" : "hidden"}`}>
          <RulesPanel />
        </div>
        <div className={`h-full ${tab === "logs" ? "block" : "hidden"}`}>
          <LogsPanel />
        </div>
      </main>
    </div>
    </WsContext.Provider>
  );
}
