import { useState, useEffect, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { DashboardView } from './components/DashboardView';
import { CaptureView } from './components/CaptureView';
import { StudioView } from './components/StudioView';
import { LayoutEditor } from './components/LayoutEditor';
import { CaptionsView } from './components/CaptionsView';
import { LibraryView } from './components/LibraryView';
import { SettingsView } from './components/SettingsView';
import type {
  ActiveTab,
  SessionData,
  LocalSession,
  LibraryItem,
  ScreenMode,
  GamingLayoutConfig,
  SingleCropConfig,
  SubtitleTheme,
  ClipMoment,
  SystemMetrics
} from './types';
import { RotateCw } from 'lucide-react';

export function App() {
  const [activeTab, setActiveTab] = useState<ActiveTab>('studio');
  const [session, setSession] = useState<SessionData | null>(null);
  const [localSessions, setLocalSessions] = useState<LocalSession[]>([]);
  const [libraryItems, setLibraryItems] = useState<LibraryItem[]>([]);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState<boolean>(true);

  // Layout Configuration
  const [screenMode, setScreenMode] = useState<ScreenMode>('gaming_split');
  const [gamingConfig, setGamingConfig] = useState<GamingLayoutConfig>({
    face_x: 65,
    face_y: 58,
    face_w: 33,
    face_h: 40,
    game_x: 5,
    game_y: 5,
    game_w: 90,
    game_h: 90,
    face_height_pct: 40
  });
  const [singleCropConfig, setSingleCropConfig] = useState<SingleCropConfig>({
    crop_x: 28,
    crop_y: 0,
    crop_w: 44,
    crop_h: 100
  });

  // Captions Configuration
  const [subtitleTheme, setSubtitleTheme] = useState<SubtitleTheme>('Hormozi Gold (Viral)');
  const [enableEmojis, setEnableEmojis] = useState<boolean>(true);

  // Loading & Processing States
  const [isScanning, setIsScanning] = useState(false);
  const [isRendering, setIsRendering] = useState(false);
  const [renderStatusMsg, setRenderStatusMsg] = useState('');
  const [renderProgress, setRenderProgress] = useState(0);

  const pollIntervalRef = useRef<number | null>(null);
  const metricsIntervalRef = useRef<number | null>(null);

  // 1. Initial Load: Fetch Session, Local Files, Library & Real Telemetry
  useEffect(() => {
    fetchSession();
    fetchLocalSessions();
    fetchLibrary();
    fetchSystemMetrics();

    // Poll live system hardware metrics every 3.5 seconds
    metricsIntervalRef.current = window.setInterval(fetchSystemMetrics, 3500);

    return () => {
      if (metricsIntervalRef.current) clearInterval(metricsIntervalRef.current);
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const fetchSystemMetrics = async () => {
    try {
      const res = await fetch('/api/system/metrics');
      if (res.ok) {
        const data: SystemMetrics = await res.json();
        setSystemMetrics(data);
        setMetricsLoading(false);
      }
    } catch (err) {
      console.warn('Could not fetch hardware metrics:', err);
    }
  };

  const fetchSession = async () => {
    try {
      const res = await fetch('/api/session');
      if (res.ok) {
        const data = await res.json();
        setSession(data);
        if (!data.video_path) {
          setActiveTab('capture');
        }
      }
    } catch (err) {
      console.error('Failed to load session:', err);
    }
  };

  const fetchLocalSessions = async () => {
    try {
      const res = await fetch('/api/sessions/local');
      if (res.ok) {
        const data = await res.json();
        setLocalSessions(data);
      }
    } catch (err) {
      console.error('Failed to load local sessions:', err);
    }
  };

  const fetchLibrary = async () => {
    try {
      const res = await fetch('/api/library');
      if (res.ok) {
        const data = await res.json();
        setLibraryItems(data);
      }
    } catch (err) {
      console.error('Failed to load library:', err);
    }
  };

  // 2. Select Local Session
  const handleSelectLocalSession = async (filename: string) => {
    try {
      const res = await fetch('/api/sessions/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename })
      });
      if (res.ok) {
        const data = await res.json();
        setSession(data);
        setActiveTab('studio');
      }
    } catch (err) {
      console.error('Error selecting session:', err);
    }
  };

  // 3. Import YouTube Video
  const handleImportYouTube = async (url: string) => {
    const res = await fetch('/api/import/youtube', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'YouTube import failed');
    }
    const data = await res.json();
    setSession(data);
    fetchLocalSessions();
  };

  // 4. Upload File
  const handleUploadFile = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/api/import/upload', {
      method: 'POST',
      body: formData
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Upload failed');
    }
    const data = await res.json();
    setSession(data);
    fetchLocalSessions();
  };

  // 5. Lossless Trim / Ripple Delete
  const handleTrimVideo = async (startTime: number, endTime: number) => {
    const res = await fetch('/api/video/trim', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ start_time: startTime, end_time: endTime })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Trim failed');
    }
    const data = await res.json();
    setSession(data);
    fetchLocalSessions();
  };

  // 6. Fetch Frame at Timestamp
  const handleFetchFrameAtTime = async (timestamp: number): Promise<string> => {
    const res = await fetch(`/api/frame?timestamp=${timestamp}`);
    if (!res.ok) {
      throw new Error('Could not fetch frame');
    }
    const data = await res.json();
    return data.url;
  };

  // 7. Scan Highlights (Ollama + Whisper)
  const handleScanHighlights = async (
    numClips: number,
    minDur: number,
    maxDur: number,
    scanStart: number
  ) => {
    setIsScanning(true);
    try {
      const res = await fetch('/api/highlights/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          num_clips: numClips,
          min_duration: minDur,
          max_duration: maxDur,
          scan_start: scanStart
        })
      });
      if (res.ok) {
        const data = await res.json();
        setSession((prev) => {
          if (!prev) return null;
          return {
            ...prev,
            discovered_clips: data.clips.map((c: any) => ({ ...c, selected: true }))
          };
        });
      }
    } catch (err) {
      console.error('Scan highlights error:', err);
    } finally {
      setIsScanning(false);
    }
  };

  // 8. Toggle Clip Selection
  const handleToggleClipSelection = (index: number) => {
    setSession((prev) => {
      if (!prev) return null;
      const updated = [...prev.discovered_clips];
      if (updated[index]) {
        updated[index] = {
          ...updated[index],
          selected: updated[index].selected === false ? true : false
        };
      }
      return { ...prev, discovered_clips: updated };
    });
  };

  const handleSelectAllClips = () => {
    setSession((prev) => {
      if (!prev) return null;
      const updated = prev.discovered_clips.map((c) => ({ ...c, selected: true }));
      return { ...prev, discovered_clips: updated };
    });
  };

  const handleSelectClipForPreview = (_clip: ClipMoment) => {
    // Seek or load
  };

  // 9. Trigger Render
  const handleTriggerRender = async () => {
    if (!session?.video_path) return;

    const clipsToRender = (session.discovered_clips || []).filter(
      (c) => c.selected !== false
    );

    if (clipsToRender.length === 0) {
      alert('Please select at least 1 clip moment to render!');
      return;
    }

    setIsRendering(true);
    setRenderStatusMsg('Starting GPU NVENC Render...');
    setRenderProgress(5);

    try {
      const res = await fetch('/api/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          clips: clipsToRender,
          layout_mode: screenMode,
          gaming_config: screenMode === 'gaming_split' ? gamingConfig : undefined,
          single_crop_config: screenMode === 'crop' ? singleCropConfig : undefined,
          subtitle_theme: subtitleTheme,
          enable_emojis: enableEmojis
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Render trigger failed');
      }

      // Start polling status
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = window.setInterval(async () => {
        try {
          const sRes = await fetch('/api/render/status');
          if (sRes.ok) {
            const statusData = await sRes.json();
            setRenderProgress(statusData.progress || 0);
            setRenderStatusMsg(statusData.message || 'Processing...');

            if (statusData.status === 'complete') {
              clearInterval(pollIntervalRef.current!);
              setIsRendering(false);
              fetchLibrary();
              setActiveTab('library');
            } else if (statusData.status === 'error') {
              clearInterval(pollIntervalRef.current!);
              setIsRendering(false);
              alert(`Render Error: ${statusData.message}`);
            }
          }
        } catch (e) {
          console.error('Error polling render status', e);
        }
      }, 1000);
    } catch (err: any) {
      alert(`Could not start render: ${err.message}`);
      setIsRendering(false);
    }
  };

  return (
    <div className="flex h-screen w-screen bg-[#0b0c10] text-gray-200 overflow-hidden font-sans">
      {/* ClipForge Left Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        session={session}
        metrics={systemMetrics}
      />

      {/* Main Studio Work Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden bg-[#0d0e15]">
        {/* Top Header */}
        <Header
          session={session}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          onTriggerRender={handleTriggerRender}
          isRendering={isRendering}
        />

        {/* Global Floating Render Notification */}
        {isRendering && (
          <div className="bg-[#181d2e] border-b border-[#2d344d] px-6 py-2.5 flex items-center justify-between shadow-lg animate-fadeIn z-30">
            <div className="flex items-center gap-3">
              <RotateCw className="w-4 h-4 text-[#ccff00] animate-spin" />
              <div>
                <span className="text-xs font-bold text-white">
                  Rendering 60fps Short:
                </span>{' '}
                <span className="text-xs text-[#ccff00] font-mono">
                  {renderStatusMsg}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-48 bg-[#0e111a] rounded-full h-2 overflow-hidden border border-[#2b334a]">
                <div
                  className="bg-[#ccff00] h-full transition-all duration-300"
                  style={{ width: `${renderProgress}%` }}
                />
              </div>
              <span className="text-xs font-mono font-bold text-[#ccff00]">
                {renderProgress}%
              </span>
            </div>
          </div>
        )}

        {/* Dynamic View Tab Body */}
        <main className="flex-1 overflow-y-auto">
          {activeTab === 'dashboard' && (
            <DashboardView
              session={session}
              localSessions={localSessions}
              metrics={systemMetrics}
              metricsLoading={metricsLoading}
              onSelectLocalSession={handleSelectLocalSession}
              setActiveTab={setActiveTab}
              onOpenStudio={() => setActiveTab('studio')}
            />
          )}

          {activeTab === 'capture' && (
            <CaptureView
              localSessions={localSessions}
              onSelectLocalSession={handleSelectLocalSession}
              onImportYouTube={handleImportYouTube}
              onUploadFile={handleUploadFile}
              setActiveTab={setActiveTab}
            />
          )}

          {activeTab === 'studio' && (
            <StudioView
              session={session}
              onScanHighlights={handleScanHighlights}
              onTrimVideo={handleTrimVideo}
              onSelectClipForPreview={handleSelectClipForPreview}
              onToggleClipSelection={handleToggleClipSelection}
              onSelectAllClips={handleSelectAllClips}
              onTriggerRender={handleTriggerRender}
              setActiveTab={setActiveTab}
              isScanning={isScanning}
              isRendering={isRendering}
            />
          )}

          {activeTab === 'layout' && (
            <LayoutEditor
              session={session}
              screenMode={screenMode}
              setScreenMode={setScreenMode}
              gamingConfig={gamingConfig}
              setGamingConfig={setGamingConfig}
              singleCropConfig={singleCropConfig}
              setSingleCropConfig={setSingleCropConfig}
              onFetchFrameAtTime={handleFetchFrameAtTime}
              setActiveTab={setActiveTab}
            />
          )}

          {activeTab === 'captions' && (
            <CaptionsView
              currentTheme={subtitleTheme}
              setTheme={setSubtitleTheme}
              enableEmojis={enableEmojis}
              setEnableEmojis={setEnableEmojis}
              setActiveTab={setActiveTab}
            />
          )}

          {activeTab === 'library' && (
            <LibraryView
              libraryItems={libraryItems}
              onRefreshLibrary={fetchLibrary}
              setActiveTab={setActiveTab}
            />
          )}

          {activeTab === 'settings' && <SettingsView />}
        </main>
      </div>
    </div>
  );
}

export default App;
