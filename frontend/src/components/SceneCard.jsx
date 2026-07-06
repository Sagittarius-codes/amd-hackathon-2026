import { useState } from 'react';
import { Copy, Check, Clapperboard, CheckCircle } from 'lucide-react';

const TABS = [
  { key: 'formal', label: 'Formal' },
  { key: 'sarcastic', label: 'Sarcastic' },
  { key: 'humorous_tech', label: 'Humor-Tech' },
  { key: 'humorous_non_tech', label: 'Humor-Non-Tech' },
];

const parseTime = (timeStr) => {
  if (!timeStr) return 0;
  const parts = timeStr.split(':');
  if (parts.length !== 3) return 0;
  const secParts = parts[2].split('.');
  return (parseInt(parts[0], 10) * 3600) + 
         (parseInt(parts[1], 10) * 60) + 
         parseInt(secParts[0], 10) + 
         (secParts[1] ? parseInt(secParts[1], 10) / 1000 : 0);
};

export default function SceneCard({ scene, isProcessing }) {
  console.log('SceneCard props.scene:', scene);
  const [activeTab, setActiveTab] = useState('formal');
  const [copied, setCopied] = useState(false);

  // Parse websocket payload structure
  const sceneNumber = scene?.scene_number || '?';
  const captions = scene?.captions || {};
  const sceneStart = scene?.scene_start_str;
  const sceneEnd = scene?.scene_end_str;
  
  let durationStr = '';
  if (sceneStart && sceneEnd) {
    const duration = parseTime(sceneEnd) - parseTime(sceneStart);
    durationStr = `${duration.toFixed(1)}s`;
  }

  const completedStylesCount = Object.keys(captions || {}).filter(k => captions[k] && captions[k] !== '[no caption]').length;
  // If scene has captions, it's processed. We check Object.keys(captions).length
  const progressPct = isProcessing ? (completedStylesCount / 4) * 100 : (Object.keys(captions).length > 0 ? 100 : 0);

  const isPending = Object.keys(captions).length === 0 && !isProcessing;
  const isComplete = Object.keys(captions).length > 0 && !isProcessing;

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
      position: 'relative',
    },
    thumbnailWrap: {
      height: 160,
      position: 'relative',
      background: 'linear-gradient(135deg, #2A1F15 0%, #1A1D27 60%, #0F1117 100%)',
      borderBottom: isComplete ? '2px solid var(--success)' : 'none',
      overflow: 'hidden',
    },
    topLeftIcon: {
      position: 'absolute',
      top: 12,
      left: 12,
      color: '#fff',
      opacity: 0.4,
      zIndex: 2,
    },
    successBadge: {
      position: 'absolute',
      top: 12,
      right: 12,
      color: 'var(--success)',
      zIndex: 2,
    },
    durationBadge: {
      position: 'absolute',
      bottom: 12,
      right: 12,
      background: 'rgba(0,0,0,0.6)',
      color: '#ddd',
      fontSize: 11,
      fontWeight: 600,
      padding: '4px 8px',
      borderRadius: 99,
      zIndex: 2,
    },
    thumbnailContent: {
      position: 'absolute',
      inset: 0,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 2,
    },
    sceneNum: {
      fontSize: 28,
      fontWeight: 800,
      color: '#fff',
      lineHeight: 1.2,
      textShadow: '0 2px 4px rgba(0,0,0,0.5)',
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
    filmStripLeft: {
      position: 'absolute',
      top: 0, left: 4, bottom: 0,
      display: 'flex', flexDirection: 'column', justifyContent: 'space-evenly',
      zIndex: 1,
    },
    filmStripRight: {
      position: 'absolute',
      top: 0, right: 4, bottom: 0,
      display: 'flex', flexDirection: 'column', justifyContent: 'space-evenly',
      zIndex: 1,
    },
    perf: {
      width: 4, height: 12,
      background: 'rgba(0,0,0,0.4)',
      borderRadius: 2,
    },
    shimmer: {
      position: 'absolute',
      inset: 0,
      background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.1) 50%, transparent 100%)',
      backgroundSize: '200% 100%',
      animation: 'shimmerThumbnail 1.5s infinite linear',
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

  const perfs = Array(5).fill(0).map((_, i) => <div key={i} style={s.perf} />);

  return (
    <div style={s.card}>
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes shimmerThumbnail {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}} />
      <div style={s.thumbnailWrap}>
        <div style={s.filmStripLeft}>{perfs}</div>
        <div style={s.filmStripRight}>{perfs}</div>
        
        <div style={s.topLeftIcon}><Clapperboard size={36} /></div>
        {isComplete && <div style={s.successBadge}><CheckCircle size={20} /></div>}
        {durationStr && <div style={s.durationBadge}>{durationStr}</div>}
        
        <div style={s.thumbnailContent}>
          <div style={s.sceneNum}>Scene {sceneNumber}</div>
          <div style={s.timestamp}>
            {sceneStart ? `${sceneStart} → ${sceneEnd}` : 'Waiting...'}
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
