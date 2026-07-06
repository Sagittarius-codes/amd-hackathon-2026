import { useState, useRef, useCallback } from 'react';
import { Upload, Film, CheckCircle, AlertCircle } from 'lucide-react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function UploadScreen({ onComplete, dimmed, setUploadedFile }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState({ pct: 0, loaded: 0, total: 0 });
  const [uploaded, setUploaded] = useState(null); // { name, size }
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const uploadFile = useCallback((file) => {
    if (!file) return;
    setError(null);
    setUploading(true);
    setUploaded(null);
    setProgress({ pct: 0, loaded: 0, total: file.size });

    const form = new FormData();
    form.append('file', file);

    const xhr = new XMLHttpRequest();
    
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const pct = Math.round((event.loaded / event.total) * 100);
        setProgress({ pct, loaded: event.loaded, total: event.total });
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        setUploaded({ name: file.name, size: file.size });
        setProgress(p => ({ ...p, pct: 100 }));
        if (setUploadedFile) setUploadedFile({ name: file.name, size: file.size });
        
        // Show success state briefly, then transition to Stage 3
        setTimeout(() => {
          setUploading(false);
          onComplete(); // Triggers Stage 3
        }, 1000);
      } else {
        let msg = 'Upload failed';
        try {
          const res = JSON.parse(xhr.responseText);
          msg = res.detail || msg;
        } catch(e) {}
        setError(msg);
        setUploading(false);
      }
    };

    xhr.onerror = () => {
      setError('Network error during upload');
      setUploading(false);
    };

    xhr.open('POST', `${API}/upload`, true);
    xhr.send(form);
  }, [onComplete]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    if (uploading || uploaded) return;
    const file = e.dataTransfer.files?.[0];
    if (file) uploadFile(file);
  }, [uploadFile, uploading, uploaded]);

  const onFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) uploadFile(file);
  };

  const s = {
    container: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100vh',
      width: '100%',
      padding: 24,
      position: 'relative',
      transition: 'filter 0.3s',
      filter: dimmed ? 'brightness(0.5)' : 'none',
    },
    dropZone: {
      width: '100%',
      maxWidth: 600,
      border: `2px dashed ${dragging ? 'var(--accent-primary)' : 'var(--border)'}`,
      borderRadius: 24,
      padding: '64px 32px',
      textAlign: 'center',
      cursor: (uploading || uploaded) ? 'default' : 'pointer',
      transition: 'all 0.2s',
      background: dragging ? 'var(--accent-soft)' : 'var(--surface)',
      boxShadow: dragging ? '0 0 20px rgba(194, 98, 42, 0.2)' : 'none',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
    },
    iconWrap: {
      width: 80, height: 80,
      borderRadius: '50%',
      background: 'var(--surface-elevated)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      marginBottom: 24,
      color: uploaded ? 'var(--success)' : 'var(--accent-primary)',
    },
    title: {
      fontSize: 24,
      fontWeight: 700,
      color: 'var(--text-primary)',
      marginBottom: 8,
    },
    subtitle: {
      fontSize: 16,
      color: 'var(--text-muted)',
      marginBottom: 32,
    },
    progressContainer: {
      width: '100%',
      maxWidth: 400,
      marginTop: 24,
    },
    progressHeader: {
      display: 'flex',
      justifyContent: 'space-between',
      fontSize: 14,
      fontWeight: 600,
      color: 'var(--text-secondary)',
      marginBottom: 8,
    },
    progressBarWrap: {
      width: '100%',
      height: 8,
      background: 'var(--surface-elevated)',
      borderRadius: 99,
      overflow: 'hidden',
    },
    progressBar: {
      height: '100%',
      background: 'var(--accent-primary)',
      width: `${progress.pct}%`,
      transition: 'width 200ms ease-out',
    },
    successWrap: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      color: 'var(--success)',
      fontSize: 18,
      fontWeight: 600,
      marginTop: 24,
    },
    errorBox: {
      marginTop: 24,
      padding: '12px 16px',
      borderRadius: 12,
      background: 'var(--error)',
      color: 'white',
      fontSize: 14,
      display: 'flex', alignItems: 'center', gap: 8,
      fontWeight: 500,
    }
  };

  return (
    <div style={s.container} className="animate-fade-slide-in">
      <div 
        style={s.dropZone}
        onClick={() => !uploading && !uploaded && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <div style={s.iconWrap}>
          {uploaded ? <CheckCircle size={40} /> : <Upload size={40} />}
        </div>
        
        {uploaded ? (
          <>
            <div style={s.title}>Upload complete</div>
            <div style={s.successWrap}>
              <Film size={20} />
              {uploaded.name} ({formatBytes(uploaded.size)})
            </div>
          </>
        ) : (
          <>
            <div style={s.title}>{dragging ? 'Drop to upload' : 'Drag & drop your video here'}</div>
            <div style={s.subtitle}>or click to browse • Accepts MP4, MOV, AVI, MKV</div>
          </>
        )}

        {uploading && (
          <div style={s.progressContainer}>
            <div style={s.progressHeader}>
              <span>Uploading... {progress.pct}%</span>
              <span>{formatBytes(progress.loaded)} / {formatBytes(progress.total)}</span>
            </div>
            <div style={s.progressBarWrap}>
              <div style={s.progressBar} />
            </div>
          </div>
        )}

        {error && (
          <div style={s.errorBox}>
            <AlertCircle size={18} />
            {error}
          </div>
        )}

        <input
          ref={inputRef}
          type="file"
          accept="video/*"
          style={{ display: 'none' }}
          onChange={onFileChange}
        />
      </div>
    </div>
  );
}
