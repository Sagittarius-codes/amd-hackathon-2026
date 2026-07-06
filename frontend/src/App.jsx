import { useState, useEffect } from 'react';
import { useWebSocket } from './hooks/useWebSocket';

import WelcomeScreen from './components/WelcomeScreen';
import UploadScreen from './components/UploadScreen';
import SceneSettingsModal from './components/SceneSettingsModal';
import Dashboard from './components/Dashboard';

export default function App() {
  const [stage, setStage] = useState(1);
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'dark';
  });
  const [uploadedFile, setUploadedFile] = useState(null); // File object representation 
  const [startTime, setStartTime] = useState(null);

  const {
    scenes, results, status, progress,
    currentScene, totalScenes, wsConnected, reset,
  } = useWebSocket();

  // Apply theme class to document root
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Track start time
  useEffect(() => {
    if (status === 'processing' && !startTime) {
      setStartTime(Date.now());
    }
    if (status === 'idle') {
      setStartTime(null);
    }
  }, [status, startTime]);

  // Fast-forward stage to Dashboard if processing, but let Welcome screen show first
  useEffect(() => {
    if (status === 'processing' && stage === 2) {
      setStage(4);
    }
  }, [status, stage]);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const res = await fetch(`${API_URL}/status`);
        const data = await res.json();
        if (data.status === 'complete' || data.status === 'idle') {
          reset();
        }
      } catch (e) {
        console.warn("App mount status fetch failed:", e);
      }
    };
    fetchStatus();
  }, [reset]);

  const handleToggleTheme = () => {
    setTheme(t => t === 'dark' ? 'light' : 'dark');
  };

  return (
    <>
      {stage === 1 && (
        <WelcomeScreen 
          onComplete={() => setStage(2)} 
        />
      )}
      
      {(stage === 2 || stage === 3) && (
        <UploadScreen 
          dimmed={stage === 3}
          setUploadedFile={setUploadedFile}
          onComplete={() => {
            setStage(3);
          }} 
        />
      )}

      {stage === 3 && (
        <SceneSettingsModal 
          onCancel={() => setStage(2)}
          onComplete={() => {
            setStage(4);
          }}
          resetWS={reset}
        />
      )}

      {stage === 4 && (
        <Dashboard 
          theme={theme}
          toggleTheme={handleToggleTheme}
          uploadedFile={uploadedFile} // This is just an indicator for the UI, could be derived differently
          status={status}
          progress={progress}
          currentScene={currentScene}
          totalScenes={totalScenes}
          results={results}
          scenes={scenes}
          wsConnected={wsConnected}
          startTime={startTime}
        />
      )}
    </>
  );
}
