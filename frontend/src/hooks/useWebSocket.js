// src/hooks/useWebSocket.js
// Connects to ws://localhost:8000/ws, processes all pipeline message types,
// and exposes live state to any consumer.  Auto-reconnects on disconnect.

import { useState, useEffect, useRef, useCallback } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_URL = (() => {
  return API_URL.replace(/^http/, 'ws') + '/ws';
})();
const RECONNECT_DELAY_MS = 3000;

/**
 * @returns {{
 *   scenes: Array,       scene descriptors from scene_detected
 *   results: Array,      accumulated caption_result payloads
 *   status: string,      idle | processing | complete | error
 *   progress: number,    0–100
 *   currentScene: number,
 *   totalScenes: number,
 *   errorMessage: string | null,
 *   wsConnected: boolean,
 * }}
 */
export function useWebSocket() {
  const [scenes, setScenes]             = useState([]);
  const [results, setResults]           = useState([]);
  const [status, setStatus]             = useState('idle');
  const [progress, setProgress]         = useState(0);
  const [currentScene, setCurrentScene] = useState(0);
  const [totalScenes, setTotalScenes]   = useState(0);
  const [errorMessage, setErrorMessage] = useState(null);
  const [wsConnected, setWsConnected]   = useState(false);

  const wsRef          = useRef(null);
  const reconnectTimer = useRef(null);
  const isMounted      = useRef(true);

  const connect = useCallback(() => {
    if (!isMounted.current) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!isMounted.current) return;
      setWsConnected(true);
      // Clear any pending reconnect timer
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
    };

    ws.onmessage = (event) => {
      if (!isMounted.current) return;
      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch {
        return;
      }

      switch (msg.type) {
        case 'scene_detected':
          // Fix F1: clear results and progress from any previous run before
          // populating the new scene list.  Handles the case where the WS
          // reconnects and a fresh pipeline run arrives while old cards are
          // still displayed from a prior session.
          setResults([]);
          setProgress(10);
          setCurrentScene(0);
          setTotalScenes(msg.total);
          setScenes(msg.scenes || []);
          setStatus('processing');
          break;

        case 'captioning_start':
          setCurrentScene(msg.scene);
          break;

        case 'caption_result': {
          const { scene, captions, frame_info } = msg;
          setResults((prev) => {
            // Avoid duplicates if WS reconnects mid-run
            const exists = prev.some((r) => r.scene === scene);
            if (exists) return prev;
            return [...prev, { scene, captions, frame_info }];
          });
          // Derive progress from scene count
          setTotalScenes((total) => {
            const pct = total > 0 ? 10 + (scene / total) * 90 : 10;
            setProgress(Math.min(100, Math.round(pct)));
            return total;
          });
          break;
        }

        case 'complete':
          setStatus('complete');
          setProgress(100);
          setCurrentScene(0);
          break;

        case 'error':
          setStatus('error');
          setErrorMessage(msg.message || 'Unknown error');
          break;

        case 'ping':
          // Server-side liveness ping (added in A8 fix) — discard silently.
          break;

        default:
          break;
      }
    };

    ws.onclose = () => {
      if (!isMounted.current) return;
      setWsConnected(false);
      // Schedule reconnect
      reconnectTimer.current = setTimeout(() => {
        if (isMounted.current) connect();
      }, RECONNECT_DELAY_MS);
    };

    ws.onerror = () => {
      // onclose fires immediately after onerror; no extra handling needed
      ws.close();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    isMounted.current = true;
    
    // Fetch initial state to recover if user refreshes page
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${API_URL}/status`);
        const data = await res.json();
        if (isMounted.current && data.status === 'processing') {
          setStatus(data.status);
          setProgress(data.progress_pct);
          setCurrentScene(data.current_scene);
          setTotalScenes(data.total_scenes);
          setResults(data.results || []);
        }
      } catch (e) {
        console.warn("Could not fetch initial status:", e);
      }
    };
    
    fetchStatus();
    connect();
    
    return () => {
      isMounted.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  /** Call this before starting a new pipeline run to clear previous results. */
  const reset = useCallback(() => {
    setScenes([]);
    setResults([]);
    setStatus('idle');
    setProgress(0);
    setCurrentScene(0);
    setTotalScenes(0);
    setErrorMessage(null);
  }, []);

  return {
    scenes,
    results,
    status,
    progress,
    currentScene,
    totalScenes,
    errorMessage,
    wsConnected,
    reset,
  };
}
