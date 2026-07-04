// src/components/Timeline.jsx
// Horizontal bar of scene segments: gray=pending, blue=active, green=done.
// Hover tooltip shows scene number and timestamp.

import { useState } from 'react';

function segmentColor(state, dark) {
  if (state === 'done')       return '#22c55e';
  if (state === 'processing') return '#6366f1';
  return dark ? '#27272a' : '#e5e7eb';
}

export default function Timeline({ dark, scenes, results, currentScene }) {
  const [tooltip, setTooltip] = useState(null); // { x, y, scene }

  if (!scenes || scenes.length === 0) {
    return (
      <div style={{
        background: dark ? '#1a1a1a' : '#ffffff',
        borderRadius: 16,
        padding: '20px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: 80,
      }}>
        <p style={{ fontSize: 13, color: dark ? '#52525b' : '#9ca3af' }}>
          Scene timeline will appear here after detection
        </p>
      </div>
    );
  }

  const doneSet = new Set(results.map((r) => r.scene));

  return (
    <div style={{
      background: dark ? '#1a1a1a' : '#ffffff',
      borderRadius: 16,
      padding: '20px 24px',
      position: 'relative',
    }}>
      <p style={{
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: '0.1em',
        textTransform: 'uppercase',
        color: dark ? '#52525b' : '#9ca3af',
        marginBottom: 12,
      }}>
        Scene Timeline — {scenes.length} scenes
      </p>

      {/* Bar */}
      <div style={{
        display: 'flex',
        gap: 2,
        height: 28,
        borderRadius: 8,
        overflow: 'hidden',
      }}>
        {scenes.map((scene, i) => {
          const sceneNum = scene.scene_number || (i + 1);
          const state = doneSet.has(sceneNum)
            ? 'done'
            : sceneNum === currentScene
            ? 'processing'
            : 'pending';

          return (
            <div
              key={sceneNum}
              style={{
                flex: 1,
                background: segmentColor(state, dark),
                borderRadius: 4,
                transition: 'background 0.4s ease',
                cursor: 'pointer',
                position: 'relative',
              }}
              onMouseEnter={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const parentRect = e.currentTarget.closest('[data-timeline]')?.getBoundingClientRect();
                setTooltip({
                  x: rect.left - (parentRect?.left || 0) + rect.width / 2,
                  scene: sceneNum,
                  ts: scene.timestamp_str || scene.scene_start_str || '',
                });
              }}
              onMouseLeave={() => setTooltip(null)}
            />
          );
        })}
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div style={{
          position: 'absolute',
          bottom: 68,
          left: Math.max(40, Math.min(tooltip.x, scenes.length > 0 ? scenes.length * 10 : 200)),
          transform: 'translateX(-50%)',
          background: dark ? '#3f3f46' : '#111827',
          color: '#fff',
          fontSize: 11,
          fontWeight: 600,
          padding: '5px 10px',
          borderRadius: 6,
          whiteSpace: 'nowrap',
          pointerEvents: 'none',
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          zIndex: 10,
        }}>
          Scene {tooltip.scene}
          {tooltip.ts && ` · ${tooltip.ts}`}
        </div>
      )}

      {/* Legend */}
      <div style={{
        display: 'flex',
        gap: 16,
        marginTop: 10,
      }}>
        {[
          { color: dark ? '#27272a' : '#e5e7eb', label: 'Pending' },
          { color: '#6366f1', label: 'Processing' },
          { color: '#22c55e', label: 'Done' },
        ].map(({ color, label }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: color, display: 'inline-block' }} />
            <span style={{ fontSize: 11, color: dark ? '#52525b' : '#9ca3af' }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
