import { Moon, Sun, Clapperboard, CheckCircle } from 'lucide-react';
import LeftPanel from './LeftPanel';
import SceneTimeline from './SceneTimeline';
import SceneCard from './SceneCard';

export default function Dashboard({ 
  theme, toggleTheme, uploadedFile, 
  status, progress, currentScene, totalScenes, results, scenes,
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
    },
    detectingState: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      animation: 'fadeSlideIn 0.5s ease-out',
    },
    pulsingFilm: {
      color: 'var(--accent-primary)',
      animation: 'pulse 1.5s infinite',
      marginBottom: 24,
    },
    detectingTitle: {
      fontSize: 22,
      fontWeight: 700,
      color: 'var(--text-primary)',
      marginBottom: 16,
    },
    indeterminateBarWrap: {
      width: 240,
      height: 4,
      background: 'var(--surface-elevated)',
      borderRadius: 99,
      overflow: 'hidden',
      position: 'relative',
      marginBottom: 12,
    },
    indeterminateBar: {
      position: 'absolute',
      top: 0, bottom: 0,
      width: '40%',
      background: 'var(--accent-primary)',
      borderRadius: 99,
      animation: 'slideBar 1.5s infinite ease-in-out',
    },
    detectingSubtext: {
      fontSize: 14,
      color: 'var(--text-muted)',
    }
  };

  const cards = [];
  if (scenes && scenes.length > 0) {
    scenes.forEach((s) => {
      const result = results.find(r => r.scene_number === s.scene_number || r.scene === s.scene_number);
      const mergedScene = { ...s, ...result };
      cards.push(
        <SceneCard 
          key={s.scene_number} 
          scene={mergedScene} 
          isProcessing={currentScene === s.scene_number} 
        />
      );
    });
  } else {
    for (let i = 1; i <= totalScenes; i++) {
      const result = results.find(r => r.scene_number === i || r.scene === i);
      cards.push(
        <SceneCard 
          key={i} 
          scene={result || { scene_number: i }} 
          isProcessing={currentScene === i} 
        />
      );
    }
  }

  const isDetecting = !totalScenes || totalScenes === 0;

  return (
    <div style={s.dashboard} className="animate-fade-slide-in">
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes slideBar {
          0% { left: -40%; }
          50% { left: 100%; }
          100% { left: -40%; }
        }
      `}} />
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

          {!isDetecting && (
            <SceneTimeline 
              totalScenes={totalScenes} 
              currentScene={currentScene} 
              results={results} 
            />
          )}
          
          {isDetecting ? (
            <div style={s.detectingState}>
              <div style={s.pulsingFilm}><Clapperboard size={64} /></div>
              <div style={s.detectingTitle}>Detecting scene boundaries...</div>
              <div style={s.indeterminateBarWrap}>
                <div style={s.indeterminateBar} />
              </div>
              <div style={s.detectingSubtext}>This may take a moment depending on video length</div>
            </div>
          ) : (
            <div style={s.grid}>
              {cards}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
