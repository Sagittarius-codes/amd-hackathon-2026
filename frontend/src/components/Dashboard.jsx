import { useState, useEffect } from 'react';
import { Moon, Sun, Clapperboard, CheckCircle, BarChart2 } from 'lucide-react';
import LeftPanel from './LeftPanel';
import SceneTimeline from './SceneTimeline';
import SceneCard from './SceneCard';

export default function Dashboard({ 
  theme, toggleTheme, uploadedFile, 
  status, progress, currentScene, totalScenes, results, scenes,
  wsConnected, startTime
}) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    let interval;
    if (status === 'processing' && startTime) {
      interval = setInterval(() => {
        setElapsed(Date.now() - startTime);
      }, 1000);
    } else if (status === 'complete') {
      if (startTime) setElapsed(Date.now() - startTime);
    }
    return () => clearInterval(interval);
  }, [status, startTime]);

  function formatTime(ms) {
    if (!ms || ms < 0) return '00:00';
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  }

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
    <div style={s.dashboard} className="animate-fade-slide-in relative">
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes slideBar {
          0% { left: -40%; }
          50% { left: 100%; }
          100% { left: -40%; }
        }
        @keyframes slideUp {
          from { transform: translateY(100%); }
          to { transform: translateY(0); }
        }
      `}} />
      <div style={s.topBar}>
        <div style={s.topLeft}>
          <div style={s.logoWrap}><Clapperboard size={18} /></div>
          <div style={s.appName}>CaptionAI</div>
        </div>
        <div style={s.topCenter} className="max-[480px]:hidden">
          by Sagittarius Codes
        </div>
        <div style={s.topRight}>
          <button style={s.themeBtn} onClick={toggleTheme} title="Toggle Theme">
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>
      </div>

      <div style={s.mainBody}>
        {/* Desktop Left Panel */}
        <div className="hidden md:flex flex-shrink-0">
          <LeftPanel 
            uploadedFile={uploadedFile}
            status={status}
            progress={progress}
            totalScenes={totalScenes}
            resultsCount={results.length}
            wsConnected={wsConnected}
            startTime={startTime}
            isMobileDrawer={false}
          />
        </div>

        <div style={s.contentArea}>
          {/* Mobile Summary Bar */}
          <div className="md:hidden flex flex-wrap items-center justify-between bg-[var(--surface-elevated)] p-3 rounded-xl mb-4 border border-[var(--border)] gap-2 shadow-sm">
            <div className="flex gap-4 items-center">
              <div className="text-[15px] font-bold text-[var(--text-primary)]">{Math.round(progress)}%</div>
              <div className="text-[12px] font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                {results.length}/{totalScenes || '-'} Scenes
              </div>
            </div>
            <div className="flex gap-4 items-center">
              <div className="text-[13px] font-semibold text-[var(--text-secondary)]">{formatTime(elapsed)}</div>
              <div className={`w-2.5 h-2.5 rounded-full ${wsConnected ? 'bg-[var(--success)] shadow-[0_0_8px_var(--success)]' : 'bg-[var(--error)] animate-pulse'}`} />
            </div>
          </div>

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
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mt-6 pb-20 md:pb-0">
              {cards}
            </div>
          )}
        </div>
      </div>

      {/* Floating Action Button for Mobile Drawer */}
      <button 
        className="md:hidden fixed bottom-6 left-6 w-14 h-14 bg-[var(--accent-primary)] text-white rounded-full flex items-center justify-center shadow-lg z-40 transition-transform active:scale-95"
        onClick={() => setDrawerOpen(true)}
        aria-label="Open Stats"
      >
        <BarChart2 size={24} />
      </button>

      {/* Slide-up Drawer Overlay */}
      {drawerOpen && (
        <div 
          className="md:hidden fixed inset-0 z-50 flex items-end bg-black/50 transition-opacity" 
          onClick={() => setDrawerOpen(false)}
        >
          <div 
            className="w-full max-h-[85vh] overflow-hidden bg-[var(--surface)] rounded-t-2xl shadow-2xl animate-[slideUp_0.3s_ease-out_forwards]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="w-full flex justify-center py-3 border-b border-[var(--border)]">
              <div className="w-12 h-1.5 bg-[var(--border)] rounded-full" />
            </div>
            <div className="overflow-y-auto max-h-[calc(85vh-32px)]">
              <LeftPanel 
                uploadedFile={uploadedFile}
                status={status}
                progress={progress}
                totalScenes={totalScenes}
                resultsCount={results.length}
                wsConnected={wsConnected}
                startTime={startTime}
                isMobileDrawer={true}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
