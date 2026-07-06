import { Moon, Sun, Clapperboard, CheckCircle } from 'lucide-react';
import LeftPanel from './LeftPanel';
import SceneTimeline from './SceneTimeline';
import SceneCard from './SceneCard';

export default function Dashboard({ 
  theme, toggleTheme, uploadedFile, 
  status, progress, currentScene, totalScenes, results,
  wsConnected, startTime
}) {

  const s = {
    dashboard: {
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      width: '100%',
    },
    topBar: {
      height: 64,
      background: 'var(--surface)',
      borderBottom: '1px solid var(--border)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
      flexShrink: 0,
    },
    topLeft: {
      display: 'flex',
      alignItems: 'center',
      gap: 12,
    },
    logoWrap: {
      width: 32, height: 32,
      background: 'var(--accent-primary)',
      borderRadius: 8,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      color: 'white',
    },
    appName: {
      fontSize: 18,
      fontWeight: 800,
      color: 'var(--text-primary)',
      letterSpacing: '-0.5px',
    },
    topCenter: {
      fontSize: 12,
      color: 'var(--text-muted)',
      fontWeight: 500,
    },
    topRight: {
      display: 'flex',
      alignItems: 'center',
    },
    themeBtn: {
      padding: 8,
      borderRadius: 8,
      color: 'var(--text-secondary)',
      background: 'var(--surface-elevated)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      transition: 'all 0.2s',
    },
    mainBody: {
      display: 'flex',
      flex: 1,
      overflow: 'hidden',
    },
    contentArea: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      padding: '24px',
      overflowY: 'auto',
    },
    grid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
      gap: 24,
      marginTop: 24,
    },
    successOverlay: {
      background: 'var(--surface-elevated)',
      padding: '24px',
      borderRadius: 16,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 12,
      color: 'var(--success)',
      fontSize: 20,
      fontWeight: 700,
      marginBottom: 24,
      border: '2px solid var(--success)',
      animation: 'fadeSlideIn 0.5s ease-out forwards',
    }
  };

  // Create an array of placeholder scenes to render all cards, 
  // replacing them with real result data as it arrives
  const cards = [];
  for (let i = 1; i <= totalScenes; i++) {
    const result = results.find(r => r.scene === i);
    cards.push(
      <SceneCard 
        key={i} 
        result={result} 
        isProcessing={currentScene === i} 
      />
    );
  }

  return (
    <div style={s.dashboard} className="animate-fade-slide-in">
      <div style={s.topBar}>
        <div style={s.topLeft}>
          <div style={s.logoWrap}><Clapperboard size={18} /></div>
          <div style={s.appName}>CaptionAI</div>
        </div>
        <div style={s.topCenter}>
          by Sagittarius Codes
        </div>
        <div style={s.topRight}>
          <button style={s.themeBtn} onClick={toggleTheme} title="Toggle Theme">
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>
      </div>

      <div style={s.mainBody}>
        <LeftPanel 
          uploadedFile={uploadedFile}
          status={status}
          progress={progress}
          totalScenes={totalScenes}
          resultsCount={results.length}
          wsConnected={wsConnected}
          startTime={startTime}
        />

        <div style={s.contentArea}>
          {status === 'complete' && (
            <div style={s.successOverlay}>
              <CheckCircle size={28} />
              Pipeline complete · Sagittarius Codes
            </div>
          )}

          <SceneTimeline 
            totalScenes={totalScenes} 
            currentScene={currentScene} 
            results={results} 
          />
          
          <div style={s.grid}>
            {cards}
          </div>
        </div>
      </div>
    </div>
  );
}
