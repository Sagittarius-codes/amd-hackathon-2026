// src/components/StatusBar.jsx
// Shows scene counts, successful captions, live elapsed timer, and
// the dark/light mode toggle button.

import { useEffect, useState } from 'react';
import { Sun, Moon, CheckCircle, Film, Clock } from 'lucide-react';

function formatElapsed(ms) {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const ss = s % 60;
  return m > 0 ? `${m}m ${ss.toString().padStart(2, '0')}s` : `${ss}s`;
}

export default function StatusBar({ dark, onToggleDark, status, totalScenes, results, startTime }) {
  const [elapsed, setElapsed] = useState(0);

  // Live timer — ticks while processing
  useEffect(() => {
    if (!startTime) { setElapsed(0); return; }
    const iv = setInterval(() => setElapsed(Date.now() - startTime), 1000);
    return () => clearInterval(iv);
  }, [startTime]);

  const successful = results.filter(
    (r) => Object.values(r.captions || {}).some((v) => v !== '[no caption]'),
  ).length;

  const c = {
    bar: {
      display: 'flex',
      alignItems: 'center',
      gap: 16,
      padding: '14px 20px',
      background: dark ? '#111111' : '#f9fafb',
      borderTop: `1.5px solid ${dark ? '#1f1f1f' : '#e5e7eb'}`,
      flexWrap: 'wrap',
    },
    stat: {
      display: 'flex',
      alignItems: 'center',
      gap: 6,
      fontSize: 12,
      fontWeight: 600,
      color: dark ? '#71717a' : '#6b7280',
    },
    statValue: {
      color: dark ? '#e4e4e7' : '#111827',
    },
    divider: {
      width: 1,
      height: 16,
      background: dark ? '#27272a' : '#e5e7eb',
    },
    toggle: {
      marginLeft: 'auto',
      display: 'flex',
      alignItems: 'center',
      gap: 6,
      padding: '7px 14px',
      borderRadius: 99,
      background: dark ? '#27272a' : '#e5e7eb',
      color: dark ? '#e4e4e7' : '#374151',
      fontSize: 12,
      fontWeight: 600,
      border: 'none',
      cursor: 'pointer',
      transition: 'background 0.2s',
    },
  };

  return (
    <div style={c.bar}>
      <div style={c.stat}>
        <Film size={14} color="#6366f1" />
        Scenes detected:&nbsp;
        <span style={c.statValue}>{totalScenes || 0}</span>
      </div>

      <div style={c.divider} />

      <div style={c.stat}>
        <CheckCircle size={14} color="#22c55e" />
        Captioned:&nbsp;
        <span style={c.statValue}>{successful}</span>
        {totalScenes > 0 && (
          <span style={{ color: dark ? '#52525b' : '#9ca3af', fontWeight: 400 }}>
            &nbsp;/ {totalScenes}
          </span>
        )}
      </div>

      <div style={c.divider} />

      <div style={c.stat}>
        <Clock size={14} color="#f59e0b" />
        Elapsed:&nbsp;
        <span style={c.statValue}>
          {startTime ? formatElapsed(elapsed) : '—'}
        </span>
      </div>

      <button style={c.toggle} onClick={onToggleDark}>
        {dark
          ? <><Sun size={14} /> Light mode</>
          : <><Moon size={14} /> Dark mode</>
        }
      </button>
    </div>
  );
}
