import { useState } from 'react';
import { Copy, Check, Film } from 'lucide-react';

const TABS = [
  { key: 'formal', label: 'Formal' },
  { key: 'sarcastic', label: 'Sarcastic' },
  { key: 'humorous_tech', label: 'Humor-Tech' },
  { key: 'humorous_non_tech', label: 'Humor-Non-Tech' },
];

export default function SceneCard({ result, isProcessing }) {
  const [activeTab, setActiveTab] = useState('formal');
  const [copied, setCopied] = useState(false);

  // Note: if result is just a stub indicating pending/processing without full data, 
  // we handle it. But the WS sends `caption_result` only when complete.
  // Wait, the prompt says "Card states: Pending: reduced opacity... Processing: accent border, pulsing shadow... Complete: normal opacity".
  // This implies we have placeholders for all scenes based on `totalScenes` and we pass `result` or `isProcessing`.
  
  const { scene, captions, frame_info } = result || { scene: '?', captions: {} };
  
  // Calculate per-scene progress based on how many caption styles are present
  // Assuming 4 styles total. If the backend sends them all at once at the end, 
  // it will jump 0 -> 100%. If it streams, it will increment. 
  // The current backend sends them all at once in `caption_result`, but we build the UI 
  // to support partials per the prompt: "increments by 25% per caption style received"
  const completedStylesCount = Object.keys(captions || {}).filter(k => captions[k] && captions[k] !== '[no caption]').length;
  const progressPct = isProcessing ? (completedStylesCount / 4) * 100 : (result ? 100 : 0);

  const isPending = !result && !isProcessing;
  const isComplete = !!result && !isProcessing;

  const rawCaption = captions?.[activeTab];
  const isMissing = !rawCaption || rawCaption === '[no caption]';
  const displayCaption = isMissing ? 'Caption unavailable' : rawCaption;

  const handleCopy = () => {
    const attemptFallback = () => {
      try {
        const ta = document.createElement('textarea');
        ta.value = displayCaption;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        setCopied(true);
        setTimeout(() => setCopied(false), 1800);
      } catch (e) {
        console.error('Copy failed:', e);
      }
    };

    if (navigator.clipboard) {
      navigator.clipboard.writeText(displayCaption).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1800);
      }).catch(attemptFallback);
    } else {
      attemptFallback();
    }
  };

  const s = {
    card: {
      background: 'var(--surface)',
      borderRadius: 16,
      overflow: 'hidden',
      border: isComplete 
        ? '1.5px solid var(--border)' 
        : isProcessing 
          ? '1.5px solid var(--accent-primary)' 
          : '1.5px solid var(--border)',
      boxShadow: isProcessing 
        ? '0 0 20px rgba(194, 98, 42, 0.15)' 
        : '0 4px 12px rgba(0,0,0,0.05)',
      animation: isProcessing ? 'pulse 2s infinite' : 'fadeSlideIn 0.35s ease both',
      opacity: isPending ? 0.6 : 1,
      display: 'flex',
      flexDirection: 'column',
      transition: 'all 0.3s ease',
    },
    thumbnailWrap: {
      height: 160,
      position: 'relative',
      background: 'linear-gradient(135deg, #111, #222)',
      borderBottom: isComplete ? '2px solid var(--success)' : 'none',
    },
    thumbnailContent: {
      position: 'absolute',
      inset: 0,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      color: '#888',
      zIndex: 2,
    },
    sceneNum: {
      fontSize: 32,
      fontWeight: 800,
      color: '#ddd',
      lineHeight: 1.2,
      marginTop: 8,
    },
    timestamp: {
      fontSize: 12,
      fontFamily: 'monospace',
      color: '#aaa',
      marginTop: 4,
      background: 'rgba(0,0,0,0.4)',
      padding: '2px 8px',
      borderRadius: 4,
    },
    shimmer: {
      position: 'absolute',
      inset: 0,
      background: 'linear-gradient(90deg, transparent 25%, rgba(255,255,255,0.05) 50%, transparent 75%)',
      backgroundSize: '400% 100%',
      animation: 'shimmer 2s infinite linear',
      zIndex: 1,
      display: isProcessing ? 'block' : 'none',
    },
    progressBarWrap: {
      height: 4,
      background: 'var(--surface-elevated)',
      width: '100%',
    },
    progressBar: {
      height: '100%',
      background: 'var(--accent-primary)',
      width: `${progressPct}%`,
      transition: 'width 400ms ease-out',
    },
    body: {
      padding: 16,
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
    },
    tabs: {
      display: 'flex',
      gap: 16,
      marginBottom: 16,
      borderBottom: '1px solid var(--border)',
    },
    tabBtn: (isActive) => ({
      padding: '8px 4px',
      fontSize: 13,
      fontWeight: 600,
      color: isActive ? 'var(--accent-primary)' : 'var(--text-muted)',
      borderBottom: isActive ? '2px solid var(--accent-primary)' : '2px solid transparent',
      transition: 'all 0.15s ease',
      marginBottom: -1,
    }),
    captionArea: {
      position: 'relative',
      background: 'var(--surface-elevated)',
      padding: '16px',
      borderRadius: 12,
      flex: 1,
    },
    captionText: {
      fontSize: 14,
      lineHeight: 1.6,
      color: isMissing ? 'var(--text-muted)' : 'var(--text-primary)',
      fontStyle: isMissing ? 'italic' : 'normal',
      paddingRight: 24, // space for copy icon
    },
    copyBtn: {
      position: 'absolute',
      top: 12,
      right: 12,
      color: copied ? 'var(--success)' : 'var(--text-muted)',
      transition: 'color 0.2s',
      cursor: isMissing ? 'default' : 'pointer',
      opacity: isMissing ? 0 : 1,
      pointerEvents: isMissing ? 'none' : 'auto',
    }
  };

  return (
    <div style={s.card}>
      <div style={s.thumbnailWrap}>
        <div style={s.thumbnailContent}>
          <Film size={28} />
          <div style={s.sceneNum}>Scene {scene}</div>
          <div style={s.timestamp}>
            {frame_info?.scene_start_str ? `${frame_info.scene_start_str} → ${frame_info.scene_end_str}` : 'Waiting...'}
          </div>
        </div>
        <div style={s.shimmer} />
      </div>

      <div style={s.progressBarWrap}>
        <div style={s.progressBar} />
      </div>

      <div style={s.body}>
        <div style={s.tabs}>
          {TABS.map(({ key, label }) => (
            <button 
              key={key} 
              style={s.tabBtn(activeTab === key)} 
              onClick={() => setActiveTab(key)}
              disabled={isPending}
            >
              {label}
            </button>
          ))}
        </div>

        <div style={s.captionArea}>
          <div style={s.captionText}>{displayCaption}</div>
          <button style={s.copyBtn} onClick={handleCopy} title="Copy caption">
            {copied ? <Check size={16} /> : <Copy size={16} />}
          </button>
        </div>
      </div>
    </div>
  );
}
