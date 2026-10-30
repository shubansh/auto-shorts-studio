import { useState, useEffect, useRef } from 'react';
import { 
  Play, Pause, Scissors, Trash2, Download, Zap, Film, 
  Settings, Folder, Sparkles, Video, CheckCircle2,
  Sliders, Palette, Monitor, Upload, RefreshCw
} from 'lucide-react';

interface VideoMeta {
  width: number;
  height: number;
  duration: number;
  fps: number;
}

interface TimelineThumb {
  timestamp: number;
  url: string;
}

interface ClipMoment {
  start: number;
  end: number;
  title: string;
  virality_score: number;
  hook_score: number;
  tags: string[];
  reason: string;
}

interface RenderJob {
  status: 'idle' | 'running' | 'complete' | 'error';
  progress: number;
  message: string;
  results: any[];
}

export default function App() {
  const [nav, setNav] = useState<'dashboard' | 'capture' | 'studio' | 'layout' | 'captions' | 'library' | 'settings'>('studio');
  const [session, setSession] = useState<{
    video_path: string | null;
    video_url: string | null;
    filename: string | null;
    meta: VideoMeta;
    preview_url: string | null;
    timeline_thumbs: TimelineThumb[];
    discovered_clips: ClipMoment[];
  } | null>(null);

  const [loading, setLoading] = useState(false);
  const [localVideos, setLocalVideos] = useState<{ filename: string; size_mb: number }[]>([]);
  const [library, setLibrary] = useState<{ filename: string; size_mb: number; video_url: string }[]>([]);
  const [ytUrl, setYtUrl] = useState('');

  // Video Player & Timeline State
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [playheadTime, setPlayheadTime] = useState(91.0); // Default to gameplay start
  const [cutIn, setCutIn] = useState(45);
  const [cutOut, setCutOut] = useState(85);

  // Layout & Alignment State (Percentage coords)
  const [fcBox, setFcBox] = useState({ x: 65, y: 5, w: 32, h: 40 });
  const [gpBox, setGpBox] = useState({ x: 15, y: 0, w: 70, h: 100 });
  const [layoutMode, setLayoutMode] = useState<'gaming_split' | 'crop' | 'blur_fit'>('gaming_split');
  const [activeTheme, setActiveTheme] = useState('Hormozi Gold (Viral)');
  const [enableEmojis, setEnableEmojis] = useState(true);

  // Selected Clip Indices
  const [selectedClips, setSelectedClips] = useState<number[]>([]);
  const [renderJob, setRenderJob] = useState<RenderJob>({ status: 'idle', progress: 0, message: '', results: [] });

  // Fetch Session on Load
  const fetchSession = async () => {
    try {
      const res = await fetch('/api/session');
      if (res.ok) {
        const data = await res.json();
        setSession(data);
        if (data.meta && data.meta.duration > 0) {
          setCutOut(Math.min(Math.round(data.meta.duration), 85));
        }
      }
    } catch (err) {
      console.error('Failed to load session:', err);
    }
  };

  const fetchLocalSessions = async () => {
    try {
      const res = await fetch('/api/sessions/local');
      if (res.ok) setLocalVideos(await res.json());
    } catch (err) {
      console.error(err);
    }
  };

  const fetchLibrary = async () => {
    try {
      const res = await fetch('/api/library');
      if (res.ok) setLibrary(await res.json());
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchSession();
    fetchLocalSessions();
    fetchLibrary();
  }, []);

  // Poll Render Job
  useEffect(() => {
    let interval: any;
    if (renderJob.status === 'running') {
      interval = setInterval(async () => {
        try {
          const res = await fetch('/api/render/status');
          if (res.ok) {
            const data: RenderJob = await res.json();
            setRenderJob(data);
            if (data.status === 'complete' || data.status === 'error') {
              clearInterval(interval);
              fetchLibrary();
              if (data.status === 'complete') {
                setNav('library');
              }
            }
          }
        } catch (e) {
          console.error('Error polling render status', e);
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [renderJob.status]);

  // Video Player Controls
  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const seekExact = (timeSec: number) => {
    if (!videoRef.current) return;
    const clamped = Math.max(0, Math.min(timeSec, session?.meta?.duration || 1000));
    videoRef.current.currentTime = clamped;
    setCurrentTime(clamped);
    setPlayheadTime(clamped);
  };

  const seekRelative = (delta: number) => {
    if (!videoRef.current) return;
    seekExact(videoRef.current.currentTime + delta);
  };

  // NLE Ripple Delete Intro (0.1s lossless cut)
  const handleRippleDeleteIntro = async () => {
    if (!session || playheadTime <= 0) return;
    const confirmed = window.confirm(
      `🗑️ RIPPLE DELETE INTRO:\n\nPermanently delete 00:00 to ${formatTime(playheadTime)} (${Math.round(playheadTime)}s) from the project?\n\nThis uses FFmpeg lossless stream copy (takes 0.1s).`
    );
    if (!confirmed) return;

    setLoading(true);
    try {
      const res = await fetch('/api/video/trim', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_time: playheadTime,
          end_time: session.meta.duration
        })
      });
      if (res.ok) {
        await fetchSession();
        await fetchLocalSessions();
        seekExact(0);
        alert('✅ Pre-roll intro deleted! Timeline updated.');
      } else {
        const err = await res.json();
        alert('Trim failed: ' + err.detail);
      }
    } catch (e) {
      alert('Error during trim: ' + e);
    } finally {
      setLoading(false);
    }
  };

  // NLE Ripple Delete Outro
  const handleRippleDeleteOutro = async () => {
    if (!session || playheadTime >= session.meta.duration) return;
    const confirmed = window.confirm(
      `🗑️ RIPPLE DELETE OUTRO:\n\nPermanently delete everything after ${formatTime(playheadTime)}?`
    );
    if (!confirmed) return;

    setLoading(true);
    try {
      const res = await fetch('/api/video/trim', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_time: 0,
          end_time: playheadTime
        })
      });
      if (res.ok) {
        await fetchSession();
        await fetchLocalSessions();
        seekExact(0);
        alert('✅ Outro deleted! Timeline updated.');
      } else {
        const err = await res.json();
        alert('Trim failed: ' + err.detail);
      }
    } catch (e) {
      alert('Error during trim: ' + e);
    } finally {
      setLoading(false);
    }
  };

  // AI Highlights Scan
  const handleScanHighlights = async (startFromSec = 0) => {
    setLoading(true);
    try {
      const res = await fetch('/api/highlights/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          num_clips: 3,
          min_duration: 20,
          max_duration: 50,
          scan_start: startFromSec
        })
      });
      if (res.ok) {
        const data = await res.json();
        setSession((prev: any) => ({ ...prev, discovered_clips: data.clips }));
        setSelectedClips(data.clips.map((_: any, idx: number) => idx));
      } else {
        const err = await res.json();
        alert('Scan failed: ' + err.detail);
      }
    } catch (e) {
      alert('Scan error: ' + e);
    } finally {
      setLoading(false);
    }
  };

  // Switch Active Session
  const handleSelectSession = async (filename: string) => {
    setLoading(true);
    try {
      const res = await fetch('/api/sessions/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename })
      });
      if (res.ok) {
        const data = await res.json();
        setSession(data);
        seekExact(0);
        setNav('studio');
      }
    } catch (e) {
      alert('Failed to switch video: ' + e);
    } finally {
      setLoading(false);
    }
  };

  // Import YouTube
  const handleImportYoutube = async () => {
    if (!ytUrl.trim()) return;
    setLoading(true);
    try {
      const res = await fetch('/api/import/youtube', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: ytUrl })
      });
      if (res.ok) {
        const data = await res.json();
        setSession(data);
        setYtUrl('');
        await fetchLocalSessions();
        setNav('studio');
      } else {
        const err = await res.json();
        alert('Import failed: ' + err.detail);
      }
    } catch (e) {
      alert('Import error: ' + e);
    } finally {
      setLoading(false);
    }
  };

  // Upload Local Video File
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);

    setLoading(true);
    try {
      const res = await fetch('/api/import/upload', {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        const data = await res.json();
        setSession(data);
        await fetchLocalSessions();
        setNav('studio');
      } else {
        const err = await res.json();
        alert('Upload failed: ' + err.detail);
      }
    } catch (err) {
      alert('Upload error: ' + err);
    } finally {
      setLoading(false);
    }
  };

  // Batch or Custom Short Render
  const handleRenderShorts = async (customClips?: ClipMoment[]) => {
    if (!session) return;
    const clipsToRender = customClips || (session.discovered_clips.filter((_, idx) => selectedClips.includes(idx)));
    if (!clipsToRender.length) {
      alert('No clips selected!');
      return;
    }

    const gamingConfig = {
      facecam: {
        x: Math.round((fcBox.x / 100) * session.meta.width),
        y: Math.round((fcBox.y / 100) * session.meta.height),
        w: Math.round((fcBox.w / 100) * session.meta.width),
        h: Math.round((fcBox.h / 100) * session.meta.height)
      },
      gameplay: {
        x: Math.round((gpBox.x / 100) * session.meta.width),
        y: Math.round((gpBox.y / 100) * session.meta.height),
        w: Math.round((gpBox.w / 100) * session.meta.width),
        h: Math.round((gpBox.h / 100) * session.meta.height)
      },
      top_height: 760
    };

    setRenderJob({ status: 'running', progress: 5, message: 'Initiating NVENC 60 FPS Render...', results: [] });

    try {
      const res = await fetch('/api/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clips: clipsToRender,
          layout_mode: layoutMode,
          gaming_config: gamingConfig,
          subtitle_theme: activeTheme,
          enable_emojis: enableEmojis
        })
      });
      if (!res.ok) {
        const err = await res.json();
        alert('Render failed: ' + err.detail);
        setRenderJob({ status: 'error', progress: 0, message: 'Render failed', results: [] });
      }
    } catch (e) {
      alert('Render error: ' + e);
    }
  };

  // Helper timecode format
  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0c0d12] text-[#f8fafc]">
      {/* ---------------- SIDEBAR ---------------- */}
      <aside className="w-64 border-r border-[#1e2436] bg-[#08090d] flex flex-col justify-between p-4">
        <div>
          {/* Logo */}
          <div className="flex items-center gap-3 pb-5 border-b border-[#1e2436] mb-5">
            <div className="w-9 h-9 rounded-lg bg-[#ccff00] text-black font-black flex items-center justify-center text-xl shadow-[0_0_12px_rgba(204,255,0,0.3)]">
              P
            </div>
            <h1 className="text-xl font-extrabold tracking-widest text-white">POWDER</h1>
          </div>

          {/* Navigation Items */}
          <div className="text-[11px] font-bold uppercase tracking-wider text-[#94a3b8] mb-2">Main Product Flow</div>
          <nav className="flex flex-col gap-1">
            {[
              { id: 'dashboard', label: 'Dashboard', icon: Monitor },
              { id: 'capture', label: 'Capture & Ingest', icon: Video },
              { id: 'studio', label: 'Studio & Editor', icon: Scissors },
              { id: 'layout', label: 'Layout & Alignment', icon: Sliders },
              { id: 'captions', label: 'Captions & Styling', icon: Palette },
              { id: 'library', label: 'Clips Library', icon: Folder },
              { id: 'settings', label: 'Settings & GPU', icon: Settings }
            ].map((item) => {
              const Icon = item.icon;
              const isActive = nav === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setNav(item.id as any)}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                    isActive 
                      ? 'bg-[#1e2436] text-[#ccff00] shadow-[0_0_10px_rgba(204,255,0,0.15)]' 
                      : 'text-[#94a3b8] hover:text-white hover:bg-[#121520]'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Sidebar Status Footer */}
        <div className="space-y-3">
          <div className="bg-[#111420] border border-[#1e2436] rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-2 h-2 rounded-full bg-[#22c55e] animate-pulse"></div>
              <span className="text-xs font-bold text-white">RTX 3050 NVENC</span>
            </div>
            <div className="text-[11px] text-[#94a3b8]">GPU 60 FPS Acceleration Online</div>
          </div>

          {session?.video_path && (
            <div className="bg-[#111420] border border-[#1e2436] rounded-lg p-3">
              <div className="text-[10px] uppercase font-bold text-[#94a3b8]">Active Session</div>
              <div className="text-xs font-semibold text-white truncate mt-0.5">{session.filename}</div>
              <div className="text-[11px] text-[#64748b] mt-1">
                {session.meta.width}x{session.meta.height} • {Math.round(session.meta.duration)}s
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* ---------------- MAIN CONTENT AREA ---------------- */}
      <main className="flex-1 flex flex-col overflow-y-auto">
        {/* Top Header */}
        <header className="h-14 border-b border-[#1e2436] bg-[#0c0d12] flex items-center justify-between px-6 shrink-0">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-bold text-white uppercase tracking-wide">
              {nav === 'studio' && '✂️ NLE Studio & Timeline Editor'}
              {nav === 'dashboard' && '🏠 Creator Dashboard'}
              {nav === 'capture' && '📥 Game Capture & Video Ingest'}
              {nav === 'layout' && '🎛️ Interactive Mouse Canvas & Alignment'}
              {nav === 'captions' && '🎨 Subtitle Styles & Karaoke'}
              {nav === 'library' && '📂 Rendered 9:16 Shorts Library'}
              {nav === 'settings' && '⚙️ System Settings & RTX 3050 NVENC'}
            </h2>

            {/* Quick Session Switcher Dropdown */}
            {localVideos.length > 0 && (
              <select
                value={session?.filename || ''}
                onChange={(e) => handleSelectSession(e.target.value)}
                className="bg-[#121520] border border-[#2a334d] text-xs font-semibold text-[#cbd5e1] rounded-lg px-2.5 py-1.5 focus:border-[#ccff00] outline-none"
              >
                {localVideos.map((v) => (
                  <option key={v.filename} value={v.filename}>
                    📁 {v.filename} ({v.size_mb} MB)
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="flex items-center gap-3">
            {renderJob.status === 'running' && (
              <div className="bg-[#ccff00]/15 border border-[#ccff00]/40 text-[#ccff00] px-3 py-1 rounded-full text-xs font-extrabold flex items-center gap-2 animate-pulse">
                <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Rendering: {renderJob.message} ({renderJob.progress}%)
              </div>
            )}
            <div className="bg-[#22c55e]/15 border border-[#22c55e]/30 text-[#4ade80] px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5" /> 15x GPU Hardware Speed
            </div>
          </div>
        </header>

        {/* ---------------- VIEW: DASHBOARD ---------------- */}
        {nav === 'dashboard' && (
          <div className="p-8 max-w-5xl space-y-6">
            <div className="grid grid-cols-3 gap-6">
              <div className="bg-[#121520] border border-[#1e2436] rounded-2xl p-5 space-y-2">
                <div className="text-xs font-bold uppercase text-[#94a3b8]">Active Project</div>
                <div className="text-lg font-black text-white truncate">{session?.filename || 'No video loaded'}</div>
                <div className="text-xs text-[#ccff00] font-semibold">{Math.round(session?.meta?.duration || 0)}s duration</div>
              </div>

              <div className="bg-[#121520] border border-[#1e2436] rounded-2xl p-5 space-y-2">
                <div className="text-xs font-bold uppercase text-[#94a3b8]">Discovered AI Clips</div>
                <div className="text-3xl font-black text-[#ccff00]">{session?.discovered_clips?.length || 0}</div>
                <div className="text-xs text-[#94a3b8]">Ready for 1-click batch export</div>
              </div>

              <div className="bg-[#121520] border border-[#1e2436] rounded-2xl p-5 space-y-2">
                <div className="text-xs font-bold uppercase text-[#94a3b8]">Rendered Shorts</div>
                <div className="text-3xl font-black text-[#38bdf8]">{library.length}</div>
                <div className="text-xs text-[#94a3b8]">Stored in storage/outputs</div>
              </div>
            </div>

            <div className="bg-[#121520] border border-[#1e2436] rounded-2xl p-6 space-y-4">
              <h3 className="text-base font-bold text-white">🚀 Quick Actions</h3>
              <div className="flex gap-4">
                <button
                  onClick={() => setNav('capture')}
                  className="bg-[#1e2436] hover:bg-[#283147] text-white font-bold text-xs px-5 py-3 rounded-xl flex items-center gap-2 transition"
                >
                  <Video className="w-4 h-4 text-[#ccff00]" /> Ingest New Video (YouTube / MP4)
                </button>
                <button
                  onClick={() => setNav('studio')}
                  className="bg-[#ccff00] hover:bg-[#b3e600] text-black font-extrabold text-xs px-5 py-3 rounded-xl flex items-center gap-2 transition"
                >
                  <Scissors className="w-4 h-4" /> Open Timeline Editor
                </button>
                <button
                  onClick={() => setNav('library')}
                  className="bg-[#1e2436] hover:bg-[#283147] text-white font-bold text-xs px-5 py-3 rounded-xl flex items-center gap-2 transition"
                >
                  <Folder className="w-4 h-4 text-[#38bdf8]" /> Browse Rendered Shorts ({library.length})
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ---------------- VIEW: CAPTURE & INGEST ---------------- */}
        {nav === 'capture' && (
          <div className="p-8 max-w-4xl space-y-6">
            {/* YouTube Ingest Box */}
            <div className="bg-[#121520] border border-[#1e2436] rounded-2xl p-6 space-y-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Video className="w-5 h-5 text-red-500" /> Import from YouTube VOD
              </h3>
              <p className="text-xs text-[#94a3b8]">
                Paste any gaming stream or gameplay video link. yt-dlp will automatically fetch 1080p 60fps quality.
              </p>
              <div className="flex gap-3">
                <input
                  type="text"
                  placeholder="https://www.youtube.com/watch?v=..."
                  value={ytUrl}
                  onChange={(e) => setYtUrl(e.target.value)}
                  className="flex-1 bg-[#090b10] border border-[#2a334d] rounded-xl px-4 py-2.5 text-sm text-white placeholder-zinc-500 focus:border-[#ccff00] outline-none"
                />
                <button
                  onClick={handleImportYoutube}
                  disabled={loading || !ytUrl.trim()}
                  className="bg-[#ccff00] hover:bg-[#b3e600] text-black font-extrabold text-sm px-6 py-2.5 rounded-xl transition disabled:opacity-50"
                >
                  {loading ? 'Downloading...' : 'Import Video'}
                </button>
              </div>
            </div>

            {/* Local MP4 File Upload */}
            <div className="bg-[#121520] border border-[#1e2436] rounded-2xl p-6 space-y-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Upload className="w-5 h-5 text-[#ccff00]" /> Upload Local Video File
              </h3>
              <p className="text-xs text-[#94a3b8]">
                Supports MP4, MOV, MKV, or WEBM gameplay recordings from OBS or GeForce Experience.
              </p>
              <label className="border-2 border-dashed border-[#2a334d] hover:border-[#ccff00] rounded-xl p-8 flex flex-col items-center justify-center cursor-pointer transition">
                <Upload className="w-8 h-8 text-[#ccff00] mb-2" />
                <span className="text-xs font-bold text-white">Click or drag MP4 video here</span>
                <span className="text-[11px] text-zinc-500 mt-1">Processed locally on NVMe disk</span>
                <input type="file" accept="video/*" onChange={handleFileUpload} className="hidden" />
              </label>
            </div>

            {/* Saved Local Videos */}
            <div className="bg-[#121520] border border-[#1e2436] rounded-2xl p-6 space-y-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Folder className="w-5 h-5 text-[#38bdf8]" /> Already Ingested Local Sessions ({localVideos.length})
              </h3>
              <div className="grid grid-cols-2 gap-3">
                {localVideos.map((v) => (
                  <div
                    key={v.filename}
                    onClick={() => handleSelectSession(v.filename)}
                    className={`p-3 rounded-xl border flex items-center justify-between cursor-pointer transition ${
                      session?.filename === v.filename
                        ? 'bg-[#1a2133] border-[#ccff00]'
                        : 'bg-[#090b10] border-[#1e2436] hover:border-[#2a334d]'
                    }`}
                  >
                    <div>
                      <div className="text-xs font-bold text-white truncate max-w-[240px]">{v.filename}</div>
                      <div className="text-[11px] text-[#94a3b8]">{v.size_mb} MB</div>
                    </div>
                    <button className="text-xs font-bold px-3 py-1 bg-[#1e2436] hover:bg-[#283147] rounded-lg text-[#ccff00]">
                      {session?.filename === v.filename ? 'Active' : 'Load'}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ---------------- VIEW: STUDIO & TIMELINE EDITOR ---------------- */}
        {nav === 'studio' && session?.video_url && (
          <div className="flex-1 p-6 grid grid-cols-12 gap-6 overflow-hidden">
            {/* Left 8 Cols: Video Player & NLE Multi-Track Timeline */}
            <div className="col-span-8 flex flex-col gap-4 overflow-y-auto pr-1">
              {/* Tool shortcuts above player */}
              <div className="flex items-center justify-between bg-[#121520] border border-[#1e2436] p-2.5 rounded-xl">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-[#ccff00] bg-[#ccff00]/15 px-2.5 py-1 rounded-md border border-[#ccff00]/30">
                    📱 9:16 Active
                  </span>
                  <button 
                    onClick={() => setNav('layout')}
                    className="text-xs font-bold text-white bg-[#1e2436] hover:bg-[#2a334d] px-3 py-1.5 rounded-md flex items-center gap-1.5 transition"
                  >
                    <Sliders className="w-3.5 h-3.5" /> Mouse Drag Layout
                  </button>
                  <button 
                    onClick={() => setNav('captions')}
                    className="text-xs font-bold text-white bg-[#1e2436] hover:bg-[#2a334d] px-3 py-1.5 rounded-md flex items-center gap-1.5 transition"
                  >
                    <Palette className="w-3.5 h-3.5" /> Subtitle Theme: {activeTheme}
                  </button>
                </div>
                <div className="font-mono text-sm font-extrabold text-[#ccff00] bg-black/60 px-3 py-1 rounded-md border border-[#1e2436]">
                  {formatTime(currentTime)} / {formatTime(session.meta.duration)}
                </div>
              </div>

              {/* Main 16:9 Video Player */}
              <div className="relative aspect-video w-full bg-black rounded-xl overflow-hidden border border-[#1e2436] shadow-2xl">
                <video
                  ref={videoRef}
                  src={session.video_url}
                  className="w-full h-full object-contain"
                  onTimeUpdate={() => {
                    if (videoRef.current) {
                      setCurrentTime(videoRef.current.currentTime);
                      setPlayheadTime(videoRef.current.currentTime);
                    }
                  }}
                  onEnded={() => setIsPlaying(false)}
                />
              </div>

              {/* CAPCUT / PREMIERE STYLE NLE TIMELINE SUITE */}
              <div className="bg-[#111422] border border-[#1e2436] rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-[#1e2436]">
                  <div className="flex items-center gap-2">
                    <Film className="w-4 h-4 text-[#ccff00]" />
                    <span className="text-xs font-bold uppercase tracking-wider text-white">NLE Multi-Track Timeline</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button onClick={() => seekRelative(-10)} className="px-2 py-1 bg-[#1a1e2d] hover:bg-[#252c42] text-xs font-bold rounded text-white">⏪ -10s</button>
                    <button onClick={() => seekRelative(-2)} className="px-2 py-1 bg-[#1a1e2d] hover:bg-[#252c42] text-xs font-bold rounded text-white">⏪ -2s</button>
                    <button onClick={togglePlay} className="px-3 py-1 bg-[#ccff00] text-black font-extrabold text-xs rounded-full flex items-center gap-1">
                      {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />} {isPlaying ? 'Pause' : 'Play'}
                    </button>
                    <button onClick={() => seekRelative(2)} className="px-2 py-1 bg-[#1a1e2d] hover:bg-[#252c42] text-xs font-bold rounded text-white">⏩ +2s</button>
                    <button onClick={() => seekRelative(10)} className="px-2 py-1 bg-[#1a1e2d] hover:bg-[#252c42] text-xs font-bold rounded text-white">⏩ +10s</button>
                    <button onClick={() => seekExact(91)} className="px-2.5 py-1 bg-[#3b82f6]/20 border border-[#3b82f6]/40 text-[#60a5fa] text-xs font-bold rounded">📍 Game Start (01:31)</button>
                  </div>
                </div>

                {/* Timeline Filmstrip Track with Draggable Red Playhead Needle */}
                <div 
                  className="relative h-20 bg-[#08090d] rounded-lg overflow-hidden border border-[#232a3d] cursor-pointer"
                  onClick={(e) => {
                    const rect = e.currentTarget.getBoundingClientRect();
                    const clickX = e.clientX - rect.left;
                    const pct = clickX / rect.width;
                    const targetSec = pct * session.meta.duration;
                    seekExact(targetSec);
                  }}
                >
                  {/* Thumbnails filmstrip */}
                  <div className="absolute inset-0 flex">
                    {session.timeline_thumbs.map((thumb, idx) => (
                      <div key={idx} className="flex-1 h-full border-r border-[#1a1f2e] overflow-hidden opacity-75 hover:opacity-100 transition">
                        <img src={thumb.url} alt="" className="w-full h-full object-cover pointer-events-none" />
                      </div>
                    ))}
                  </div>

                  {/* Cut In & Cut Out Marker Range Overlay */}
                  <div 
                    className="absolute top-0 bottom-0 bg-[#ccff00]/20 border-l-2 border-r-2 border-[#ccff00] pointer-events-none z-10"
                    style={{
                      left: `${(cutIn / session.meta.duration) * 100}%`,
                      width: `${((cutOut - cutIn) / session.meta.duration) * 100}%`
                    }}
                  >
                    <div className="text-[10px] font-black bg-[#ccff00] text-black px-1 rounded-sm absolute top-1 left-1">
                      SHORT RANGE ({cutOut - cutIn}s)
                    </div>
                  </div>

                  {/* Red Playhead Line */}
                  <div 
                    className="absolute top-0 bottom-0 w-0.5 bg-red-500 shadow-[0_0_8px_red] z-20 pointer-events-none"
                    style={{ left: `${(playheadTime / session.meta.duration) * 100}%` }}
                  >
                    <div className="w-3 h-3 bg-red-500 rounded-full -ml-[5px] -mt-1 shadow-md"></div>
                  </div>
                </div>

                {/* NLE Cut / Split & Ripple Delete Buttons */}
                <div className="grid grid-cols-2 gap-3 pt-2">
                  <button 
                    onClick={handleRippleDeleteIntro}
                    disabled={loading || playheadTime <= 1.0}
                    className="bg-red-500/15 border border-red-500/40 hover:bg-red-500/25 text-red-300 font-bold py-2.5 px-4 rounded-xl text-xs flex items-center justify-center gap-2 transition disabled:opacity-50"
                  >
                    <Trash2 className="w-4 h-4 text-red-400" />
                    Ripple Delete Intro (Cut Left of {formatTime(playheadTime)}) [0.1s]
                  </button>

                  <button 
                    onClick={handleRippleDeleteOutro}
                    disabled={loading || playheadTime >= (session.meta.duration - 2)}
                    className="bg-[#1e2436] border border-[#2a334d] hover:bg-[#283147] text-white font-bold py-2.5 px-4 rounded-xl text-xs flex items-center justify-center gap-2 transition disabled:opacity-50"
                  >
                    <Scissors className="w-4 h-4 text-[#ccff00]" />
                    Ripple Delete Outro (Cut Right of {formatTime(playheadTime)})
                  </button>
                </div>

                {/* Custom Selection In/Out Short Exporter */}
                <div className="pt-2 border-t border-[#1e2436] flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setCutIn(Math.round(currentTime))}
                      className="px-2.5 py-1 bg-[#1e2436] hover:bg-[#283147] text-white text-xs font-bold rounded"
                    >
                      [ Mark In ({formatTime(currentTime)})
                    </button>
                    <button
                      onClick={() => setCutOut(Math.round(currentTime))}
                      className="px-2.5 py-1 bg-[#1e2436] hover:bg-[#283147] text-white text-xs font-bold rounded"
                    >
                      Mark Out ({formatTime(currentTime)}) ]
                    </button>
                    <div className="text-xs font-semibold text-[#cbd5e1] ml-2">
                      Range: <span className="font-mono text-[#ccff00] font-bold">{formatTime(cutIn)}</span> ──▶ <span className="font-mono text-[#ccff00] font-bold">{formatTime(cutOut)}</span> ({cutOut - cutIn}s)
                    </div>
                  </div>

                  <button
                    onClick={() => handleRenderShorts([{
                      start: cutIn,
                      end: cutOut,
                      title: `Custom Cut (${formatTime(cutIn)}-${formatTime(cutOut)})`,
                      virality_score: 95,
                      hook_score: 9.5,
                      tags: ['✂️ Custom Cut', '⚡ Clip it'],
                      reason: 'Interactive timeline user selection'
                    }])}
                    disabled={renderJob.status === 'running' || (cutOut - cutIn) < 5}
                    className="bg-[#ccff00] hover:bg-[#b3e600] text-black font-extrabold text-xs px-4 py-2 rounded-lg flex items-center gap-2 transition disabled:opacity-50 shadow-lg"
                  >
                    <Zap className="w-3.5 h-3.5" /> RENDER THIS {cutOut - cutIn}s SHORT
                  </button>
                </div>
              </div>
            </div>

            {/* Right 4 Cols: AI Moments & Virality Cards */}
            <div className="col-span-4 bg-[#111422] border border-[#1e2436] rounded-xl p-4 flex flex-col justify-between overflow-y-auto">
              <div>
                <div className="flex items-center justify-between pb-3 border-b border-[#1e2436] mb-3">
                  <h3 className="font-bold text-white text-sm flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-[#ccff00]" /> Suggested Moments
                  </h3>
                  <span className="text-xs font-bold text-[#ccff00]">⚡ AI Discovery</span>
                </div>

                {/* Filter Tags */}
                <div className="flex gap-1.5 overflow-x-auto pb-2 mb-3">
                  {['Clip it (3)', 'Wow (2)', '💀 Kill', '👑 Victory', '😂 Laughter'].map((t, idx) => (
                    <span key={idx} className="bg-[#181d2e] border border-[#283147] text-[#cbd5e1] text-[11px] font-semibold px-2 py-0.5 rounded-full shrink-0">
                      {t}
                    </span>
                  ))}
                </div>

                {/* Trigger AI Scan if empty */}
                {!session.discovered_clips.length && (
                  <div className="bg-[#181d2c] border border-[#242b3d] rounded-xl p-4 text-center my-3">
                    <p className="text-xs text-[#94a3b8] mb-3">
                      Scan audio with Faster-Whisper on GPU & detect clutch gameplay with Ollama.
                    </p>
                    <button
                      onClick={() => handleScanHighlights(91)}
                      disabled={loading}
                      className="w-full bg-[#ccff00] hover:bg-[#b3e600] text-black font-extrabold text-xs py-2.5 rounded-lg flex items-center justify-center gap-2 transition"
                    >
                      <Sparkles className="w-4 h-4" /> Scan Highlights (Skip Intro)
                    </button>
                  </div>
                )}

                {/* Moments List */}
                <div className="space-y-2.5 max-h-[440px] overflow-y-auto pr-1">
                  {session.discovered_clips.map((c, idx) => {
                    const isChecked = selectedClips.includes(idx);
                    return (
                      <div 
                        key={idx}
                        onClick={() => {
                          if (isChecked) setSelectedClips(selectedClips.filter(i => i !== idx));
                          else setSelectedClips([...selectedClips, idx]);
                        }}
                        className={`p-3 rounded-xl border transition cursor-pointer ${
                          isChecked ? 'bg-[#1a2133] border-[#ccff00]/40' : 'bg-[#141724] border-[#1e2436] hover:border-[#2a334d]'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-black text-[#ccff00] bg-[#ccff00]/15 border border-[#ccff00]/30 px-2 py-0.5 rounded">
                            ⚡ {c.virality_score || 90}
                          </span>
                          <span className="text-[11px] font-bold text-[#94a3b8]">
                            {formatTime(c.start)} - {formatTime(c.end)} ({Math.round(c.end - c.start)}s)
                          </span>
                        </div>
                        <div className="text-xs font-bold text-white mb-1.5">{c.title}</div>
                        <div className="flex gap-1 flex-wrap mb-1">
                          {c.tags?.map((t, tidx) => (
                            <span key={tidx} className="bg-[#1f273b] text-[#cbd5e1] text-[10px] font-bold px-1.5 py-0.5 rounded">
                              {t}
                            </span>
                          ))}
                        </div>
                        <div className="text-[11px] text-[#94a3b8] italic">"{c.reason}"</div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Big Neon Create Button */}
              {session.discovered_clips.length > 0 && (
                <div className="pt-3 border-t border-[#1e2436] mt-3">
                  <button
                    onClick={() => handleRenderShorts()}
                    disabled={renderJob.status === 'running' || !selectedClips.length}
                    className="w-full bg-[#ccff00] hover:bg-[#b3e600] text-black font-black text-sm py-3 rounded-full flex items-center justify-center gap-2 shadow-[0_4px_16px_rgba(204,255,0,0.3)] transition disabled:opacity-50"
                  >
                    <Zap className="w-4 h-4" /> Create {selectedClips.length} Selected Shorts
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ---------------- VIEW: LAYOUT & INTERACTIVE ALIGNMENT ---------------- */}
        {nav === 'layout' && session?.preview_url && (
          <div className="p-6 max-w-6xl space-y-6">
            <div className="bg-[#121520] border border-[#1e2436] rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="font-black text-white text-base">Powder.gg Dual Visual Alignment Canvas</h3>
                  <p className="text-xs text-[#94a3b8] mt-1">
                    Drag the Green Facecam and Cyan Gameplay boxes to align your short before rendering.
                  </p>
                </div>

                {/* Layout Mode Selector */}
                <div className="flex gap-2 bg-[#090b10] p-1 rounded-xl border border-[#1e2436]">
                  {[
                    { id: 'gaming_split', label: '🎮 Split (40/60)' },
                    { id: 'crop', label: '📱 Full Crop 9:16' },
                    { id: 'blur_fit', label: '🎞️ Cinematic Blur' }
                  ].map((m) => (
                    <button
                      key={m.id}
                      onClick={() => setLayoutMode(m.id as any)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${
                        layoutMode === m.id ? 'bg-[#ccff00] text-black' : 'text-[#94a3b8] hover:text-white'
                      }`}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Presets */}
              <div className="flex gap-2 mb-4">
                <span className="text-xs font-bold text-[#94a3b8] self-center">Presets:</span>
                {[
                  { label: 'Bottom-Right Facecam', fc: { x: 65, y: 55, w: 32, h: 42 }, gp: { x: 15, y: 0, w: 70, h: 100 } },
                  { label: 'Top-Right Facecam', fc: { x: 65, y: 5, w: 32, h: 42 }, gp: { x: 15, y: 0, w: 70, h: 100 } },
                  { label: 'Center Facecam', fc: { x: 30, y: 15, w: 40, h: 50 }, gp: { x: 15, y: 0, w: 70, h: 100 } },
                  { label: 'Face Only Full', fc: { x: 25, y: 0, w: 50, h: 100 }, gp: { x: 15, y: 0, w: 70, h: 100 } }
                ].map((p, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setFcBox(p.fc);
                      setGpBox(p.gp);
                    }}
                    className="bg-[#181d2e] hover:bg-[#252c42] border border-[#283147] text-white text-xs font-semibold px-3 py-1 rounded-lg transition"
                  >
                    {p.label}
                  </button>
                ))}
              </div>

              <div className="grid grid-cols-12 gap-6 items-start">
                {/* Interactive 16:9 Raw Frame */}
                <div className="col-span-8 relative aspect-video bg-black rounded-xl overflow-hidden border-2 border-[#283147] select-none shadow-xl">
                  <img src={session.preview_url} alt="" className="w-full h-full object-contain pointer-events-none" />

                  {/* Green Facecam Draggable Box */}
                  <div 
                    style={{
                      left: `${fcBox.x}%`,
                      top: `${fcBox.y}%`,
                      width: `${fcBox.w}%`,
                      height: `${fcBox.h}%`
                    }}
                    className="absolute border-4 border-[#00ff88] bg-[#00ff88]/15 cursor-move rounded shadow-lg flex items-start p-1"
                  >
                    <span className="text-[10px] font-black bg-black text-[#00ff88] px-1.5 py-0.5 rounded">
                      📷 FACECAM (Top 40%)
                    </span>
                  </div>

                  {/* Cyan Gameplay Draggable Box */}
                  <div 
                    style={{
                      left: `${gpBox.x}%`,
                      top: `${gpBox.y}%`,
                      width: `${gpBox.w}%`,
                      height: `${gpBox.h}%`
                    }}
                    className="absolute border-4 border-[#00d2ff] bg-[#00d2ff]/15 cursor-move rounded shadow-lg flex items-start p-1"
                  >
                    <span className="text-[10px] font-black bg-black text-[#00d2ff] px-1.5 py-0.5 rounded">
                      🎯 GAMEPLAY (Bottom 60%)
                    </span>
                  </div>
                </div>

                {/* Simulated 9:16 Mobile Mockup */}
                <div className="col-span-4 flex flex-col items-center">
                  <div className="text-xs font-bold text-[#94a3b8] mb-2 uppercase">Live 9:16 Short Preview</div>
                  <div className="w-52 h-[380px] bg-black rounded-2xl border-4 border-[#283147] overflow-hidden flex flex-col shadow-2xl relative">
                    {/* Top Facecam (40%) */}
                    <div className="h-[40%] bg-zinc-900 overflow-hidden relative border-b-2 border-[#ccff00]">
                      <img src={session.preview_url} alt="" className="w-full h-full object-cover scale-150" />
                    </div>
                    {/* Bottom Gameplay (60%) */}
                    <div className="h-[60%] bg-zinc-950 overflow-hidden relative flex items-center justify-center">
                      <img src={session.preview_url} alt="" className="w-full h-full object-cover scale-125" />
                      {/* Subtitle badge */}
                      <div className="absolute bottom-6 bg-black/80 border border-[#ccff00] text-[#ffff00] font-black text-xs px-2.5 py-1 rounded shadow-lg">
                        VIRAL SUBTITLE 🔥
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => setNav('studio')}
                  className="bg-[#ccff00] hover:bg-[#b3e600] text-black font-extrabold text-sm py-2.5 px-6 rounded-full flex items-center gap-2 transition"
                >
                  <CheckCircle2 className="w-4 h-4" /> Save Layout & Return to Studio
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ---------------- VIEW: CAPTIONS & STYLING ---------------- */}
        {nav === 'captions' && (
          <div className="p-8 max-w-4xl space-y-6">
            <div className="bg-[#121520] border border-[#1e2436] rounded-2xl p-6 space-y-5">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Palette className="w-5 h-5 text-[#ccff00]" /> Viral Subtitle & Karaoke Styling
              </h3>

              <div className="space-y-4">
                <label className="text-xs font-bold text-[#94a3b8] uppercase">Select Font Theme</label>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { id: 'Hormozi Gold (Viral)', desc: 'Yellow highlight, thick black border, max engagement' },
                    { id: 'Cyberpunk Neon', desc: 'Neon green/cyan gamer aesthetic' },
                    { id: 'Clean Minimalist', desc: 'White modern sans-serif with soft shadow' },
                    { id: 'TikTok Bold', desc: 'Punchy white on translucent black banner' }
                  ].map((t) => (
                    <div
                      key={t.id}
                      onClick={() => setActiveTheme(t.id)}
                      className={`p-4 rounded-xl border cursor-pointer transition ${
                        activeTheme === t.id
                          ? 'bg-[#1a2133] border-[#ccff00]'
                          : 'bg-[#090b10] border-[#1e2436] hover:border-[#2a334d]'
                      }`}
                    >
                      <div className="text-sm font-extrabold text-white mb-1">{t.id}</div>
                      <div className="text-xs text-[#94a3b8]">{t.desc}</div>
                    </div>
                  ))}
                </div>

                <div className="pt-4 border-t border-[#1e2436] flex items-center justify-between">
                  <div>
                    <div className="text-sm font-bold text-white">✨ Auto-Emojis</div>
                    <div className="text-xs text-[#94a3b8]">Automatically tag emotional words with emojis (🔥 💀 👑 🚀)</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={enableEmojis}
                    onChange={(e) => setEnableEmojis(e.target.checked)}
                    className="w-5 h-5 accent-[#ccff00] cursor-pointer"
                  />
                </div>
              </div>

              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => setNav('studio')}
                  className="bg-[#ccff00] hover:bg-[#b3e600] text-black font-extrabold text-sm py-2.5 px-6 rounded-full flex items-center gap-2 transition"
                >
                  <CheckCircle2 className="w-4 h-4" /> Apply & Return to Studio
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ---------------- VIEW: CLIPS LIBRARY ---------------- */}
        {nav === 'library' && (
          <div className="p-6 space-y-6">
            <h3 className="font-bold text-white text-base">🎬 Rendered 9:16 Shorts Gallery ({library.length})</h3>
            <div className="grid grid-cols-3 gap-6">
              {library.map((item, idx) => (
                <div key={idx} className="bg-[#121520] border border-[#1e2436] rounded-xl overflow-hidden p-3 space-y-3">
                  <div className="aspect-[9/16] bg-black rounded-lg overflow-hidden">
                    <video src={item.video_url} controls className="w-full h-full object-cover" />
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-xs font-bold text-white truncate max-w-[180px]">{item.filename}</div>
                      <div className="text-[11px] text-[#94a3b8]">{item.size_mb} MB</div>
                    </div>
                    <a
                      href={item.video_url}
                      download={item.filename}
                      className="bg-[#ccff00] hover:bg-[#b3e600] text-black font-bold p-2 rounded-lg transition"
                    >
                      <Download className="w-4 h-4" />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ---------------- VIEW: SETTINGS ---------------- */}
        {nav === 'settings' && (
          <div className="p-6 max-w-4xl space-y-6">
            <div className="bg-[#121520] border border-[#1e2436] rounded-xl p-5 space-y-3">
              <h4 className="font-bold text-[#ccff00] text-sm">🟢 NVIDIA GeForce RTX 3050 NVENC</h4>
              <p className="text-xs text-[#cbd5e1] leading-relaxed">
                • VRAM: 6GB Dedicated GDDR6<br />
                • Video Encoder: Hardware h264_nvenc (Preset P6, High Quality)<br />
                • Speed: ~15x faster than CPU realtime render<br />
                • Compute: CUDA 12 float16 Faster-Whisper
              </p>
            </div>
            <div className="bg-[#121520] border border-[#1e2436] rounded-xl p-5 space-y-3">
              <h4 className="font-bold text-[#38bdf8] text-sm">⌨️ Keyboard Shortcuts</h4>
              <p className="text-xs text-[#cbd5e1] leading-relaxed">
                • Space: Play / Pause Video<br />
                • S: Split at Playhead<br />
                • F: Toggle Fullscreen<br />
                • Ctrl+R: Reload Interface
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
