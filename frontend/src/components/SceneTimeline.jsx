export default function SceneTimeline({ totalScenes, currentScene, results }) {
  if (!totalScenes || totalScenes === 0) return null;

  const s = {
    container: {
      width: '100%',
      marginBottom: 24,
    },
    header: {
      display: 'flex',
      justifyContent: 'space-between',
      fontSize: 13,
      fontWeight: 600,
      color: 'var(--text-secondary)',
      marginBottom: 8,
    },
    bar: {
      display: 'flex',
      height: 12,
      background: 'var(--surface-elevated)',
      borderRadius: 6,
      overflow: 'hidden',
      gap: 2, // 2px gap between segments
    },
    segment: (status) => {
      let bg = 'transparent';
      let anim = 'none';
      if (status === 'complete') bg = 'var(--success)';
      else if (status === 'processing') {
        bg = 'var(--accent-primary)';
        anim = 'pulse 1.5s infinite';
      } else {
        bg = 'var(--border)';
      }

      return {
        flex: 1,
        background: bg,
        animation: anim,
        transition: 'background 0.3s ease',
      };
    }
  };

  const segments = [];
  for (let i = 1; i <= totalScenes; i++) {
    const isComplete = results.some(r => r.scene === i);
    const isProcessing = currentScene === i;
    
    let status = 'pending';
    if (isComplete) status = 'complete';
    else if (isProcessing) status = 'processing';

    segments.push(<div key={i} style={s.segment(status)} title={`Scene ${i}: ${status}`} />);
  }

  return (
    <div style={s.container}>
      <div style={s.header}>
        <span>Timeline Overview</span>
        <span>{results.length} / {totalScenes} Scenes</span>
      </div>
      <div style={s.bar}>
        {segments}
      </div>
    </div>
  );
}
