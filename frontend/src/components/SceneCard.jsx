// src/components/SceneCard.jsx
// Shows a scene's thumbnail placeholder, timestamps, 4 style tabs, caption,
// and a copy-to-clipboard button.

import { useState } from 'react';
import { Copy, Check, Film } from 'lucide-react';

const TABS = [
  { key: 'formal',           label: 'Formal' },
  { key: 'sarcastic',        label: 'Sarcastic' },
  { key: 'humorous_tech',    label: 'Humor-Tech' },
  { key: 'humorous_non_tech', label: 'Humor-Non-Tech' },
];

const TAB_COLORS = {
  formal:           { active: '#6366f1', bg: '#eef2ff', darkBg: '#1e1e3f' },
  sarcastic:        { active: '#f59e0b', bg: '#fffbeb', darkBg: '#2a2210' },
  humorous_tech:    { active: '#10b981', bg: '#ecfdf5', darkBg: '#0f2318' },
  humorous_non_tech:{ active: '#ec4899', bg: '#fdf2f8', darkBg: '#2a1020' },
};

export default function SceneCard({ dark, result }) {
  const [activeTab, setActiveTab] = useState('formal');
  const [copied, setCopied]       = useState(false);

  const { scene, captions, frame_info } = result;
  const caption  = captions?.[activeTab] || '[no caption]';
  const tabStyle = TAB_COLORS[activeTab];
  const isMissing = caption === '[no caption]';

  const handleCopy = () => {
    navigator.clipboard.writeText(caption).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    });
  };

  const c = {
    card: {
      background: dark ? '#1a1a1a' : '#ffffff',
      borderRadius: 16,
      overflow: 'hidden',
      border: `1.5px solid ${dark ? '#27272a' : '#f3f4f6'}`,
      boxShadow: dark
        ? '0 4px 24px rgba(0,0,0,0.4)'
        : '0 2px 12px rgba(0,0,0,0.07)',
      animation: 'fadeSlideIn 0.35s ease both',
    },
    thumbnail: {
      width: '100%',
      aspectRatio: '16/9',
      background: dark
        ? `linear-gradient(135deg, #1e1e2e 0%, #252540 100%)`
        : `linear-gradient(135deg, #e0e7ff 0%, #f5f3ff 100%)`,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 8,
      position: 'relative',
    },
    sceneNum: {
      fontSize: 28,
      fontWeight: 800,
      color: dark ? '#4f46e5' : '#6366f1',
      lineHeight: 1,
    },
    sceneLabel: {
      fontSize: 10,
      fontWeight: 700,
      letterSpacing: '0.12em',
      textTransform: 'uppercase',
      color: dark ? '#52525b' : '#9ca3af',
    },
    timeRange: {
      position: 'absolute',
      bottom: 8, left: 10,
      fontSize: 10,
      fontFamily: 'monospace',
      background: 'rgba(0,0,0,0.55)',
      color: '#fff',
      padding: '2px 7px',
      borderRadius: 4,
    },
    body: {
      padding: '14px 16px',
    },
    tabs: {
      display: 'flex',
      gap: 4,
      marginBottom: 12,
      flexWrap: 'wrap',
    },
    tabBtn: (key) => ({
      padding: '5px 10px',
      borderRadius: 8,
      fontSize: 11,
      fontWeight: 600,
      border: 'none',
      cursor: 'pointer',
      transition: 'all 0.15s',
      background: activeTab === key
        ? TAB_COLORS[key].active
        : dark ? '#27272a' : '#f3f4f6',
      color: activeTab === key
        ? '#ffffff'
        : dark ? '#71717a' : '#6b7280',
    }),
    captionBox: {
      background: dark ? tabStyle.darkBg : tabStyle.bg,
      borderRadius: 10,
      padding: '12px 14px',
      minHeight: 64,
      position: 'relative',
    },
    captionText: {
      fontSize: 13,
      lineHeight: 1.6,
      color: isMissing
        ? dark ? '#52525b' : '#9ca3af'
        : dark ? '#e4e4e7' : '#111827',
      fontStyle: isMissing ? 'italic' : 'normal',
      paddingRight: 28,
    },
    copyBtn: {
      position: 'absolute',
      top: 8, right: 8,
      padding: '4px',
      borderRadius: 6,
      background: 'transparent',
      color: copied ? '#22c55e' : dark ? '#52525b' : '#9ca3af',
      cursor: isMissing ? 'default' : 'pointer',
      transition: 'color 0.15s',
      display: 'flex',
    },
  };

  return (
    <div style={c.card}>
      {/* Thumbnail */}
      <div style={c.thumbnail}>
        <Film size={22} color={dark ? '#4f46e5' : '#6366f1'} />
        <span style={c.sceneNum}>{scene}</span>
        <span style={c.sceneLabel}>Scene</span>
        {frame_info?.scene_start_str && (
          <span style={c.timeRange}>
            {frame_info.scene_start_str} → {frame_info.scene_end_str}
          </span>
        )}
      </div>

      {/* Body */}
      <div style={c.body}>
        {/* Timestamp pill */}
        <div style={{
          fontFamily: 'monospace',
          fontSize: 11,
          color: dark ? '#6366f1' : '#4f46e5',
          marginBottom: 10,
        }}>
          {frame_info?.timestamp_str || '—'}
        </div>

        {/* Style tabs */}
        <div style={c.tabs}>
          {TABS.map(({ key, label }) => (
            <button key={key} style={c.tabBtn(key)} onClick={() => setActiveTab(key)}>
              {label}
            </button>
          ))}
        </div>

        {/* Caption box */}
        <div style={c.captionBox}>
          <p style={c.captionText}>{caption}</p>
          <button
            style={c.copyBtn}
            onClick={!isMissing ? handleCopy : undefined}
            title="Copy caption"
          >
            {copied
              ? <Check size={14} />
              : <Copy size={14} />
            }
          </button>
        </div>
      </div>
    </div>
  );
}
