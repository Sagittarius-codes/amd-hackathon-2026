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
            reset(); // Clear old WS state
            setStage(4);
          }}
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
          wsConnected={wsConnected}
          startTime={startTime}
        />
      )}
    </>
  );
}
