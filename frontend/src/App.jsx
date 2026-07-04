// src/App.jsx
// Root layout: sidebar (left) + main area (right).
// Owns dark-mode state and wires up the WebSocket hook to all children.

import { useState, useEffect, useRef } from 'react';
import { useWebSocket } from './hooks/useWebSocket';

import VideoUpload    from './components/VideoUpload';
import ProcessControls from './components/ProcessControls';
import ProgressPanel  from './components/ProgressPanel';
import Timeline       from './components/Timeline';
import SceneCard      from './components/SceneCard';
import StatusBar      from './components/StatusBar';

import { Clapperboard } from 'lucide-react';

export default function App() {
  const [dark, setDark]           = useState(true);
  const [startTime, setStartTime] = useState(null);

  const {
    scenes, results, status, progress,
    currentScene, totalScenes, wsConnected, reset,
  } = useWebSocket();

  // Record pipeline start time for the elapsed timer
  useEffect(() => {
    if (status === 'processing' && !startTime) {
      setStartTime(Date.now());
    }
    if (status === 'idle') {
      setStartTime(null);
    }
  }, [status]); // eslint-disable-line react-hooks/exhaustive-deps

  // Find the timestamp of the scene currently being processed
  const currentTimestamp = (() => {
    if (currentScene === 0) return null;
    const hit = results.find((r) => r.scene === currentScene);
    return hit?.frame_info?.timestamp_str || null;
  })();

  // ---- Theme tokens --------------------------------------------------------
  const bg      = dark ? '#0f0f0f' : '#f5f5f5';
  const sidebar  = dark ? '#111111' : '#ffffff';
  const border   = dark ? '#1f1f1f' : '#e5e7eb';

  // ---- Styles --------------------------------------------------------------
  const s = {
    root: {
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      background: bg,
      color: dark ? '#e4e4e7' : '#111827',
      transition: 'background 0.25s, color 0.25s',
    },

    /* ── Top header bar ── */
    header: {
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      padding: '14px 24px',
      background: sidebar,
      borderBottom: `1.5px solid ${border}`,
      flexShrink: 0,
    },
    logoIcon: {
      width: 36, height: 36,
      borderRadius: 10,
      background: 'linear-gradient(135deg,#6366f1 0%,#a855f7 100%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0,
    },
    title: {
      fontSize: 16,
      fontWeight: 800,
      color: dark ? '#ffffff' : '#111827',
      letterSpacing: '-0.3px',
    },
    subtitle: {
      fontSize: 11,
      color: dark ? '#52525b' : '#9ca3af',
      marginLeft: 2,
    },

    /* ── Body below header ── */
    body: {
      display: 'flex',
      flex: 1,
      overflow: 'hidden',
    },

    /* ── Left sidebar ── */
    sidebar: {
      width: 280,
      flexShrink: 0,
      background: sidebar,
      borderRight: `1.5px solid ${border}`,
      display: 'flex',
      flexDirection: 'column',
      gap: 0,
      overflowY: 'auto',
      transition: 'background 0.25s',
    },
    sidebarSection: {
      padding: '20px 18px',
      borderBottom: `1px solid ${border}`,
    },

    /* ── Main area ── */
    main: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    },
    topRow: {
      display: 'flex',
      gap: 16,
      padding: '16px 20px',
      flexShrink: 0,
    },
    cardsArea: {
      flex: 1,
      overflowY: 'auto',
      padding: '0 20px 20px',
    },
    cardsGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
      gap: 16,
    },
    emptyState: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      gap: 12,
      opacity: 0.4,
    },
    emptyText: {
      fontSize: 14,
      fontWeight: 500,
      color: dark ? '#71717a' : '#6b7280',
    },
  };

  return (
    <div style={s.root}>
      {/* ── Header ─────────────────────────────────────────────── */}
      <header style={s.header}>
        <div style={s.logoIcon}>
          <Clapperboard size={18} color="#fff" />
        </div>
        <div>
          <div style={s.title}>CaptionAI Pipeline</div>
          <div style={s.subtitle}>AMD Developer Hackathon 2026</div>
        </div>

        {/* Connection badge */}
        <div style={{
          marginLeft: 'auto',
          display: 'flex', alignItems: 'center', gap: 6,
          fontSize: 11, fontWeight: 600,
          color: wsConnected
            ? dark ? '#4ade80' : '#16a34a'
            : dark ? '#f87171' : '#dc2626',
          background: wsConnected
            ? dark ? '#052e16' : '#dcfce7'
            : dark ? '#2d1414' : '#fee2e2',
          padding: '5px 12px',
          borderRadius: 99,
        }}>
          <span style={{
            width: 7, height: 7, borderRadius: '50%',
            background: wsConnected ? '#22c55e' : '#ef4444',
            animation: wsConnected ? 'none' : 'pulse 1.5s infinite',
          }} />
          {wsConnected ? 'Live' : 'Connecting…'}
        </div>
      </header>

      {/* ── Body ───────────────────────────────────────────────── */}
      <div style={s.body}>

        {/* ── Sidebar ─── */}
        <aside style={s.sidebar}>
          <div style={s.sidebarSection}>
            <VideoUpload
              dark={dark}
              onUploaded={reset}
            />
          </div>

          <div style={s.sidebarSection}>
            <ProcessControls
              dark={dark}
              status={status}
              wsConnected={wsConnected}
              onStarted={() => setStartTime(Date.now())}
            />
          </div>

          {/* Spacer pushes nothing — sidebar scrolls if needed */}
        </aside>

        {/* ── Main area ─── */}
        <main style={s.main}>
          {/* Progress ring + Timeline row */}
          <div style={s.topRow}>
            <ProgressPanel
              dark={dark}
              status={status}
              progress={progress}
              currentScene={currentScene}
              totalScenes={totalScenes}
              currentTimestamp={currentTimestamp}
            />

            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 16 }}>
              <Timeline
                dark={dark}
                scenes={scenes}
                results={results}
                currentScene={currentScene}
              />

              {/* Quick stat pills */}
              {results.length > 0 && (
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  {[
                    { label: 'Detected',  value: totalScenes, color: '#6366f1' },
                    { label: 'Captioned', value: results.length, color: '#22c55e' },
                    { label: 'Pending',   value: Math.max(0, totalScenes - results.length), color: '#f59e0b' },
                  ].map(({ label, value, color }) => (
                    <div key={label} style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      background: dark ? '#1a1a1a' : '#ffffff',
                      borderRadius: 10,
                      padding: '10px 16px',
                      border: `1.5px solid ${dark ? '#27272a' : '#f3f4f6'}`,
                    }}>
                      <span style={{
                        fontSize: 20, fontWeight: 800, color,
                      }}>{value}</span>
                      <span style={{
                        fontSize: 11, fontWeight: 600,
                        color: dark ? '#52525b' : '#9ca3af',
                        textTransform: 'uppercase', letterSpacing: '0.08em',
                      }}>{label}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Scene cards */}
          <div style={s.cardsArea}>
            {results.length === 0 ? (
              <div style={s.emptyState}>
                <Clapperboard size={48} color={dark ? '#27272a' : '#d1d5db'} />
                <p style={s.emptyText}>
                  {status === 'processing'
                    ? 'Detecting scenes…'
                    : 'Scene captions will appear here'}
                </p>
              </div>
            ) : (
              <div style={s.cardsGrid}>
                {results.map((result) => (
                  <SceneCard
                    key={result.scene}
                    dark={dark}
                    result={result}
                  />
                ))}
              </div>
            )}
          </div>
        </main>
      </div>

      {/* ── Status bar ─────────────────────────────────────────── */}
      <StatusBar
        dark={dark}
        onToggleDark={() => setDark((d) => !d)}
        status={status}
        totalScenes={totalScenes}
        results={results}
        startTime={startTime}
      />
    </div>
  );
}
