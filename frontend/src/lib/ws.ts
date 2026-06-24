import { useEffect, useRef, useCallback, createContext, useContext } from "react";

const WS_URL = "ws://localhost:8000/ws";

export type WsEvent =
  | { event: "rule_update"; data: Record<string, unknown> }
  | { event: "rule_delete"; data: { id: string } }
  | { event: "log_event"; data: Record<string, unknown> }
  | { event: "approval_needed"; data: Record<string, unknown> }
  | { event: "approval_resolved"; data: { id: string; approved: boolean } };

type Listener = (evt: WsEvent) => void;

// Shared context — one WS connection for the whole app
export const WsContext = createContext<{ subscribe: (fn: Listener) => () => void } | null>(null);

export function useWsEvent(handler: Listener) {
  const ctx = useContext(WsContext);
  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  useEffect(() => {
    if (!ctx) return;
    return ctx.subscribe((evt) => handlerRef.current(evt));
  }, [ctx]);
}

// Place this once at App root
export function useWebSocketProvider() {
  const listeners = useRef<Set<Listener>>(new Set());
  const ws = useRef<WebSocket | null>(null);
  const unmounted = useRef(false);

  const connect = useCallback(() => {
    if (unmounted.current) return;
    console.log("[WS] Connecting to", WS_URL);
    const socket = new WebSocket(WS_URL);
    ws.current = socket;

    socket.onopen = () => console.log("[WS] Connected");

    socket.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as WsEvent;
        console.log("[WS] Message received:", data);
        listeners.current.forEach((fn) => fn(data));
      } catch {
        console.warn("[WS] Failed to parse message:", e.data);
      }
    };

    socket.onerror = (err) => console.error("[WS] Error:", err);

    socket.onclose = (e) => {
      console.warn("[WS] Disconnected (code:", e.code, "). Reconnecting in 2s…");
      if (!unmounted.current) setTimeout(connect, 2000);
    };
  }, []);

  useEffect(() => {
    unmounted.current = false;
    connect();
    return () => {
      unmounted.current = true;
      ws.current?.close();
    };
  }, [connect]);

  const subscribe = useCallback((fn: Listener) => {
    listeners.current.add(fn);
    return () => listeners.current.delete(fn);
  }, []);

  return { subscribe };
}
