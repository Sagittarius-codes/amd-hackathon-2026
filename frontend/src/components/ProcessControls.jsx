// src/components/ProcessControls.jsx
// Max-scenes input + Run Pipeline button + status badge.
// Calls POST /process with optional max_scenes body.

import { useState } from 'react';
import axios from 'axios';
import { Play, StopCircle, Loader, ChevronDown } from 'lucide-react';

// API base URL — set VITE_API_URL at build time (see frontend/Dockerfile).
// Falls back to localhost:8000 for local `npm run dev` usage.
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const STATUS_LABELS = {
  idle:       { label: 'Idle',        bg: '#27272a', color: '#71717a' },
  processing: { label: 'Processing',  bg: '#1e3a5f', color: '#60a5fa' },
  complete:   { label: 'Complete',    bg: '#052e16', color: '#4ade80' },
  error:      { label: 'Error',       bg: '#2d1414', color: '#f87171' },
};

// Fix F6: component now receives `effectiveStatus` — the combined
// (localStatus + WS status) expression computed in App.jsx, so the button
// locks and shows "Running…" immediately on click without waiting for the
// first WebSocket message to arrive from the backend.
export default function ProcessControls({ dark, effectiveStatus, onStarted, wsConnected }) {
  const [maxScenes, setMaxScenes] = useState('');
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState(null);

  const isRunning = effectiveStatus === 'processing';
  const badge     = STATUS_LABELS[effectiveStatus] || STATUS_LABELS.idle;

  const handleRun = async () => {
    setError(null);
    setLoading(true);
    try {
      const body = { max_scenes: maxScenes ? parseInt(maxScenes, 10) : null };
      await axios.post(`${API}/process`, body);
      onStarted?.();
      // Force immediate visual feedback
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to start');
    } finally {
      setLoading(false);
    }
  };

  const c = {
    label: {
      fontSize: 13,
      fontWeight: 600,
      color: dark ? '#a1a1aa' : '#6b7280',
      letterSpacing: '0.08em',
      textTransform: 'uppercase',
      marginBottom: 10,
      display: 'block',
    },
    inputWrap: {
      position: 'relative',
      marginBottom: 14,
    },
    input: {
      width: '100%',
      background: dark ? '#141414' : '#f9fafb',
      border: `1.5px solid ${dark ? '#27272a' : '#e5e7eb'}`,
      borderRadius: 10,
      padding: '10px 14px',
      color: dark ? '#e4e4e7' : '#111827',
      fontSize: 14,
      transition: 'border-color 0.15s',
    },
    inputHint: {
      fontSize: 11,
      color: dark ? '#52525b' : '#9ca3af',
      marginTop: 5,
    },
    badge: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      background: badge.bg,
      color: badge.color,
      fontSize: 12,
      fontWeight: 600,
      borderRadius: 99,
      padding: '4px 12px',
      marginBottom: 14,
    },
    dot: {
      width: 7, height: 7,
      borderRadius: '50%',
      background: badge.color,
      animation: isRunning ? 'pulse 1.5s ease-in-out infinite' : 'none',
    },
    button: {
      width: '100%',
      padding: '12px 0',
      borderRadius: 12,
      fontWeight: 700,
      fontSize: 14,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 8,
      transition: 'opacity 0.15s, transform 0.1s',
      background: isRunning
        ? dark ? '#1a1a2a' : '#f3f4f6'
        : 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
      color: isRunning
        ? dark ? '#52525b' : '#9ca3af'
        : '#ffffff',
      cursor: isRunning || loading ? 'not-allowed' : 'pointer',
      opacity: isRunning || loading ? 0.6 : 1,
      boxShadow: isRunning ? 'none' : '0 4px 20px rgba(99,102,241,0.35)',
    },
    wsIndicator: {
      display: 'flex', alignItems: 'center', gap: 6,
      fontSize: 11,
      color: dark ? '#52525b' : '#9ca3af',
      marginTop: 12,
    },
    wsDot: {
      width: 6, height: 6,
      borderRadius: '50%',
      background: wsConnected ? '#22c55e' : '#ef4444',
    },
    errorBox: {
      marginTop: 10,
      padding: '8px 12px',
      borderRadius: 8,
      background: dark ? '#1f0a0a' : '#fef2f2',
      color: dark ? '#f87171' : '#dc2626',
      fontSize: 12,
    },
  };

  return (
    <div>
      <span style={c.label}>Pipeline Controls</span>

      {/* Status badge */}
      <div style={c.badge}>
        <span style={c.dot} />
        {badge.label}
      </div>

      {/* Max scenes input */}
      <div style={c.inputWrap}>
        <input
          style={c.input}
          type="number"
          min={1}
          placeholder="Max scenes (leave empty = all)"
          value={maxScenes}
          onChange={(e) => setMaxScenes(e.target.value)}
          disabled={isRunning}
        />
        <p style={c.inputHint}>Limit scenes for testing — leave blank for full run</p>
      </div>

      {/* Run button */}
      <button
        style={c.button}
        onClick={handleRun}
        disabled={isRunning || loading}
      >
        {loading
          ? <Loader size={16} style={{ animation: 'spin 1s linear infinite' }} />
          : isRunning
          ? <StopCircle size={16} />
          : <Play size={16} />
        }
        {loading ? 'Starting…' : isRunning ? 'Running…' : 'Run Pipeline'}
      </button>

      {/* WebSocket connection indicator */}
      <div style={c.wsIndicator}>
        <span style={c.wsDot} />
        {wsConnected ? 'WebSocket connected' : 'Reconnecting WebSocket…'}
      </div>

      {error && <div style={c.errorBox}>{error}</div>}
    </div>
  );
}
