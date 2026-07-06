import { useState, useEffect } from 'react';
import { Clapperboard } from 'lucide-react';

export default function WelcomeScreen({ onComplete }) {
  const [progress, setProgress] = useState(0);
  const [messageIdx, setMessageIdx] = useState(0);

  const messages = [
    "Initializing pipeline...",
    "Loading scene detector...",
    "Warming up caption engine...",
    "Ready."
  ];

  useEffect(() => {
    // 5 seconds total = 5000ms
    const totalDuration = 5000;
    const intervalTime = 50; // update every 50ms
    const steps = totalDuration / intervalTime;
    let currentStep = 0;

    const timer = setInterval(() => {
      currentStep++;
      const newProgress = (currentStep / steps) * 100;
      setProgress(newProgress);

      // Update message based on progress
      if (newProgress < 25) setMessageIdx(0);
      else if (newProgress < 50) setMessageIdx(1);
      else if (newProgress < 85) setMessageIdx(2);
      else setMessageIdx(3);

      if (currentStep >= steps) {
        clearInterval(timer);
        setTimeout(onComplete, 300); // small delay after 100%
      }
    }, intervalTime);

    return () => clearInterval(timer);
  }, [onComplete]);

  const s = {
    container: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      width: '100%',
      position: 'relative',
    },
    logoWrap: {
      marginBottom: 24,
      background: 'var(--accent-primary)',
      padding: 16,
      borderRadius: 16,
      color: 'white',
      boxShadow: '0 8px 32px rgba(194, 98, 42, 0.3)',
    },
    title: {
      fontSize: 42,
      fontWeight: 800,
      color: 'var(--text-primary)',
      letterSpacing: '-1px',
      marginBottom: 8,
    },
    subtitle: {
      fontSize: 16,
      fontWeight: 500,
      color: 'var(--text-muted)',
      marginBottom: 48,
    },
    progressWrap: {
      width: 300,
      height: 6,
      background: 'var(--surface-elevated)',
      borderRadius: 99,
      overflow: 'hidden',
      marginBottom: 16,
    },
    progressBar: {
      height: '100%',
      background: 'var(--accent-primary)',
      width: `${progress}%`,
      transition: 'width 50ms linear',
    },
    message: {
      fontSize: 14,
      fontWeight: 500,
      color: 'var(--text-secondary)',
      transition: 'opacity 0.3s',
      height: 20, // fixed height to prevent jumping
    },
    footer: {
      position: 'absolute',
      bottom: 24,
      fontSize: 12,
      fontWeight: 500,
      color: 'var(--text-muted)',
    }
  };

  return (
    <div style={s.container} className="animate-fade-slide-in">
      <div style={s.logoWrap}>
        <Clapperboard size={48} />
      </div>
      <h1 style={s.title}>CaptionAI</h1>
      <p style={s.subtitle}>AMD Developer Hackathon 2026 · Track 2</p>
      
      <div style={s.progressWrap}>
        <div style={s.progressBar} />
      </div>
      <div style={s.message}>{messages[messageIdx]}</div>

      <div style={s.footer}>Built by Sagittarius Codes</div>
    </div>
  );
}
