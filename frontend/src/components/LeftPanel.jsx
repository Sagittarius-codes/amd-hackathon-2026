import { useEffect, useState } from 'react';
import { Film, Activity, CheckCircle2, Clock } from 'lucide-react';

function formatTime(ms) {
  if (!ms || ms < 0) return '00:00';
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

export default function LeftPanel({
  uploadedFile,
  status,
  progress,
  totalScenes,
  resultsCount,
  wsConnected,
  startTime
}) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    let interval;
    if (status === 'processing' && startTime) {
      interval = setInterval(() => {
        setElapsed(Date.now() - startTime);
      }, 1000);
    } else if (status === 'complete') {
      // Freeze timer
      if (startTime) setElapsed(Date.now() - startTime);
    }
    return () => clearInterval(interval);
  }, [status, startTime]);

  const pendingCount = Math.max(0, totalScenes - resultsCount);
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  const s = {
    panel: {
      width: 280,
      background: 'var(--surface)',
      borderRight: '1.5px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      padding: '24px 20px',
      flexShrink: 0,
      overflowY: 'auto',
    },
    section: {
      marginBottom: 32,
    },
    sectionTitle: {
      fontSize: 12,
      fontWeight: 700,
      color: 'var(--text-muted)',
      textTransform: 'uppercase',
      letterSpacing: '0.1em',
      marginBottom: 16,
    },
    fileCard: {
      background: 'var(--surface-elevated)',
      borderRadius: 12,
      padding: 16,
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      border: '1px solid var(--border)',
    },
    fileName: {
      fontSize: 13,
      fontWeight: 600,
      color: 'var(--text-primary)',
      whiteSpace: 'nowrap',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      maxWidth: 160,
    },
    fileSize: {
      fontSize: 12,
      color: 'var(--text-muted)',
    },
    ringContainer: {
      position: 'relative',
      width: 140,
      height: 140,
      margin: '0 auto 24px',
    },
    svg: {
      transform: 'rotate(-90deg)',
      width: '100%',
      height: '100%',
    },
    ringBg: {
      fill: 'none',
      stroke: 'var(--surface-elevated)',
      strokeWidth: 12,
    },
    ringProgress: {
      fill: 'none',
      stroke: status === 'complete' ? 'var(--success)' : 'var(--accent-primary)',
      strokeWidth: 12,
      strokeLinecap: 'round',
      strokeDasharray: circumference,
      strokeDashoffset,
      transition: 'stroke-dashoffset 0.5s ease-out',
    },
    ringText: {
      position: 'absolute',
      inset: 0,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
    },
    ringCount: {
      fontSize: 24,
      fontWeight: 800,
      color: 'var(--text-primary)',
    },
    ringLabel: {
      fontSize: 11,
      fontWeight: 600,
      color: 'var(--text-muted)',
      textTransform: 'uppercase',
    },
    linearBarWrap: {
      height: 6,
      background: 'var(--surface-elevated)',
      borderRadius: 99,
      overflow: 'hidden',
      marginBottom: 8,
    },
    linearBar: {
      height: '100%',
      background: status === 'complete' ? 'var(--success)' : 'var(--accent-primary)',
      width: `${progress}%`,
      transition: 'width 0.5s ease-out',
    },
    pctText: {
      textAlign: 'center',
      fontSize: 13,
      fontWeight: 600,
      color: 'var(--text-secondary)',
    },
    statsGrid: {
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
    },
    statPill: (color) => ({
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      background: 'var(--surface-elevated)',
      padding: '12px 16px',
      borderRadius: 12,
      borderLeft: `4px solid ${color}`,
    }),
    statLabel: {
      fontSize: 13,
      fontWeight: 600,
      color: 'var(--text-secondary)',
    },
    statValue: {
      fontSize: 16,
      fontWeight: 800,
      color: 'var(--text-primary)',
    },
    statusIndicator: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      fontSize: 13,
      fontWeight: 500,
      color: 'var(--text-secondary)',
      marginTop: 'auto', // push to bottom
      paddingTop: 24,
    },
    wsDot: {
      width: 8, height: 8,
      borderRadius: '50%',
      background: wsConnected ? 'var(--success)' : 'var(--error)',
      boxShadow: wsConnected ? '0 0 8px var(--success)' : 'none',
      animation: wsConnected ? 'none' : 'pulse 1.5s infinite',
    }
  };

  return (
    <div style={s.panel}>
      {uploadedFile && (
        <div style={s.section}>
          <div style={s.sectionTitle}>Source Video</div>
          <div style={s.fileCard}>
            <Film size={20} color="var(--accent-primary)" />
            <div>
              <div style={s.fileName} title={uploadedFile.name}>{uploadedFile.name}</div>
              <div style={s.fileSize}>{(uploadedFile.size / (1024*1024)).toFixed(1)} MB</div>
            </div>
          </div>
        </div>
      )}

      <div style={s.section}>
        <div style={s.sectionTitle}>Pipeline Progress</div>
        
        <div style={s.ringContainer}>
          <svg style={s.svg}>
            <circle cx="70" cy="70" r={radius} style={s.ringBg} />
            <circle cx="70" cy="70" r={radius} style={s.ringProgress} />
          </svg>
          <div style={s.ringText}>
            <div style={s.ringCount}>{resultsCount}/{totalScenes || '-'}</div>
            <div style={s.ringLabel}>Scenes</div>
          </div>
        </div>

        <div style={s.linearBarWrap}>
          <div style={s.linearBar} />
        </div>
        <div style={s.pctText}>{Math.round(progress)}% Complete</div>
      </div>

      <div style={s.section}>
        <div style={s.sectionTitle}>Statistics</div>
        <div style={s.statsGrid}>
          <div style={s.statPill('var(--accent-primary)')}>
            <span style={s.statLabel}>Detected</span>
            <span style={s.statValue}>{totalScenes}</span>
          </div>
          <div style={s.statPill('var(--success)')}>
            <span style={s.statLabel}>Captioned</span>
            <span style={s.statValue}>{resultsCount}</span>
          </div>
          <div style={s.statPill('var(--text-muted)')}>
            <span style={s.statLabel}>Pending</span>
            <span style={s.statValue}>{pendingCount}</span>
          </div>
          <div style={s.statPill('var(--border)')}>
            <span style={s.statLabel}><Clock size={14} style={{display:'inline', verticalAlign:'middle', marginRight:6}}/>Elapsed</span>
            <span style={s.statValue}>{formatTime(elapsed)}</span>
          </div>
        </div>
      </div>

      <div style={s.statusIndicator}>
        <div style={s.wsDot} />
        {wsConnected ? 'Backend Connected' : 'Connecting...'}
      </div>
    </div>
  );
}
