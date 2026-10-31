import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Play,
  Pause,
  Scissors,
  Trash2,
  Zap,
  Sparkles,
  Sliders,
  Volume2,
  VolumeX,
  Clock,
  Flame,
  CheckSquare,
  Square,
  Maximize2,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  RotateCw,
  ZoomIn,
  ZoomOut,
  Maximize,
  Volume1,
  Mic,
  MicOff,
  Crosshair,
  FastForward,
  CornerDownRight,
  Info,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  X,
  Layers,
  Award,
  Gamepad2
} from 'lucide-react';
import type {
  SessionData,
  ClipMoment,
  ActiveTab,
  WaveformData,
  AIScanOptions,
  AIScanJobStatus,
  GameType
} from '../types';

interface StudioViewProps {
  session: SessionData | null;
  onScanHighlights: (options: AIScanOptions) => Promise<void>;
  onTrimVideo: (startTime: number, endTime: number, mode?: string) => Promise<void>;
  onSelectClipForPreview: (clip: ClipMoment) => void;
  onToggleClipSelection: (index: number) => void;
  onSelectAllClips: () => void;
  onTriggerRender: () => void;
  setActiveTab: (tab: ActiveTab) => void;
  isScanning: boolean;
  scanJobStatus?: AIScanJobStatus | null;
  onCancelScan?: () => void;
  ollamaModels?: string[];
  isRendering: boolean;
}

export const StudioView: React.FC<StudioViewProps> = ({
  session,
  onScanHighlights,
  onTrimVideo,
  onSelectClipForPreview,
  onToggleClipSelection,
  onSelectAllClips,
  onTriggerRender,
  setActiveTab,
  isScanning,
  scanJobStatus,
  onCancelScan,
  ollamaModels = ['llama3.2:latest', 'qwen2.5:3b'],
  isRendering
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const timelineContainerRef = useRef<HTMLDivElement>(null);
  const timelineTrackRef = useRef<HTMLDivElement>(null);
  const waveformCanvasRef = useRef<HTMLCanvasElement>(null);

  // Playback & Video State
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1.0);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackRate, setPlaybackRate] = useState<number>(1.0);
  const [isDraggingPlayhead, setIsDraggingPlayhead] = useState(false);

  // Timeline In / Out Markers
  const [inPoint, setInPoint] = useState<number>(0);
  const [outPoint, setOutPoint] = useState<number>(30);
  const [timelineZoom, setTimelineZoom] = useState<number>(1.0); // 1.0x to 6.0x

  // Waveform Data
  const [waveformData, setWaveformData] = useState<WaveformData | null>(null);
  const [waveformLoading, setWaveformLoading] = useState(false);

  // Undo / Redo History for Timeline Range
  const [history, setHistory] = useState<{ inPoint: number; outPoint: number }[]>([]);
  const [redoStack, setRedoStack] = useState<{ inPoint: number; outPoint: number }[]>([]);

  // Pre-roll Direct Trim & Dialog Controls
  const [trimMode, setTrimMode] = useState<'fast' | 'accurate'>('fast');
  const [isTrimming, setIsTrimming] = useState(false);
  const [showPreRollDialog, setShowPreRollDialog] = useState(false);
  const [preRollDeleteSeconds, setPreRollDeleteSeconds] = useState(45);

  // Multi-Signal AI Highlights Engine Settings (Phase 5)
  const [numClips, setNumClips] = useState(3);
  const [minDuration, setMinDuration] = useState(20);
  const [maxDuration, setMaxDuration] = useState(50);
  const [ignoreIntro, setIgnoreIntro] = useState(true);
  const [introSeconds, setIntroSeconds] = useState(45);
  const [gameType, setGameType] = useState<GameType>('generic');
  const [whisperModel, setWhisperModel] = useState('small');
  const [ollamaModel, setOllamaModel] = useState(ollamaModels[0] || 'llama3.2:latest');
  const [sensitivity, setSensitivity] = useState(1.0);
  const [showAdvancedAI, setShowAdvancedAI] = useState(false);
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [hoveredHQSClipId, setHoveredHQSClipId] = useState<string | null>(null);

  const fps = session?.meta?.fps || 30.0;
  const frameTime = 1.0 / fps;
  const totalDur = session?.meta?.duration || duration || 1;

  // 1. Fetch Waveform on session video load
  useEffect(() => {
    if (session?.video_path) {
      fetchWaveform();
    }
  }, [session?.video_path, session?.filename]);

  const fetchWaveform = async () => {
    setWaveformLoading(true);
    try {
      const res = await fetch('/api/media/waveform');
      if (res.ok) {
        const data: WaveformData = await res.json();
        setWaveformData(data);
      }
    } catch (err) {
      console.warn('Could not load waveform:', err);
    } finally {
      setWaveformLoading(false);
    }
  };

  // 2. Render Audio Waveform onto HTML5 Canvas
  useEffect(() => {
    const canvas = waveformCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    if (!waveformData || !waveformData.audio_available || !waveformData.peaks || waveformData.peaks.length === 0) {
      ctx.fillStyle = '#4b5563';
      ctx.font = '10px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(
        waveformLoading ? 'Generating audio waveform...' : '🔇 No audio stream detected',
        width / 2,
        height / 2 + 3
      );
      return;
    }

    const peaks = waveformData.peaks;
    const barCount = peaks.length;
    const barWidth = Math.max(1.5, width / barCount);
    const midY = height / 2;

    const progressPct = currentTime / totalDur;
    const playheadX = progressPct * width;

    // Draw waveform bars
    for (let i = 0; i < barCount; i++) {
      const x = (i / barCount) * width;
      const peakVal = peaks[i];
      const barHeight = Math.max(2, peakVal * (height * 0.85));

      // Color active audio green #ccff00, unplayed audio cyan/muted
      if (x <= playheadX) {
        ctx.fillStyle = '#ccff00';
      } else {
        ctx.fillStyle = '#00d2ff88';
      }

      ctx.fillRect(x, midY - barHeight / 2, barWidth - 0.5, barHeight);
    }
  }, [waveformData, currentTime, totalDur, timelineZoom, waveformLoading]);

  // 3. Timecode Formatter (MM:SS:FF)
  const formatTimecode = (seconds: number) => {
    const safeSecs = Math.max(0, seconds);
    const mins = Math.floor(safeSecs / 60);
    const secs = Math.floor(safeSecs % 60);
    const frameNum = Math.floor((safeSecs % 1) * fps);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}:${frameNum.toString().padStart(2, '0')}`;
  };

  const formatTime = (seconds: number) => {
    const safeSecs = Math.max(0, seconds);
    const mins = Math.floor(safeSecs / 60);
    const secs = Math.floor(safeSecs % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // 4. Video Events
  const handleTimeUpdate = () => {
    if (videoRef.current && !isDraggingPlayhead) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      const d = videoRef.current.duration;
      setDuration(d);
      setOutPoint(Math.min(30, d));
      videoRef.current.playbackRate = playbackRate;
      videoRef.current.volume = isMuted ? 0 : volume;
    }
  };

  const togglePlay = useCallback(() => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
    }
  }, [isPlaying]);

  const seekTo = useCallback((time: number) => {
    const target = Math.max(0, Math.min(totalDur, time));
    if (videoRef.current) {
      videoRef.current.currentTime = target;
    }
    setCurrentTime(target);
  }, [totalDur]);

  const stepFrame = useCallback((frames: number) => {
    if (!videoRef.current) return;
    videoRef.current.pause();
    setIsPlaying(false);
    const nextTime = Math.max(0, Math.min(totalDur, videoRef.current.currentTime + frames * frameTime));
    seekTo(nextTime);
  }, [frameTime, seekTo, totalDur]);

  const seekRelative = useCallback((deltaSec: number) => {
    if (!videoRef.current) return;
    seekTo(videoRef.current.currentTime + deltaSec);
  }, [seekTo]);

  // 5. In / Out Points & Undo/Redo
  const pushHistory = () => {
    setHistory((prev) => [...prev, { inPoint, outPoint }]);
    setRedoStack([]);
  };

  const handleSetInPoint = useCallback(() => {
    pushHistory();
    setInPoint(currentTime);
    if (outPoint <= currentTime) {
      setOutPoint(Math.min(totalDur, currentTime + 30));
    }
  }, [currentTime, outPoint, totalDur]);

  const handleSetOutPoint = useCallback(() => {
    if (currentTime > inPoint) {
      pushHistory();
      setOutPoint(currentTime);
    }
  }, [currentTime, inPoint]);

  const handleClearSelection = () => {
    pushHistory();
    setInPoint(0);
    setOutPoint(totalDur);
  };

  const handleUndo = useCallback(() => {
    if (history.length === 0) return;
    const prev = history[history.length - 1];
    setRedoStack((r) => [...r, { inPoint, outPoint }]);
    setHistory((h) => h.slice(0, h.length - 1));
    setInPoint(prev.inPoint);
    setOutPoint(prev.outPoint);
  }, [history, inPoint, outPoint]);

  const handleRedo = useCallback(() => {
    if (redoStack.length === 0) return;
    const next = redoStack[redoStack.length - 1];
    setHistory((h) => [...h, { inPoint, outPoint }]);
    setRedoStack((r) => r.slice(0, r.length - 1));
    setInPoint(next.inPoint);
    setOutPoint(next.outPoint);
  }, [redoStack, inPoint, outPoint]);

  // Split clip at playhead
  const handleSplitAtPlayhead = () => {
    if (currentTime > inPoint && currentTime < outPoint) {
      pushHistory();
      setOutPoint(currentTime);
    }
  };

  // 6. Global Keyboard Shortcuts Listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is currently typing in an input or textarea
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

      if (e.code === 'Space') {
        e.preventDefault();
        togglePlay();
      } else if (e.code === 'ArrowLeft') {
        e.preventDefault();
        if (e.shiftKey) seekRelative(-2);
        else stepFrame(-1);
      } else if (e.code === 'ArrowRight') {
        e.preventDefault();
        if (e.shiftKey) seekRelative(2);
        else stepFrame(1);
      } else if (e.key === 'j' || e.key === 'J') {
        seekRelative(-2);
      } else if (e.key === 'k' || e.key === 'K') {
        if (videoRef.current) {
          videoRef.current.pause();
          setIsPlaying(false);
        }
      } else if (e.key === 'l' || e.key === 'L') {
        seekRelative(2);
      } else if (e.key === 'i' || e.key === 'I') {
        handleSetInPoint();
      } else if (e.key === 'o' || e.key === 'O') {
        handleSetOutPoint();
      } else if (e.code === 'Home') {
        seekTo(0);
      } else if (e.code === 'End') {
        seekTo(totalDur);
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        if (e.shiftKey) handleRedo();
        else handleUndo();
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') {
        handleRedo();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [togglePlay, seekRelative, stepFrame, handleSetInPoint, handleSetOutPoint, seekTo, totalDur, handleUndo, handleRedo]);

  // 7. Timeline Scrubbing / Dragging
  const handleTimelineMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!timelineTrackRef.current) return;
    setIsDraggingPlayhead(true);
    updateSeekFromEvent(e);
  };

  const updateSeekFromEvent = (e: MouseEvent | React.MouseEvent) => {
    if (!timelineTrackRef.current) return;
    const rect = timelineTrackRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const pct = Math.max(0, Math.min(1, clickX / rect.width));
    seekTo(pct * totalDur);
  };

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (isDraggingPlayhead) {
        updateSeekFromEvent(e);
      }
    };
    const onMouseUp = () => {
      if (isDraggingPlayhead) {
        setIsDraggingPlayhead(false);
      }
    };

    if (isDraggingPlayhead) {
      window.addEventListener('mousemove', onMouseMove);
      window.addEventListener('mouseup', onMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };
  }, [isDraggingPlayhead]);

  // 8. Fullscreen Toggle
  const toggleFullscreen = () => {
    if (!videoRef.current) return;
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      videoRef.current.requestFullscreen().catch(() => {});
    }
  };

  // 9. Pre-Roll Intro Trimming Execution (Fast Lossless 0.1s or NVENC Accurate)
  const executeDirectPreRollTrim = async (targetSeconds?: number) => {
    const cutSec = typeof targetSeconds === 'number' ? targetSeconds : preRollDeleteSeconds;
    if (cutSec < 0.5 || cutSec >= totalDur) return;
    setIsTrimming(true);
    try {
      await onTrimVideo(cutSec, totalDur, trimMode);
      setShowPreRollDialog(false);
      seekTo(0);
    } catch (err: any) {
      alert(`Trim failed: ${err.message}`);
    } finally {
      setIsTrimming(false);
    }
  };

  // 10. AI Highlight Scanning Trigger with Multimodal Parameters
  const handleTriggerScan = () => {
    if (isScanning || !session?.video_path) return;
    onScanHighlights({
      num_clips: numClips,
      min_duration: minDuration,
      max_duration: maxDuration,
      scan_start: ignoreIntro ? introSeconds : 0.0,
      game_type: gameType,
      whisper_model: whisperModel,
      ollama_model: ollamaModel,
      sensitivity: sensitivity
    });
  };

  const clips = session?.discovered_clips || [];

  // Filter Categories & Counts matching Streamlit / gaming signals
  const filterCounts = {
    all: clips.length,
    kill: clips.filter(c => (c.tags?.some(t => t.toLowerCase().includes('kill')) || c.reason?.toLowerCase().includes('kill'))).length,
    victory: clips.filter(c => (c.tags?.some(t => t.toLowerCase().includes('victory') || t.toLowerCase().includes('clutch')) || c.reason?.toLowerCase().includes('win'))).length,
    laughter: clips.filter(c => (c.tags?.some(t => t.toLowerCase().includes('laugh')) || c.reason?.toLowerCase().includes('laugh'))).length,
    clutch: clips.filter(c => (c.tags?.some(t => t.toLowerCase().includes('clutch')) || c.reason?.toLowerCase().includes('clutch'))).length,
    loud: clips.filter(c => (c.tags?.some(t => t.toLowerCase().includes('loud') || t.toLowerCase().includes('scream')) || c.reason?.toLowerCase().includes('scream'))).length,
  };

  const filteredClips = clips.filter((c) => {
    if (activeFilter === 'all') return true;
    if (activeFilter === 'kill') {
      return c.tags?.some(t => t.toLowerCase().includes('kill')) || c.reason?.toLowerCase().includes('kill');
    }
    if (activeFilter === 'victory') {
      return c.tags?.some(t => t.toLowerCase().includes('victory') || t.toLowerCase().includes('clutch')) || c.reason?.toLowerCase().includes('win');
    }
    if (activeFilter === 'laughter') {
      return c.tags?.some(t => t.toLowerCase().includes('laugh')) || c.reason?.toLowerCase().includes('laugh');
    }
    if (activeFilter === 'clutch') {
      return c.tags?.some(t => t.toLowerCase().includes('clutch')) || c.reason?.toLowerCase().includes('clutch');
    }
    if (activeFilter === 'loud') {
      return c.tags?.some(t => t.toLowerCase().includes('loud') || t.toLowerCase().includes('scream')) || c.reason?.toLowerCase().includes('scream');
    }
    return c.label?.toLowerCase().includes(activeFilter.toLowerCase()) || c.reason?.toLowerCase().includes(activeFilter.toLowerCase());
  });

  const selectedClipsCount = clips.filter((c) => c.selected !== false).length;

  return (
    <div className="p-6 max-w-[1650px] mx-auto space-y-6 animate-fadeIn">
      {/* Main Grid: Left Video Player & Professional NLE Timeline (67%) | Right AI Clips Panel (33%) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Player + Professional Multi-Track Timeline (8 cols) */}
        <div className="lg:col-span-8 space-y-4">
          {/* ======================================================== */}
          {/* 16:9 VIDEO PLAYER WITH FRAME-ACCURATE TRANSPORT         */}
          {/* ======================================================== */}
          <div className="relative bg-black rounded-2xl overflow-hidden border border-[#232738] shadow-2xl group">
            {session?.video_url ? (
              <video
                ref={videoRef}
                src={session.video_url}
                className="w-full aspect-video object-contain bg-black"
                onTimeUpdate={handleTimeUpdate}
                onLoadedMetadata={handleLoadedMetadata}
                onClick={togglePlay}
              />
            ) : (
              <div className="w-full aspect-video flex flex-col items-center justify-center text-gray-500 bg-[#0d0f17]">
                <Clock className="w-12 h-12 mb-2 text-gray-600" />
                <p className="text-sm font-semibold">No video loaded in session</p>
                <button
                  onClick={() => setActiveTab('capture')}
                  className="mt-3 px-4 py-2 bg-[#ccff00] text-black text-xs font-bold rounded-lg shadow-lg hover:bg-[#b8e600]"
                >
                  Import Gameplay Video
                </button>
              </div>
            )}

            {/* Top Overlay Buttons */}
            <div className="absolute top-4 right-4 flex items-center gap-2">
              <button
                onClick={() => setActiveTab('layout')}
                className="px-3 py-1.5 rounded-lg bg-black/60 hover:bg-black/90 backdrop-blur-md text-white text-xs font-semibold flex items-center gap-1.5 border border-white/10 shadow-lg"
              >
                <Sliders className="w-3.5 h-3.5 text-[#00d2ff]" />
                <span>Adjust 9:16 Layout</span>
              </button>
              <button
                onClick={toggleFullscreen}
                className="p-1.5 rounded-lg bg-black/60 hover:bg-black/90 backdrop-blur-md text-white text-xs border border-white/10 shadow-lg"
                title="Fullscreen"
              >
                <Maximize2 className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Bottom In-Player Controls Bar */}
            <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/95 via-black/60 to-transparent flex items-center justify-between text-white text-xs">
              {/* Left Transport */}
              <div className="flex items-center gap-3">
                <button
                  onClick={togglePlay}
                  className="p-1.5 rounded-lg hover:bg-white/20 transition-colors"
                  title="Play / Pause (Space)"
                >
                  {isPlaying ? (
                    <Pause className="w-4 h-4 fill-white" />
                  ) : (
                    <Play className="w-4 h-4 fill-white" />
                  )}
                </button>

                {/* Frame Step Backward */}
                <button
                  onClick={() => stepFrame(-1)}
                  className="p-1 rounded hover:bg-white/20 text-gray-300 hover:text-white"
                  title="Previous Frame (Left Arrow)"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>

                {/* Frame Step Forward */}
                <button
                  onClick={() => stepFrame(1)}
                  className="p-1 rounded hover:bg-white/20 text-gray-300 hover:text-white"
                  title="Next Frame (Right Arrow)"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>

                {/* Precise Timecode (MM:SS:FF) */}
                <div className="font-mono text-xs font-bold text-white bg-black/50 px-2 py-0.5 rounded border border-white/10 flex items-center gap-1">
                  <span className="text-[#ccff00]">{formatTimecode(currentTime)}</span>
                  <span className="text-gray-400">/</span>
                  <span className="text-gray-300">{formatTimecode(totalDur)}</span>
                </div>

                {/* Volume & Mute */}
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => {
                      if (videoRef.current) {
                        videoRef.current.muted = !isMuted;
                        setIsMuted(!isMuted);
                      }
                    }}
                    className="p-1 rounded hover:bg-white/20 transition-colors"
                  >
                    {isMuted || volume === 0 ? (
                      <VolumeX className="w-4 h-4 text-red-400" />
                    ) : volume < 0.5 ? (
                      <Volume1 className="w-4 h-4" />
                    ) : (
                      <Volume2 className="w-4 h-4" />
                    )}
                  </button>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={isMuted ? 0 : volume}
                    onChange={(e) => {
                      const v = parseFloat(e.target.value);
                      setVolume(v);
                      setIsMuted(v === 0);
                      if (videoRef.current) {
                        videoRef.current.volume = v;
                        videoRef.current.muted = v === 0;
                      }
                    }}
                    className="w-16 h-1 accent-[#ccff00] cursor-pointer"
                  />
                </div>
              </div>

              {/* Right Controls: Playback Speed & Source Specs */}
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1 bg-black/40 px-2 py-1 rounded-md border border-white/10">
                  <span className="text-[10px] text-gray-400">Speed:</span>
                  <select
                    value={playbackRate}
                    onChange={(e) => {
                      const rate = parseFloat(e.target.value);
                      setPlaybackRate(rate);
                      if (videoRef.current) videoRef.current.playbackRate = rate;
                    }}
                    className="bg-transparent text-[#ccff00] font-bold text-xs focus:outline-none cursor-pointer"
                  >
                    <option value={0.5} className="bg-[#121522] text-white">0.5x</option>
                    <option value={1.0} className="bg-[#121522] text-white">1.0x</option>
                    <option value={1.5} className="bg-[#121522] text-white">1.5x</option>
                    <option value={2.0} className="bg-[#121522] text-white">2.0x</option>
                  </select>
                </div>

                <span className="text-[10px] bg-[#ccff00]/20 text-[#ccff00] px-2 py-0.5 rounded font-bold uppercase font-mono">
                  {Math.round(fps)} FPS Source
                </span>
              </div>
            </div>
          </div>

          {/* ======================================================== */}
          {/* PROFESSIONAL MULTI-TRACK NLE TIMELINE                   */}
          {/* ======================================================== */}
          <div className="bg-[#121522] border border-[#232738] rounded-2xl p-5 space-y-4 shadow-xl">
            {/* Timeline Toolbar: Mark In/Out, Zoom, Undo/Redo */}
            <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-[#1c2132]">
              {/* Left Transport Seekers */}
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => seekTo(0)}
                  className="px-2 py-1 text-xs font-mono font-bold text-gray-400 hover:text-white rounded bg-[#171a28] hover:bg-[#22273a] border border-[#293047]"
                  title="Go to Start (Home)"
                >
                  ⏮ 0:00
                </button>
                <button
                  onClick={() => seekRelative(-10)}
                  className="px-2 py-1 text-xs font-bold text-gray-300 hover:text-white rounded bg-[#171a28] hover:bg-[#22273a] border border-[#293047]"
                  title="Seek -10s"
                >
                  -10s
                </button>
                <button
                  onClick={() => seekRelative(-2)}
                  className="px-2 py-1 text-xs font-bold text-gray-300 hover:text-white rounded bg-[#171a28] hover:bg-[#22273a] border border-[#293047]"
                  title="Seek -2s"
                >
                  -2s
                </button>
                <button
                  onClick={togglePlay}
                  className="px-3 py-1 bg-[#ccff00] text-black font-extrabold rounded text-xs hover:bg-[#b8e600] transition-transform active:scale-95"
                >
                  {isPlaying ? 'PAUSE' : 'PLAY'}
                </button>
                <button
                  onClick={() => seekRelative(2)}
                  className="px-2 py-1 text-xs font-bold text-gray-300 hover:text-white rounded bg-[#171a28] hover:bg-[#22273a] border border-[#293047]"
                  title="Seek +2s"
                >
                  +2s
                </button>
                <button
                  onClick={() => seekRelative(10)}
                  className="px-2 py-1 text-xs font-bold text-gray-300 hover:text-white rounded bg-[#171a28] hover:bg-[#22273a] border border-[#293047]"
                  title="Seek +10s"
                >
                  +10s
                </button>
              </div>

              {/* Center: In / Out Markers & Split */}
              <div className="flex items-center gap-1.5">
                <button
                  onClick={handleSetInPoint}
                  className="px-2.5 py-1 text-xs font-bold rounded-lg bg-[#1a1f30] hover:bg-[#252c44] text-[#ccff00] border border-[#2b334d]"
                  title="Mark In (I)"
                >
                  [ In ({formatTime(inPoint)})
                </button>
                <button
                  onClick={handleSetOutPoint}
                  className="px-2.5 py-1 text-xs font-bold rounded-lg bg-[#1a1f30] hover:bg-[#252c44] text-[#00d2ff] border border-[#2b334d]"
                  title="Mark Out (O)"
                >
                  Out ({formatTime(outPoint)}) ]
                </button>
                <button
                  onClick={handleSplitAtPlayhead}
                  disabled={currentTime <= inPoint || currentTime >= outPoint}
                  className="px-2.5 py-1 text-xs font-bold rounded-lg bg-[#1a1f30] hover:bg-[#252c44] text-gray-300 border border-[#2b334d] disabled:opacity-40"
                  title="Split range at playhead"
                >
                  <Scissors className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={handleClearSelection}
                  className="px-2 py-1 text-[11px] text-gray-400 hover:text-white rounded"
                  title="Clear In/Out Selection"
                >
                  Clear
                </button>
              </div>

              {/* Right: Zoom & History */}
              <div className="flex items-center gap-2">
                <button
                  onClick={handleUndo}
                  disabled={history.length === 0}
                  className="p-1 rounded bg-[#171a28] text-gray-400 hover:text-white disabled:opacity-30 border border-[#293047]"
                  title="Undo (Ctrl+Z)"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={handleRedo}
                  disabled={redoStack.length === 0}
                  className="p-1 rounded bg-[#171a28] text-gray-400 hover:text-white disabled:opacity-30 border border-[#293047]"
                  title="Redo (Ctrl+Y)"
                >
                  <RotateCw className="w-3.5 h-3.5" />
                </button>

                <div className="h-4 w-px bg-[#262c3f] mx-1" />

                {/* Timeline Zoom Controls */}
                <div className="flex items-center gap-1 bg-[#10131d] px-2 py-0.5 rounded-lg border border-[#242b3e]">
                  <button
                    onClick={() => setTimelineZoom((z) => Math.max(1.0, z - 0.5))}
                    className="p-1 text-gray-400 hover:text-white"
                    title="Zoom Out"
                  >
                    <ZoomOut className="w-3.5 h-3.5" />
                  </button>
                  <span className="text-[10px] font-mono font-bold text-gray-300 w-7 text-center">
                    {timelineZoom.toFixed(1)}x
                  </span>
                  <button
                    onClick={() => setTimelineZoom((z) => Math.min(5.0, z + 0.5))}
                    className="p-1 text-gray-400 hover:text-white"
                    title="Zoom In"
                  >
                    <ZoomIn className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setTimelineZoom(1.0)}
                    className="text-[10px] font-bold text-[#ccff00] hover:underline ml-1"
                    title="Fit to Screen"
                  >
                    Fit
                  </button>
                </div>
              </div>
            </div>

            {/* Scrollable Multi-Track Timeline Container */}
            <div
              ref={timelineContainerRef}
              className="relative overflow-x-auto overflow-y-hidden border border-[#252b3e] rounded-xl bg-[#090b10] select-none"
            >
              <div
                ref={timelineTrackRef}
                onMouseDown={handleTimelineMouseDown}
                style={{ width: `${timelineZoom * 100}%` }}
                className="relative cursor-pointer min-w-full"
              >
                {/* Track 1: Filmstrip Video Track */}
                <div className="relative h-16 border-b border-[#1a1f30] overflow-hidden flex opacity-85 hover:opacity-95 transition-opacity">
                  {session?.timeline_thumbs && session.timeline_thumbs.length > 0 ? (
                    session.timeline_thumbs.map((thumb, idx) => (
                      <div
                        key={idx}
                        className="flex-1 h-full border-r border-[#1a1f30] overflow-hidden relative"
                      >
                        <img
                          src={thumb.url}
                          alt={`Thumb ${idx}`}
                          className="w-full h-full object-cover pointer-events-none"
                        />
                        <span className="absolute bottom-1 right-1 text-[8px] bg-black/70 text-gray-300 px-1 rounded font-mono">
                          {formatTime(thumb.timestamp)}
                        </span>
                      </div>
                    ))
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-xs text-gray-600 font-mono">
                      Filmstrip Video Track
                    </div>
                  )}
                </div>

                {/* Track 2: Audio Waveform Canvas */}
                <div className="relative h-12 bg-[#0c0e17] overflow-hidden flex items-center">
                  <canvas
                    ref={waveformCanvasRef}
                    width={1200 * timelineZoom}
                    height={48}
                    className="w-full h-full pointer-events-none"
                  />
                </div>

                {/* Marked Range Highlight (Between In and Out) */}
                {outPoint > inPoint && (
                  <div
                    className="absolute top-0 bottom-0 bg-[#ccff00]/15 border-x-2 border-[#ccff00] pointer-events-none z-10"
                    style={{
                      left: `${(inPoint / totalDur) * 100}%`,
                      width: `${((outPoint - inPoint) / totalDur) * 100}%`
                    }}
                  >
                    <div className="absolute top-1 left-1.5 text-[9px] font-black text-[#ccff00] bg-black/80 px-1.5 py-0.5 rounded shadow">
                      Selected Range: {Math.round(outPoint - inPoint)}s
                    </div>
                  </div>
                )}

                {/* AI Discovered Moments Marker Pills */}
                {clips.map((clip, idx) => (
                  <div
                    key={idx}
                    onClick={(e) => {
                      e.stopPropagation();
                      seekTo(clip.start);
                    }}
                    className="absolute top-0 bottom-0 bg-purple-500/20 hover:bg-purple-500/40 border-x border-purple-400 cursor-pointer pointer-events-auto z-10"
                    style={{
                      left: `${(clip.start / totalDur) * 100}%`,
                      width: `${((clip.end - clip.start) / totalDur) * 100}%`
                    }}
                    title={`AI Highlight #${idx + 1}: ${clip.reason}`}
                  >
                    <div className="absolute bottom-1 left-1 text-[8px] bg-purple-900/90 text-purple-200 px-1 rounded font-bold shadow">
                      ⚡ #{idx + 1}
                    </div>
                  </div>
                ))}

                {/* Red Draggable Playhead Needle */}
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-20 pointer-events-none shadow-[0_0_8px_rgba(239,68,68,0.9)]"
                  style={{ left: `${(currentTime / totalDur) * 100}%` }}
                >
                  <div className="w-3 h-3 -ml-1.5 bg-red-500 rounded-sm rotate-45 transform -translate-y-1/2 shadow-lg" />
                </div>
              </div>
            </div>

            {/* Quick Actions: Pre-Roll Intro Cut (Screenshot 2 Match) & Custom Range Short */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
              {/* Pre-Roll Intro Cut Action Card (Lossless 0.1s Fast or Frame-Accurate) */}
              <div className="p-4 rounded-xl bg-[#141724] border-2 border-rose-500/40 space-y-3 shadow-lg relative overflow-hidden">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Scissors className="w-4 h-4 text-rose-400" />
                    <span className="text-xs font-extrabold text-white">
                      Cut & Delete Pre-Roll Intro
                    </span>
                  </div>
                  <span className="text-[10px] font-mono font-bold bg-rose-500/20 text-rose-300 px-2 py-0.5 rounded border border-rose-500/30">
                    Lossless 0.1s Fast
                  </span>
                </div>

                <p className="text-[11px] text-gray-300 leading-tight">
                  Cut off the talking webcam intro and delete everything before your desired timestamp. The trimmed video becomes your new active project!
                </p>

                {/* Second Counter Stepper [-] [ 45 ] [+] & Playhead Sync */}
                <div className="space-y-1.5 pt-1">
                  <div className="flex items-center justify-between text-[11px] text-gray-300">
                    <span>Delete video timeline before (seconds):</span>
                    <button
                      type="button"
                      onClick={() => setPreRollDeleteSeconds(Math.round(currentTime))}
                      className="text-[10px] text-[#ccff00] hover:underline font-mono"
                    >
                      Use Playhead ({formatTime(currentTime)})
                    </button>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setPreRollDeleteSeconds((s) => Math.max(1, s - 5))}
                      className="w-8 h-8 rounded-lg bg-[#1c2236] hover:bg-[#28314e] text-white font-bold text-sm border border-[#2b334d] flex items-center justify-center transition-colors"
                      title="Step -5s"
                    >
                      -
                    </button>
                    <input
                      type="number"
                      min="1"
                      max={Math.max(1, Math.round(totalDur - 2))}
                      value={preRollDeleteSeconds}
                      onChange={(e) => setPreRollDeleteSeconds(Math.max(1, parseInt(e.target.value) || 1))}
                      className="flex-1 h-8 bg-[#0b0e17] border border-[#2b334d] rounded-lg px-2 text-center text-xs text-white font-mono font-bold focus:border-rose-400 focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => setPreRollDeleteSeconds((s) => Math.min(Math.round(totalDur - 2), s + 5))}
                      className="w-8 h-8 rounded-lg bg-[#1c2236] hover:bg-[#28314e] text-white font-bold text-sm border border-[#2b334d] flex items-center justify-center transition-colors"
                      title="Step +5s"
                    >
                      +
                    </button>

                    <button
                      type="button"
                      onClick={() => executeDirectPreRollTrim()}
                      disabled={isTrimming || !session?.video_path}
                      className="px-4 h-8 rounded-lg bg-[#ccff00] text-black font-extrabold text-xs hover:bg-[#b8e600] disabled:opacity-50 flex items-center gap-1.5 shadow-md shadow-[#ccff00]/10 transition-transform hover:scale-[1.02]"
                    >
                      <Scissors className="w-3.5 h-3.5" />
                      <span>{isTrimming ? 'Cutting...' : 'Cut & Delete Intro'}</span>
                    </button>
                  </div>
                </div>

                {/* Subtext info pill */}
                <div className="flex items-center justify-between text-[10px] text-gray-400 font-mono pt-0.5 border-t border-[#23283c]">
                  <span>
                    📍 New video start: <strong className="text-[#ccff00]">{formatTime(preRollDeleteSeconds)}</strong>
                  </span>
                  <span>
                    Deleted duration: <strong>{preRollDeleteSeconds}s</strong>
                  </span>
                </div>
              </div>

              {/* Export Selected In-Out Range as Short */}
              <div className="p-4 rounded-xl bg-gradient-to-r from-[#ccff00]/10 via-[#00d2ff]/10 to-transparent border border-[#ccff00]/30 space-y-3 shadow-lg flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <Zap className="w-4 h-4 text-[#ccff00]" />
                      <span className="text-xs font-extrabold text-white">Custom Range Short</span>
                    </div>
                    <span className="text-[10px] text-[#ccff00] font-mono font-bold bg-[#ccff00]/15 px-2 py-0.5 rounded border border-[#ccff00]/30">
                      {Math.round(outPoint - inPoint)}s Selected
                    </span>
                  </div>

                  <p className="text-[11px] text-gray-300 leading-tight">
                    Instantly render this custom in-out range with 9:16 layout, auto facecam zoom and Hormozi viral captions.
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between text-[10px] font-mono text-gray-400">
                    <span>Range: {formatTime(inPoint)} → {formatTime(outPoint)}</span>
                    <span>Target: 9:16 vertical</span>
                  </div>

                  <button
                    onClick={() => {
                      onSelectClipForPreview({
                        start: inPoint,
                        end: outPoint,
                        score: 9.5,
                        reason: `Timeline Selection (${formatTime(inPoint)} - ${formatTime(outPoint)})`
                      });
                      onTriggerRender();
                    }}
                    disabled={isRendering || outPoint <= inPoint}
                    className="w-full py-2.5 px-3 rounded-lg bg-[#ccff00] text-black font-extrabold text-xs hover:bg-[#b8e600] transition-all flex items-center justify-center gap-2 shadow-lg shadow-[#ccff00]/15 disabled:opacity-50"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>Render In/Out Short ({Math.round(outPoint - inPoint)}s)</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: AI Suggested Moments & Clip Discovery (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-[#121522] border border-[#232738] rounded-2xl p-5 shadow-xl space-y-4">
            {/* Header with Glowing AI Discovery Pill */}
            <div className="flex items-center justify-between pb-3 border-b border-[#1f2438]">
              <div className="flex items-center gap-2">
                <Flame className="w-5 h-5 text-[#ccff00]" />
                <h3 className="font-extrabold text-sm text-white">AI Suggested Moments</h3>
              </div>
              <span className="text-[11px] font-mono font-bold bg-[#ccff00]/15 text-[#ccff00] px-2 py-0.5 rounded-full border border-[#ccff00]/30 flex items-center gap-1 shadow-sm">
                <Zap className="w-3 h-3 fill-current" />
                <span>AI Discovery</span>
              </span>
            </div>

            {/* Filter Pills matching Screenshot 1 (All, Kill, Victory, Laughter, Clutch, Loud) */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none text-[11px] font-bold">
              <button
                onClick={() => setActiveFilter('all')}
                className={`px-2.5 py-1 rounded-full whitespace-nowrap transition-all ${
                  activeFilter === 'all'
                    ? 'bg-[#ccff00] text-black font-extrabold shadow'
                    : 'bg-[#181d2c] text-gray-400 hover:text-white'
                }`}
              >
                All ({filterCounts.all})
              </button>
              <button
                onClick={() => setActiveFilter('kill')}
                className={`px-2.5 py-1 rounded-full whitespace-nowrap transition-all flex items-center gap-1 ${
                  activeFilter === 'kill'
                    ? 'bg-rose-500 text-white font-extrabold shadow'
                    : 'bg-[#181d2c] text-gray-400 hover:text-white'
                }`}
              >
                <span>💀 Kill</span>
                {filterCounts.kill > 0 && <span className="text-[9px] opacity-80">({filterCounts.kill})</span>}
              </button>
              <button
                onClick={() => setActiveFilter('victory')}
                className={`px-2.5 py-1 rounded-full whitespace-nowrap transition-all flex items-center gap-1 ${
                  activeFilter === 'victory'
                    ? 'bg-amber-500 text-black font-extrabold shadow'
                    : 'bg-[#181d2c] text-gray-400 hover:text-white'
                }`}
              >
                <span>👑 Victory</span>
                {filterCounts.victory > 0 && <span className="text-[9px] opacity-80">({filterCounts.victory})</span>}
              </button>
              <button
                onClick={() => setActiveFilter('laughter')}
                className={`px-2.5 py-1 rounded-full whitespace-nowrap transition-all flex items-center gap-1 ${
                  activeFilter === 'laughter'
                    ? 'bg-yellow-400 text-black font-extrabold shadow'
                    : 'bg-[#181d2c] text-gray-400 hover:text-white'
                }`}
              >
                <span>😂 Laughter</span>
                {filterCounts.laughter > 0 && <span className="text-[9px] opacity-80">({filterCounts.laughter})</span>}
              </button>
              <button
                onClick={() => setActiveFilter('clutch')}
                className={`px-2.5 py-1 rounded-full whitespace-nowrap transition-all flex items-center gap-1 ${
                  activeFilter === 'clutch'
                    ? 'bg-purple-500 text-white font-extrabold shadow'
                    : 'bg-[#181d2c] text-gray-400 hover:text-white'
                }`}
              >
                <span>⚡ Clutch</span>
                {filterCounts.clutch > 0 && <span className="text-[9px] opacity-80">({filterCounts.clutch})</span>}
              </button>
              <button
                onClick={() => setActiveFilter('loud')}
                className={`px-2.5 py-1 rounded-full whitespace-nowrap transition-all flex items-center gap-1 ${
                  activeFilter === 'loud'
                    ? 'bg-cyan-500 text-black font-extrabold shadow'
                    : 'bg-[#181d2c] text-gray-400 hover:text-white'
                }`}
              >
                <span>🔊 Loud</span>
                {filterCounts.loud > 0 && <span className="text-[9px] opacity-80">({filterCounts.loud})</span>}
              </button>
            </div>

            {/* AI Highlight Scanner Trigger Card (Screenshot 1 & 2 Match) */}
            <div className="bg-[#0e111a] border border-[#1f2438] rounded-xl p-4 space-y-3.5 shadow-inner">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[#ccff00]" />
                <h4 className="font-extrabold text-xs text-white">AI Highlight Scanner</h4>
              </div>

              <p className="text-[11px] text-gray-400 leading-tight">
                Scans audio with Faster-Whisper on GPU & uses Ollama to find viral hooks, clutch gameplay, and laughter.
              </p>

              {/* Game Preset Selector */}
              <div className="space-y-1">
                <label className="text-[11px] text-gray-300 font-semibold flex items-center justify-between">
                  <span>Game Intelligence Preset:</span>
                  <span className="text-[#ccff00] font-mono text-[10px] uppercase font-bold">
                    {gameType}
                  </span>
                </label>
                <select
                  value={gameType}
                  onChange={(e) => setGameType(e.target.value as GameType)}
                  className="w-full bg-[#171b29] border border-[#2b334a] rounded-lg px-2.5 py-1.5 text-xs text-white font-medium focus:border-[#ccff00] focus:outline-none"
                >
                  <option value="generic">🎯 Generic Gaming Stream</option>
                  <option value="valorant">🎯 Valorant (Headshots, Clutches, Defuse)</option>
                  <option value="cs2">🔫 Counter-Strike 2 (Aces, Bomb Plant)</option>
                  <option value="fortnite">🏹 Fortnite (Victory Royale, Snipes)</option>
                  <option value="pubg">🪂 PUBG (Chicken Dinner, Vehicle Kills)</option>
                  <option value="minecraft">⛏️ Minecraft (Diamond finds, Mob Fights)</option>
                  <option value="gtav">🚗 GTA V (Heists, Car Chases, Chaos)</option>
                </select>
              </div>

              {/* Moments Count & Duration Sliders */}
              <div className="grid grid-cols-2 gap-3 pt-1">
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[11px] text-gray-300 font-semibold">
                    <span>Moments Count:</span>
                    <span className="text-[#ccff00] font-mono font-bold">{numClips}</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="8"
                    value={numClips}
                    onChange={(e) => setNumClips(parseInt(e.target.value))}
                    className="w-full accent-[#ccff00]"
                  />
                </div>

                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[11px] text-gray-300 font-semibold">
                    <span>Target Duration:</span>
                    <span className="text-[#ccff00] font-mono font-bold">{minDuration} - {maxDuration}s</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <input
                      type="range"
                      min="15"
                      max="35"
                      value={minDuration}
                      onChange={(e) => setMinDuration(parseInt(e.target.value))}
                      className="w-1/2 accent-[#ccff00]"
                      title="Min duration"
                    />
                    <input
                      type="range"
                      min="35"
                      max="60"
                      value={maxDuration}
                      onChange={(e) => setMaxDuration(parseInt(e.target.value))}
                      className="w-1/2 accent-[#00d2ff]"
                      title="Max duration"
                    />
                  </div>
                </div>
              </div>

              {/* Pre-Roll Intro Scan Option (Screenshot 2 Match) */}
              <div className="space-y-1.5 pt-1 border-t border-[#1a1f30]">
                <label className="flex items-center gap-2 text-xs text-gray-200 cursor-pointer font-medium">
                  <input
                    type="checkbox"
                    checked={ignoreIntro}
                    onChange={(e) => setIgnoreIntro(e.target.checked)}
                    className="rounded accent-[#ccff00]"
                  />
                  <span>✂️ Ignore Pre-Roll Intro in AI Scan</span>
                </label>

                {ignoreIntro && (
                  <div className="space-y-1 bg-[#131724] p-2 rounded-lg border border-[#20273c]">
                    <div className="flex items-center justify-between text-[11px] text-gray-300">
                      <span>Scan speech only after (seconds):</span>
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => setIntroSeconds((s) => Math.max(0, s - 5))}
                          className="w-5 h-5 rounded bg-[#1c2236] text-gray-300 hover:text-white text-xs flex items-center justify-center font-bold"
                        >
                          -
                        </button>
                        <input
                          type="number"
                          min="0"
                          max="300"
                          value={introSeconds}
                          onChange={(e) => setIntroSeconds(parseInt(e.target.value) || 0)}
                          className="w-12 bg-[#0b0e17] border border-[#2b334a] rounded px-1 text-center text-xs text-white font-mono font-bold"
                        />
                        <button
                          type="button"
                          onClick={() => setIntroSeconds((s) => s + 5)}
                          className="w-5 h-5 rounded bg-[#1c2236] text-gray-300 hover:text-white text-xs flex items-center justify-center font-bold"
                        >
                          +
                        </button>
                      </div>
                    </div>
                    <p className="text-[10px] text-gray-400">
                      AI will ignore 00:00 to {formatTime(introSeconds)} and only look for gameplay highlights.
                    </p>
                  </div>
                )}
              </div>

              {/* Advanced AI Settings Accordion */}
              <div className="pt-1">
                <button
                  type="button"
                  onClick={() => setShowAdvancedAI(!showAdvancedAI)}
                  className="text-[11px] text-gray-400 hover:text-gray-200 flex items-center gap-1 font-semibold"
                >
                  {showAdvancedAI ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  <span>Advanced AI Engine (Whisper & Ollama)</span>
                </button>

                {showAdvancedAI && (
                  <div className="mt-2 p-2.5 rounded-lg bg-[#141826] border border-[#23293e] space-y-2 text-[11px]">
                    <div className="space-y-1">
                      <span className="text-gray-300 font-semibold block">Faster-Whisper CUDA Model:</span>
                      <select
                        value={whisperModel}
                        onChange={(e) => setWhisperModel(e.target.value)}
                        className="w-full bg-[#0d101a] border border-[#262c3f] rounded px-2 py-1 text-white text-xs font-mono"
                      >
                        <option value="small">small (Recommended: 1.2GB VRAM, High Accuracy)</option>
                        <option value="base">base (0.7GB VRAM, Ultra Fast)</option>
                        <option value="medium">medium (2.6GB VRAM, Multilingual Deep)</option>
                      </select>
                    </div>

                    <div className="space-y-1">
                      <span className="text-gray-300 font-semibold block">Ollama LLM Viral Hook Generator:</span>
                      <select
                        value={ollamaModel}
                        onChange={(e) => setOllamaModel(e.target.value)}
                        className="w-full bg-[#0d101a] border border-[#262c3f] rounded px-2 py-1 text-white text-xs font-mono"
                      >
                        {ollamaModels.map((m) => (
                          <option key={m} value={m}>
                            {m} (Local)
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between text-gray-300">
                        <span>Sensitivity:</span>
                        <span className="font-mono text-[#ccff00] font-bold">{sensitivity.toFixed(1)}x</span>
                      </div>
                      <input
                        type="range"
                        min="0.6"
                        max="1.6"
                        step="0.1"
                        value={sensitivity}
                        onChange={(e) => setSensitivity(parseFloat(e.target.value))}
                        className="w-full accent-[#ccff00]"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Scan Trigger / Multi-Stage Progress Status */}
              {isScanning || scanJobStatus?.status === 'running' ? (
                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-extrabold text-amber-300 flex items-center gap-1.5">
                      <RotateCw className="w-3.5 h-3.5 animate-spin" />
                      <span>{scanJobStatus?.stage_name || 'AI Scanning In Progress...'}</span>
                    </span>
                    <span className="font-mono font-bold text-amber-300">
                      {scanJobStatus?.progress || 10}%
                    </span>
                  </div>

                  {/* Real Multi-Stage Progress Bar */}
                  <div className="w-full bg-[#0b0e17] rounded-full h-2 overflow-hidden border border-amber-500/30">
                    <div
                      className="bg-gradient-to-r from-amber-400 via-[#ccff00] to-emerald-400 h-full transition-all duration-300"
                      style={{ width: `${scanJobStatus?.progress || 10}%` }}
                    />
                  </div>

                  <p className="text-[10px] text-gray-300 font-mono truncate">
                    {scanJobStatus?.message || 'Processing audio and visual intelligence...'}
                  </p>

                  {onCancelScan && (
                    <button
                      type="button"
                      onClick={onCancelScan}
                      className="w-full py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 text-[11px] font-bold border border-rose-500/40 transition-colors"
                    >
                      Cancel AI Scan
                    </button>
                  )}
                </div>
              ) : (
                <button
                  type="button"
                  onClick={handleTriggerScan}
                  disabled={!session?.video_path}
                  className={`w-full py-3 rounded-xl text-xs font-black uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
                    !session?.video_path
                      ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                      : 'bg-[#ccff00] text-black hover:bg-[#b8e600] shadow-lg shadow-[#ccff00]/20 hover:scale-[1.02] cursor-pointer'
                  }`}
                >
                  <Sparkles className="w-4 h-4 fill-current" />
                  <span>Scan & Discover Highlights</span>
                </button>
              )}
            </div>

            {/* Batch Controls Bar (Select All / Render Selected) */}
            {clips.length > 0 && (
              <div className="flex items-center justify-between text-xs px-1 pt-1 border-t border-[#1f2438]">
                <button
                  type="button"
                  onClick={onSelectAllClips}
                  className="text-gray-300 hover:text-white font-semibold flex items-center gap-1.5"
                >
                  {selectedClipsCount === clips.length ? (
                    <CheckSquare className="w-4 h-4 text-[#ccff00]" />
                  ) : (
                    <Square className="w-4 h-4 text-gray-400" />
                  )}
                  <span>
                    Select All ({selectedClipsCount}/{clips.length})
                  </span>
                </button>

                <button
                  type="button"
                  onClick={onTriggerRender}
                  disabled={isRendering || selectedClipsCount === 0}
                  className="px-3 py-1 rounded-lg bg-[#ccff00] text-black font-extrabold text-[11px] hover:bg-[#b8e600] disabled:opacity-50 transition-colors flex items-center gap-1 shadow-sm"
                >
                  <Play className="w-3 h-3 fill-current" />
                  <span>Render Selected ({selectedClipsCount})</span>
                </button>
              </div>
            )}

            {/* Clips List with Explainable HQS Badges & Quick Sync */}
            <div className="space-y-3 max-h-[480px] overflow-y-auto pr-1">
              {filteredClips.length === 0 ? (
                <div className="text-center py-10 text-gray-500 text-xs space-y-1">
                  <p className="font-semibold text-gray-400">No highlights discovered yet</p>
                  <p className="text-[11px]">
                    Click "Scan & Discover Highlights" above to run multi-signal AI intelligence on your gaming recording.
                  </p>
                </div>
              ) : (
                filteredClips.map((clip, idx) => {
                  const clipId = clip.id || `clip-${idx}`;
                  const isCurrent = currentTime >= clip.start && currentTime <= clip.end;
                  const hqsVal = Math.round(clip.hqs || (clip.score ? clip.score * 10 : 85));
                  const isHovered = hoveredHQSClipId === clipId;

                  return (
                    <div
                      key={clipId}
                      onClick={() => {
                        seekTo(clip.start);
                        setInPoint(clip.start);
                        setOutPoint(clip.end);
                        onSelectClipForPreview(clip);
                      }}
                      className={`p-3.5 rounded-xl border transition-all cursor-pointer relative group ${
                        isCurrent
                          ? 'bg-[#1b2133] border-[#ccff00] shadow-lg shadow-[#ccff00]/10'
                          : 'bg-[#0e111a] border-[#1e2334] hover:border-gray-500 hover:bg-[#121622]'
                      }`}
                    >
                      {/* Top Header: Tag Badge + Title + Explainable HQS Score */}
                      <div className="flex items-start justify-between gap-2 mb-1.5">
                        <div className="flex items-center gap-1.5 font-bold text-xs text-white truncate">
                          <span className="text-[#ccff00] font-mono">#{idx + 1}</span>
                          <span className="truncate">
                            {clip.title || clip.label || 'Viral Gaming Moment'}
                          </span>
                        </div>

                        {/* Explainable HQS Score Pill with Breakdown Popover */}
                        <div className="relative flex-shrink-0">
                          <div
                            onClick={(e) => {
                              e.stopPropagation();
                              setHoveredHQSClipId(isHovered ? null : clipId);
                            }}
                            className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-black bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/25 transition-colors shadow-sm"
                            title="Highlight Quality Score (HQS). Click to view breakdown."
                          >
                            <Zap className="w-3 h-3 fill-emerald-400 text-emerald-400" />
                            <span>{hqsVal} HQS</span>
                          </div>

                          {/* Interactive Score Breakdown Popover */}
                          {isHovered && clip.hqs_breakdown && (
                            <div
                              onClick={(e) => e.stopPropagation()}
                              className="absolute right-0 top-7 z-30 w-52 p-3 bg-[#111420] border border-[#2b334a] rounded-xl shadow-2xl text-[10px] space-y-1.5 backdrop-blur-md animate-fadeIn"
                            >
                              <div className="flex items-center justify-between pb-1 border-b border-[#202638] font-bold text-white text-[11px]">
                                <span>HQS Breakdown</span>
                                <span className="text-emerald-400 font-mono">{hqsVal}/100</span>
                              </div>
                              <div className="space-y-1 text-gray-300">
                                <div className="flex justify-between">
                                  <span>🎣 Viral Hook (25%):</span>
                                  <span className="font-mono text-white font-bold">{clip.hqs_breakdown.hook.toFixed(1)}/25</span>
                                </div>
                                <div className="flex justify-between">
                                  <span>🔊 Audio Energy (20%):</span>
                                  <span className="font-mono text-white font-bold">{clip.hqs_breakdown.audio.toFixed(1)}/20</span>
                                </div>
                                <div className="flex justify-between">
                                  <span>⚔️ In-Game Event (25%):</span>
                                  <span className="font-mono text-white font-bold">{clip.hqs_breakdown.event.toFixed(1)}/25</span>
                                </div>
                                <div className="flex justify-between">
                                  <span>💡 Context Setup (20%):</span>
                                  <span className="font-mono text-white font-bold">{clip.hqs_breakdown.context.toFixed(1)}/20</span>
                                </div>
                                <div className="flex justify-between">
                                  <span>🎬 Visual Motion (10%):</span>
                                  <span className="font-mono text-white font-bold">{clip.hqs_breakdown.visual.toFixed(1)}/10</span>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Viral Hook Text Quote Banner */}
                      {clip.hook_text && (
                        <div className="mb-2 p-2 rounded-lg bg-[#141928] border border-[#242c44] text-[11px] font-semibold text-[#ccff00] italic leading-tight">
                          💬 "{clip.hook_text}"
                        </div>
                      )}

                      {/* AI Reasoning / Explanation */}
                      <p className="text-[11px] text-gray-400 line-clamp-2 mb-2 leading-relaxed">
                        {clip.reason}
                      </p>

                      {/* Bottom Footer: Timestamps, Sync Button, Render Button & Checkbox */}
                      <div className="flex items-center justify-between text-[10px] pt-1.5 border-t border-[#1a1f2e]">
                        <span className="font-mono text-gray-400 bg-[#161a28] px-1.5 py-0.5 rounded border border-[#232738]">
                          {formatTime(clip.start)} - {formatTime(clip.end)} ({Math.round(clip.end - clip.start)}s)
                        </span>

                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              seekTo(clip.start);
                              setInPoint(clip.start);
                              setOutPoint(clip.end);
                            }}
                            className="text-[#00d2ff] hover:underline font-semibold flex items-center gap-1"
                            title="Set Timeline In/Out markers to this moment"
                          >
                            <span>Set In/Out</span>
                          </button>

                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              onToggleClipSelection(idx);
                            }}
                            className="text-gray-400 hover:text-white flex items-center gap-1 font-semibold"
                          >
                            {clip.selected !== false ? (
                              <>
                                <CheckSquare className="w-3.5 h-3.5 text-[#ccff00]" />
                                <span className="text-white">Selected</span>
                              </>
                            ) : (
                              <>
                                <Square className="w-3.5 h-3.5" />
                                <span>Select</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Pre-Roll Trim Confirmation Modal */}
      {showPreRollDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fadeIn">
          <div className="bg-[#141724] border border-[#292f44] rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-[#23283c]">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <Scissors className="w-4 h-4 text-rose-400" />
                <span>Cut & Delete Pre-Roll Intro</span>
              </h3>
              <button
                onClick={() => setShowPreRollDialog(false)}
                className="text-gray-400 hover:text-white text-xs"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs text-gray-300">
              <p>
                Delete talking intro from <strong className="text-white">00:00</strong> to{' '}
                <strong className="text-[#ccff00]">{formatTime(currentTime)}</strong>. The video will start cleanly from this moment.
              </p>

              {/* Trimming Mode Selector */}
              <div className="space-y-2 pt-1">
                <span className="font-bold text-white block">Choose Trimming Engine:</span>
                <label className="flex items-start gap-2.5 p-2.5 rounded-xl border border-[#2b334d] bg-[#0d0f17] cursor-pointer hover:border-[#ccff00]">
                  <input
                    type="radio"
                    name="trim_mode"
                    value="fast"
                    checked={trimMode === 'fast'}
                    onChange={() => setTrimMode('fast')}
                    className="accent-[#ccff00] mt-0.5"
                  />
                  <div>
                    <div className="font-bold text-white flex items-center gap-1.5">
                      <span>⚡ Mode A: Fast Keyframe Trim</span>
                      <span className="text-[9px] bg-[#ccff00]/20 text-[#ccff00] px-1 rounded">0.1s Stream Copy</span>
                    </div>
                    <div className="text-[11px] text-gray-400">
                      Instantly cuts at nearest keyframe with zero re-encoding.
                    </div>
                  </div>
                </label>

                <label className="flex items-start gap-2.5 p-2.5 rounded-xl border border-[#2b334d] bg-[#0d0f17] cursor-pointer hover:border-[#00d2ff]">
                  <input
                    type="radio"
                    name="trim_mode"
                    value="accurate"
                    checked={trimMode === 'accurate'}
                    onChange={() => setTrimMode('accurate')}
                    className="accent-[#00d2ff] mt-0.5"
                  />
                  <div>
                    <div className="font-bold text-white flex items-center gap-1.5">
                      <span>🎯 Mode B: Accurate Frame Trim</span>
                      <span className="text-[9px] bg-[#00d2ff]/20 text-[#00d2ff] px-1 rounded">NVENC 60fps</span>
                    </div>
                    <div className="text-[11px] text-gray-400">
                      Frame-accurate cut to exact millisecond using RTX 3050 NVENC.
                    </div>
                  </div>
                </label>
              </div>

              <div className="bg-[#0e111a] p-3 rounded-lg border border-[#202538] font-mono text-[11px] text-gray-300">
                <div>Cut range: 00:00 → {formatTime(currentTime)}</div>
                <div>New duration: ~{formatTime(totalDur - currentTime)}</div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowPreRollDialog(false)}
                className="px-4 py-2 rounded-lg bg-[#1f2438] text-gray-300 hover:text-white font-medium text-xs"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => executeDirectPreRollTrim(currentTime)}
                disabled={isTrimming}
                className="px-5 py-2 rounded-lg bg-rose-500 hover:bg-rose-600 text-white font-bold text-xs shadow-lg transition-transform hover:scale-105"
              >
                {isTrimming ? 'Trimming...' : 'Confirm Cut'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
