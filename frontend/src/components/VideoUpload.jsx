// src/components/VideoUpload.jsx
// Drag-and-drop (or click-to-browse) video upload panel.
// Calls POST /upload and reports filename + size after success.

import { useState, useRef, useCallback } from 'react';
import axios from 'axios';
import { Upload, Film, CheckCircle, AlertCircle, Loader } from 'lucide-react';

// API base URL — set VITE_API_URL at build time (see frontend/Dockerfile).
// Falls back to localhost:8000 for local `npm run dev` usage.
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export default function VideoUpload({ dark, onUploaded }) {
  const [dragging, setDragging]     = useState(false);
  const [uploading, setUploading]   = useState(false);
  const [uploaded, setUploaded]     = useState(null);  // { name, size }
  const [error, setError]           = useState(null);
  const inputRef = useRef(null);

  const c = {
    card: {
      background: dark ? '#1a1a1a' : '#ffffff',
      border: `2px dashed ${dragging
        ? '#6366f1'
        : dark ? '#2a2a2a' : '#d1d5db'}`,
      borderRadius: 16,
      padding: '28px 20px',
      textAlign: 'center',
      cursor: 'pointer',
      transition: 'border-color 0.2s, background 0.2s',
      background: dragging
        ? dark ? '#1e1e2e' : '#eef2ff'
        : dark ? '#1a1a1a' : '#ffffff',
    },
    label: {
      fontSize: 13,
      fontWeight: 600,
      color: dark ? '#a1a1aa' : '#6b7280',
      letterSpacing: '0.08em',
      textTransform: 'uppercase',
      marginBottom: 16,
      display: 'block',
    },
    iconWrap: {
      width: 56, height: 56,
      borderRadius: '50%',
      background: dark ? '#252535' : '#ede9fe',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      margin: '0 auto 16px',
    },
    hint: {
      fontSize: 13,
      color: dark ? '#52525b' : '#9ca3af',
      marginTop: 8,
    },
    successRow: {
      display: 'flex', alignItems: 'center', gap: 10,
      background: dark ? '#0f2318' : '#ecfdf5',
      borderRadius: 10,
      padding: '12px 14px',
      marginTop: 14,
    },
    fileName: {
      fontWeight: 600,
      fontSize: 13,
      color: dark ? '#4ade80' : '#16a34a',
      whiteSpace: 'nowrap',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      maxWidth: 160,
    },
    fileSize: {
      fontSize: 11,
      color: dark ? '#22c55e' : '#15803d',
      marginLeft: 'auto',
      flexShrink: 0,
    },
    errorBox: {
      marginTop: 12,
      padding: '10px 12px',
      borderRadius: 8,
      background: dark ? '#1f0a0a' : '#fef2f2',
      color: dark ? '#f87171' : '#dc2626',
      fontSize: 12,
      display: 'flex', alignItems: 'center', gap: 6,
    },
  };

  const upload = useCallback(async (file) => {
    if (!file) return;
    setError(null);
    setUploading(true);
    setUploaded(null);

    const form = new FormData();
    form.append('file', file);

    try {
      await axios.post(`${API}/upload`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setUploaded({ name: file.name, size: file.size });
      onUploaded?.();
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Upload failed';
      setError(msg);
    } finally {
      setUploading(false);
    }
  }, [onUploaded]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) upload(file);
  }, [upload]);

  const onFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) upload(file);
  };

  return (
    <div>
      <span style={c.label}>Video Source</span>
      <div
        style={c.card}
        onClick={() => !uploading && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <div style={c.iconWrap}>
          {uploading
            ? <Loader size={24} color="#6366f1" style={{ animation: 'spin 1s linear infinite' }} />
            : uploaded
            ? <CheckCircle size={24} color="#22c55e" />
            : <Upload size={24} color="#6366f1" />
          }
        </div>

        <p style={{ fontWeight: 600, color: dark ? '#e4e4e7' : '#111827', fontSize: 14 }}>
          {uploading
            ? 'Uploading…'
            : dragging
            ? 'Drop to upload'
            : 'Drag & drop or click to browse'}
        </p>
        <p style={c.hint}>MP4, MOV, AVI, MKV accepted</p>

        <input
          ref={inputRef}
          type="file"
          accept="video/*"
          style={{ display: 'none' }}
          onChange={onFileChange}
        />
      </div>

      {uploaded && (
        <div style={c.successRow}>
          <Film size={16} color="#22c55e" />
          <span style={c.fileName} title={uploaded.name}>{uploaded.name}</span>
          <span style={c.fileSize}>{formatBytes(uploaded.size)}</span>
        </div>
      )}

      {error && (
        <div style={c.errorBox}>
          <AlertCircle size={14} />
          {error}
        </div>
      )}
    </div>
  );
}
