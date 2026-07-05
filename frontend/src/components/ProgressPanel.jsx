// src/components/ProgressPanel.jsx
// Circular SVG progress ring + "Scene X of Y" centre text +
// current scene timestamp + status message.

import { useMemo } from 'react';

const SIZE   = 180;
const STROKE = 12;
const R      = (SIZE - STROKE) / 2;
const CIRCUM = 2 * Math.PI * R;

function statusText(status, currentScene, totalScenes) {
  if (status === 'idle')     return 'Upload a video to begin';
  if (status === 'error')    return '⚠ Pipeline error';
  if (status === 'complete') return '✓ All scenes captioned!';
  // processing + no WS message yet → scene detection hasn't reported back
  if (totalScenes === 0)     return 'Starting pipeline…';
  // processing + scenes known but none being captioned yet → detection phase
  if (currentScene === 0)    return 'Detecting scenes…';
  return `Captioning scene ${currentScene}…`;
}


function ringColor(status) {
  if (status === 'complete') return '#22c55e';
  if (status === 'error')    return '#ef4444';
  return 'url(#progressGradient)';
}

export default function ProgressPanel({
  dark,
  status,
  progress,
  currentScene,
  totalScenes,
  currentTimestamp,
}) {
  const offset = useMemo(
    () => CIRCUM - (progress / 100) * CIRCUM,
    [progress],
  );

  const c = {
    wrap: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 16,
      padding: '24px 20px',
      background: dark ? '#1a1a1a' : '#ffffff',
      borderRadius: 20,
      flexShrink: 0,
    },
    title: {
      fontSize: 11,
      fontWeight: 700,
      letterSpacing: '0.1em',
      textTransform: 'uppercase',
      color: dark ? '#52525b' : '#9ca3af',
      alignSelf: 'flex-start',
    },
    centreLabel: {
      fontSize: 13,
      fontWeight: 600,
      color: dark ? '#a1a1aa' : '#6b7280',
      marginTop: 2,
    },
    bigNum: {
      fontSize: 36,
      fontWeight: 800,
      color: dark ? '#ffffff' : '#111827',
      lineHeight: 1,
    },
    statusMsg: {
      fontSize: 13,
      fontWeight: 500,
      color: dark ? '#a1a1aa' : '#6b7280',
      textAlign: 'center',
      minHeight: 20,
    },
    timestamp: {
      fontFamily: 'monospace',
      fontSize: 12,
      color: dark ? '#6366f1' : '#4f46e5',
      background: dark ? '#1e1e2e' : '#eef2ff',
      padding: '4px 12px',
      borderRadius: 99,
      display: currentTimestamp ? 'block' : 'none',
    },
    pct: {
      fontSize: 11,
      color: dark ? '#52525b' : '#9ca3af',
    },
  };

  return (
    <div style={c.wrap}>
      <span style={c.title}>Progress</span>

      {/* SVG ring */}
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
        <defs>
          <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%"   stopColor="#6366f1" />
            <stop offset="100%" stopColor="#a855f7" />
          </linearGradient>
        </defs>

        {/* Track */}
        <circle
          cx={SIZE / 2} cy={SIZE / 2} r={R}
          fill="none"
          stroke={dark ? '#27272a' : '#e5e7eb'}
          strokeWidth={STROKE}
        />

        {/* Progress arc */}
        <circle
          cx={SIZE / 2} cy={SIZE / 2} r={R}
          fill="none"
          stroke={ringColor(status)}
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={CIRCUM}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}
          style={{ transition: 'stroke-dashoffset 0.6s cubic-bezier(0.4,0,0.2,1)' }}
        />

        {/* Centre text */}
        <text
          x="50%" y="44%"
          textAnchor="middle" dominantBaseline="middle"
          fontSize={status === 'complete' ? 28 : 32}
          fontWeight={800}
          fill={dark ? '#ffffff' : '#111827'}
        >
          {status === 'complete' ? '✓' : `${Math.round(progress)}%`}
        </text>

        <text
          x="50%" y="63%"
          textAnchor="middle" dominantBaseline="middle"
          fontSize={12}
          fontWeight={600}
          fill={dark ? '#71717a' : '#9ca3af'}
        >
          {totalScenes > 0
            ? `${currentScene || (status === 'complete' ? totalScenes : 0)} / ${totalScenes} scenes`
            : 'No video loaded'}
        </text>
      </svg>

      {/* Status message */}
      <p style={c.statusMsg}>
        {statusText(status, currentScene, totalScenes)}
      </p>

      {/* Current timestamp pill */}
      <span style={c.timestamp}>{currentTimestamp}</span>
    </div>
  );
}
