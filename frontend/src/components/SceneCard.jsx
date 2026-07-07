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
      borderRadius: 20,
      overflow: 'hidden',
      border: isComplete 
        ? '1px solid rgba(16, 185, 129, 0.3)' // Subtle green border if complete
        : isProcessing 
          ? '1px solid rgba(194, 98, 42, 0.5)' // Accent primary glow
          : '1px solid var(--border)',
      boxShadow: isProcessing 
        ? '0 12px 32px rgba(194, 98, 42, 0.2)' 
        : '0 8px 24px rgba(0,0,0,0.04)',
      animation: 'fadeSlideIn 0.35s ease both', // removed heavy pulse for subtle glow
      opacity: isPending ? 0.6 : 1,
      display: 'flex',
      flexDirection: 'column',
      transition: 'transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease',
      position: 'relative',
    },
    thumbnailWrap: {
      position: 'relative',
      background: 'linear-gradient(135deg, #1A1D27 0%, #0F1117 100%)',
      overflow: 'hidden',
    },
    topLeftIcon: {
      position: 'absolute',
      top: -20,
      left: -20,
      color: '#fff',
      opacity: 0.05,
      zIndex: 1,
      transform: 'rotate(-15deg)',
    },
    topBadges: {
      position: 'absolute',
      top: 12,
      right: 12,
      display: 'flex',
      gap: 8,
      zIndex: 3,
    },
    badgeSuccess: {
      background: 'rgba(16, 185, 129, 0.2)',
      backdropFilter: 'blur(8px)',
      border: '1px solid rgba(16, 185, 129, 0.3)',
      color: '#10b981',
      fontSize: 12,
      fontWeight: 600,
      padding: '4px 10px',
      borderRadius: 99,
      display: 'flex',
      alignItems: 'center',
      gap: 4,
    },
    sceneNumBadge: {
      position: 'absolute',
      bottom: 12,
      left: 12,
      background: 'rgba(0,0,0,0.4)',
      backdropFilter: 'blur(8px)',
      border: '1px solid rgba(255,255,255,0.1)',
      padding: '6px 12px',
      borderRadius: 10,
      zIndex: 3,
      display: 'flex',
      flexDirection: 'column',
    },
    sceneNumText: {
      fontSize: 15,
      fontWeight: 800,
      color: '#fff',
      letterSpacing: '0.5px',
    },
    timestampText: {
      fontSize: 11,
      fontFamily: 'monospace',
      color: 'rgba(255,255,255,0.6)',
      marginTop: 2,
    },
    durationBadge: {
      position: 'absolute',
      bottom: 12,
      right: 12,
      background: 'rgba(0,0,0,0.6)',
      backdropFilter: 'blur(4px)',
      color: '#ddd',
      fontSize: 11,
      fontWeight: 600,
      padding: '4px 8px',
      borderRadius: 8,
      zIndex: 3,
    },
    shimmer: {
      position: 'absolute',
      inset: 0,
      background: 'linear-gradient(105deg, transparent 20%, rgba(255,255,255,0.06) 50%, transparent 80%)',
      backgroundSize: '200% 100%',
      animation: 'shimmerThumbnail 2s infinite linear',
      zIndex: 2,
      display: isProcessing ? 'block' : 'none',
    },
    progressBarWrap: {
      height: 3,
      background: 'var(--surface-elevated)',
      width: '100%',
    },
    progressBar: {
      height: '100%',
      background: isComplete ? 'var(--success)' : 'var(--accent-primary)',
      width: `${progressPct}%`,
      transition: 'width 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
    },
    body: {
      padding: 20,
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
    },
    segmentedControl: {
      display: 'flex',
      background: 'var(--surface-elevated)',
      borderRadius: 10,
      padding: 4,
      marginBottom: 16,
      border: '1px solid var(--border)',
    },
    segmentBtn: (isActive) => ({
      flex: 1,
      padding: '6px 2px',
      fontSize: 12,
      fontWeight: 600,
      color: isActive ? 'var(--text-primary)' : 'var(--text-muted)',
      background: isActive ? 'var(--surface)' : 'transparent',
      borderRadius: 6,
      boxShadow: isActive ? '0 2px 6px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)' : 'none',
      border: isActive ? '1px solid var(--border)' : '1px solid transparent',
      transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
      minWidth: 0,
      position: 'relative',
      zIndex: isActive ? 2 : 1,
    }),
    captionArea: {
      position: 'relative',
      background: 'var(--surface-elevated)',
      padding: '16px',
      borderRadius: 12,
      flex: 1,
      border: '1px solid var(--border)',
      boxShadow: 'inset 0 2px 8px rgba(0,0,0,0.02)',
    },
    captionText: {
      fontSize: 14,
      lineHeight: 1.6,
      color: isMissing ? 'var(--text-muted)' : 'var(--text-primary)',
      fontStyle: isMissing ? 'italic' : 'normal',
      paddingRight: 28, // space for copy icon
    },
    copyBtn: {
      position: 'absolute',
      top: 12,
      right: 12,
      color: copied ? 'var(--success)' : 'var(--text-muted)',
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: 6,
      transition: 'all 0.2s ease',
      cursor: isMissing ? 'default' : 'pointer',
      opacity: isMissing ? 0 : 1,
      pointerEvents: isMissing ? 'none' : 'auto',
      boxShadow: '0 2px 4px rgba(0,0,0,0.04)',
    }
  };

  return (
    <div style={s.card} className="hover:-translate-y-1 hover:shadow-xl group">
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes shimmerThumbnail {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}} />
      <div style={s.thumbnailWrap} className="h-[140px] md:h-[180px]">
        <div style={s.topLeftIcon}><Clapperboard size={120} /></div>
        
        <div style={s.topBadges}>
          {isComplete && (
            <div style={s.badgeSuccess}>
              <CheckCircle size={14} /> Done
            </div>
          )}
        </div>

        <div style={s.sceneNumBadge}>
          <span style={s.sceneNumText}>Scene {sceneNumber}</span>
          <span style={s.timestampText}>
            {sceneStart ? `${sceneStart} → ${sceneEnd}` : 'Waiting...'}
          </span>
        </div>

        {durationStr && <div style={s.durationBadge}>{durationStr}</div>}
        
        <div style={s.shimmer} />
      </div>

      <div style={s.progressBarWrap}>
        <div style={s.progressBar} />
      </div>

      <div style={s.body}>
        <div style={s.segmentedControl}>
          {TABS.map(({ key, label }) => (
            <button 
              key={key} 
              style={s.segmentBtn(activeTab === key)} 
              className="truncate text-center"
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
