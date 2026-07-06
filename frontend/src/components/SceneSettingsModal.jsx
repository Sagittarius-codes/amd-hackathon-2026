import { useState, useEffect } from 'react';
import axios from 'axios';
import { Loader, Play, X } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function SceneSettingsModal({ onComplete, onCancel }) {
  const [maxScenes, setMaxScenes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [closing, setClosing] = useState(false); // true if sliding out left

  // On mount, modal slides in from right via CSS animation.
  // On run pipeline, we want to slide out left, then call onComplete.

  const handleRun = async () => {
    setError(null);
    setLoading(true);
    try {
      const body = { max_scenes: maxScenes ? parseInt(maxScenes, 10) : null };
      await axios.post(`${API}/process`, body);
      setClosing(true);
      setTimeout(() => onComplete(), 300); // Wait for slide out animation
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to start');
      setLoading(false);
    }
  };

  const s = {
    overlay: {
      position: 'absolute',
      top: 0, left: 0, right: 0, bottom: 0,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 100,
      // The background dimming is handled by UploadScreen's dimmed prop
    },
    modal: {
      background: 'var(--surface-elevated)',
      width: '100%',
      maxWidth: 500,
      borderRadius: 24,
      padding: 32,
      boxShadow: '0 24px 64px rgba(0,0,0,0.2)',
      border: '1px solid var(--border)',
      position: 'relative',
      // Determine animation based on closing state
      animation: closing 
        ? 'fadeSlideOutLeft 0.3s ease-in forwards' 
        : 'fadeSlideInRight 0.3s ease-out forwards',
    },
    title: {
      fontSize: 24,
      fontWeight: 700,
      color: 'var(--text-primary)',
      marginBottom: 16,
    },
    description: {
      fontSize: 15,
      lineHeight: 1.6,
      color: 'var(--text-secondary)',
      marginBottom: 32,
    },
    inputWrap: {
      marginBottom: 32,
    },
    label: {
      display: 'block',
      fontSize: 13,
      fontWeight: 600,
      color: 'var(--text-primary)',
      marginBottom: 8,
    },
    input: {
      width: '100%',
      background: 'var(--surface)',
      border: '2px solid var(--border)',
      borderRadius: 12,
      padding: '14px 16px',
      color: 'var(--text-primary)',
      fontSize: 16,
      transition: 'border-color 0.2s',
    },
    inputHint: {
      fontSize: 13,
      color: 'var(--text-muted)',
      marginTop: 8,
    },
    buttonRow: {
      display: 'flex',
      gap: 16,
      justifyContent: 'flex-end',
    },
    btnCancel: {
      padding: '12px 24px',
      borderRadius: 12,
      fontWeight: 600,
      fontSize: 15,
      color: 'var(--text-secondary)',
      background: 'transparent',
      transition: 'background 0.2s',
    },
    btnRun: {
      padding: '12px 24px',
      borderRadius: 12,
      fontWeight: 600,
      fontSize: 15,
      color: 'white',
      background: 'var(--accent-primary)',
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      boxShadow: '0 4px 16px rgba(194, 98, 42, 0.3)',
      transition: 'transform 0.1s, opacity 0.2s',
      opacity: loading ? 0.7 : 1,
      cursor: loading ? 'not-allowed' : 'pointer',
    },
    errorBox: {
      marginBottom: 24,
      padding: '12px 16px',
      borderRadius: 12,
      background: 'var(--error)',
      color: 'white',
      fontSize: 14,
      fontWeight: 500,
    }
  };

  return (
    <div style={s.overlay}>
      <div style={s.modal}>
        <div style={s.title}>Configure Pipeline</div>
        <div style={s.description}>
          CaptionAI detects scene boundaries in your video and generates captions for each scene — not individual frames. This keeps captions contextually meaningful.
        </div>

        <div style={s.inputWrap}>
          <label style={s.label}>Max scenes to caption</label>
          <input
            style={s.input}
            type="number"
            min={1}
            placeholder="Leave blank for all scenes"
            value={maxScenes}
            onChange={(e) => setMaxScenes(e.target.value)}
            disabled={loading}
          />
          <div style={s.inputHint}>Limit scenes for faster testing. Leave blank to caption the entire video.</div>
        </div>

        {error && <div style={s.errorBox}>{error}</div>}

        <div style={s.buttonRow}>
          <button 
            style={s.btnCancel} 
            onClick={onCancel}
            disabled={loading}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--surface)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          >
            Cancel
          </button>
          <button 
            style={s.btnRun} 
            onClick={handleRun}
            disabled={loading}
          >
            {loading ? <Loader size={18} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} /> : <Play size={18} />}
            {loading ? 'Starting...' : 'Run Pipeline'}
          </button>
        </div>
      </div>
    </div>
  );
}
