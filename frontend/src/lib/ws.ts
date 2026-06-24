import { useEffect, useRef, useCallback } from "react";

const WS_URL = "ws://localhost:8000/ws";

export type WsEvent =
  | { event: "rule_update"; data: Record<string, unknown> }
  | { event: "rule_delete"; data: { id: string } }
  | { event: "log_event"; data: Record<string, unknown> }
  | { event: "approval_needed"; data: Record<string, unknown> }
  | { event: "approval_resolved"; data: { id: string; approved: boolean } };

export function useWebSocket(onMessage: (evt: WsEvent) => void) {
  const ws = useRef<WebSocket | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    const socket = new WebSocket(WS_URL);
    ws.current = socket;

    socket.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as WsEvent;
        onMessageRef.current(data);
      } catch {
        // ignore malformed frames
      }
    };

    socket.onclose = () => {
      // Reconnect after 2s if connection drops
      setTimeout(connect, 2000);
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      ws.current?.close();
    };
  }, [connect]);
}
