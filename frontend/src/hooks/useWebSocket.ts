import { useCallback, useEffect, useRef, useState } from 'react';
import type { BranchesData, EnvironmentsData, WsOutgoingMessage } from '../types/index';

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected';

export interface UseWebSocketReturn {
  sendMessage: (msg: WsOutgoingMessage) => void;
  lastBranchesMessage: BranchesData | null;
  lastEnvironmentsMessage: EnvironmentsData | null;
  lastError: { message: string } | null;
  connectionStatus: ConnectionStatus;
}

export function useWebSocket(): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [lastBranchesMessage, setLastBranchesMessage] = useState<BranchesData | null>(null);
  const [lastEnvironmentsMessage, setLastEnvironmentsMessage] = useState<EnvironmentsData | null>(null);
  const [lastError, setLastError] = useState<{ message: string } | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('connecting');

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      wsRef.current.onclose = null;
      wsRef.current.close();
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const ws = new WebSocket(`${protocol}//${host}/ws`);
    wsRef.current = ws;
    setConnectionStatus('connecting');

    ws.onopen = () => {
      setConnectionStatus('connected');
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const message: unknown = JSON.parse(event.data as string);
        if (message && typeof message === 'object') {
          const msg = message as Record<string, unknown>;
          if ('branches' in msg) {
            setLastBranchesMessage(msg.branches as BranchesData);
          } else if ('environments' in msg) {
            setLastEnvironmentsMessage(msg.environments as EnvironmentsData);
          } else if ('error' in msg) {
            setLastError(msg.error as { message: string });
          }
        }
      } catch (e) {
        console.error('Error processing WebSocket message:', e);
      }
    };

    ws.onclose = () => {
      setConnectionStatus('disconnected');
      reconnectTimerRef.current = setTimeout(() => connect(), 5000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, [connect]);

  const sendMessage = useCallback((msg: WsOutgoingMessage) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  return { sendMessage, lastBranchesMessage, lastEnvironmentsMessage, lastError, connectionStatus };
}
