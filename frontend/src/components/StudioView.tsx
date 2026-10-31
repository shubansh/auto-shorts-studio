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
  CornerDownRight
} from 'lucide-react';
import type { SessionData, ClipMoment, ActiveTab, WaveformData } from '../types';

interface StudioViewProps {
  session: SessionData | null;
  onScanHighlights: (numClips: number, minDur: number, maxDur: number, scanStart: number) => Promise<void>;
  onTrimVideo: (startTime: number, endTime: number, mode?: string) => Promise<void>;
  onSelectClipForPreview: (clip: ClipMoment) => void;
  onToggleClipSelection: (index: number) => void;
  onSelectAllClips: () => void;
  onTriggerRender: () => void;
  setActiveTab: (tab: ActiveTab) => void;
  isScanning: boolean;
  isRendering: boolean;
}

export const StudioView: React.FC<StudioViewProps> = ({
  session,
  onScanHighlights,
  onTrimVideo,
  onSelectClipForPreview,
  onToggleClipSelection,
  onSelectAllClips: _onSelectAllClips,
  onTriggerRender,
  setActiveTab,
  isScanning,
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

  // Pre-roll Trim Controls
  const [trimMode, setTrimMode] = useState<'fast' | 'accurate'>('fast');
  const [isTrimming, setIsTrimming] = useState(false);
  const [showPreRollDialog, setShowPreRollDialog] = useState(false);

  // AI Highlights settings
  const [numClips, setNumClips] = useState(3);
  const [ignoreIntro, setIgnoreIntro] = useState(true);
  const [introSeconds, setIntroSeconds] = useState(45);
  const [activeFilter, setActiveFilter] = useState<string>('all');

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

  // 9. Pre-Roll Intro Trimming Execution
  const executePreRollTrim = async () => {
    if (currentTime < 0.5) return;
    setIsTrimming(true);
    try {
      await onTrimVideo(currentTime, totalDur, trimMode);
      setShowPreRollDialog(false);
      seekTo(0);
    } catch (err: any) {
      alert(`Trim failed: ${err.message}`);
    } finally {
      setIsTrimming(false);
    }
  };

  const clips = session?.discovered_clips || [];
  const filteredClips = clips.filter((c) => {
    if (activeFilter === 'all') return true;
    return c.label?.toLowerCase().includes(activeFilter.toLowerCase()) || c.reason?.toLowerCase().includes(activeFilter.toLowerCase());
  });

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

            {/* Quick Actions: Pre-Roll Intro Cut & Instant Range Export */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
              {/* Pre-Roll Intro Cut Action Card */}
              <div className="p-3.5 rounded-xl bg-[#151926] border border-[#242b3e] space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Trash2 className="w-4 h-4 text-rose-400" />
                    <span className="text-xs font-extrabold text-white">Pre-Roll Intro Cutter</span>
                  </div>
                  <span className="text-[10px] text-gray-400 font-mono">
                    Playhead: {formatTime(currentTime)}
                  </span>
                </div>

                <p className="text-[11px] text-gray-400 leading-tight">
                  Cut off the talking intro from 00:00 to current playhead without modifying the original source.
                </p>

                <div className="flex items-center gap-2 pt-1">
                  <button
                    onClick={() => setShowPreRollDialog(true)}
                    disabled={currentTime < 1 || isTrimming}
                    className={`flex-1 py-2 px-3 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
                      currentTime >= 1
                        ? 'bg-rose-500/20 text-rose-300 hover:bg-rose-500/30 border border-rose-500/40 cursor-pointer'
                        : 'bg-[#1a1f2e] text-gray-500 border-[#242b3e] cursor-not-allowed'
                    }`}
                  >
                    <Scissors className="w-3.5 h-3.5" />
                    <span>Cut Intro Before {formatTime(currentTime)}</span>
                  </button>
                </div>
              </div>

              {/* Export Selected In-Out Range as Short */}
              <div className="p-3.5 rounded-xl bg-gradient-to-r from-[#ccff00]/10 via-[#00d2ff]/10 to-transparent border border-[#ccff00]/30 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-[#ccff00]" />
                    <span className="text-xs font-extrabold text-white">Custom Range Short</span>
                  </div>
                  <span className="text-[10px] text-[#ccff00] font-mono font-bold">
                    {Math.round(outPoint - inPoint)}s Selected
                  </span>
                </div>

                <p className="text-[11px] text-gray-300 leading-tight">
                  Instantly render this custom in-out range with 9:16 layout and Hormozi viral captions.
                </p>

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
                  className="w-full py-2 px-3 rounded-lg bg-[#ccff00] text-black font-extrabold text-xs hover:bg-[#b8e600] transition-all flex items-center justify-center gap-1.5 shadow-lg shadow-[#ccff00]/10"
                >
                  <Play className="w-3 h-3 fill-current" />
                  <span>Render In/Out Short ({Math.round(outPoint - inPoint)}s)</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: AI Highlight Moments & Clip Discovery (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-[#121522] border border-[#232738] rounded-2xl p-5 shadow-xl space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between pb-3 border-b border-[#1f2438]">
              <div className="flex items-center gap-2">
                <Flame className="w-5 h-5 text-[#ccff00]" />
                <h3 className="font-extrabold text-sm text-white">AI Highlight Clips</h3>
              </div>
              <span className="text-xs font-mono bg-[#1a1f30] text-[#ccff00] px-2 py-0.5 rounded font-bold">
                {clips.length} Discovered
              </span>
            </div>

            {/* AI Highlight Scanner Trigger Card */}
            <div className="bg-[#0e111a] border border-[#1f2438] rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between text-xs text-gray-300 font-semibold">
                <span>Moment Count:</span>
                <span className="text-[#ccff00] font-mono">{numClips} Clips</span>
              </div>
              <input
                type="range"
                min="1"
                max="8"
                value={numClips}
                onChange={(e) => setNumClips(parseInt(e.target.value))}
                className="w-full accent-[#ccff00]"
              />

              <div className="flex items-center justify-between pt-1">
                <label className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={ignoreIntro}
                    onChange={(e) => setIgnoreIntro(e.target.checked)}
                    className="rounded accent-[#ccff00]"
                  />
                  <span>Ignore Intro ({introSeconds}s)</span>
                </label>
                {ignoreIntro && (
                  <input
                    type="number"
                    min="0"
                    max="300"
                    value={introSeconds}
                    onChange={(e) => setIntroSeconds(parseInt(e.target.value) || 0)}
                    className="w-16 bg-[#171b29] border border-[#2b334a] rounded px-2 py-0.5 text-xs text-white font-mono text-center"
                  />
                )}
              </div>

              <button
                onClick={() => onScanHighlights(numClips, 20, 50, ignoreIntro ? introSeconds : 0)}
                disabled={isScanning || !session?.video_path}
                className={`w-full py-2.5 rounded-xl text-xs font-extrabold uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
                  isScanning
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 cursor-wait'
                    : !session?.video_path
                    ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
                    : 'bg-[#ccff00] text-black hover:bg-[#b8e600] shadow-md shadow-[#ccff00]/15 hover:scale-[1.02]'
                }`}
              >
                <Sparkles className="w-4 h-4" />
                <span>{isScanning ? 'Scanning Highlights...' : 'Scan & Discover Highlights'}</span>
              </button>
            </div>

            {/* Clips List */}
            <div className="space-y-2.5 max-h-[460px] overflow-y-auto pr-1">
              {filteredClips.length === 0 ? (
                <div className="text-center py-8 text-gray-500 text-xs">
                  No highlights scanned yet. Click "Scan & Discover Highlights" to find clutch gameplay and viral moments.
                </div>
              ) : (
                filteredClips.map((clip, idx) => (
                  <div
                    key={idx}
                    onClick={() => {
                      seekTo(clip.start);
                      setInPoint(clip.start);
                      setOutPoint(clip.end);
                      onSelectClipForPreview(clip);
                    }}
                    className={`p-3 rounded-xl border transition-all cursor-pointer group ${
                      currentTime >= clip.start && currentTime <= clip.end
                        ? 'bg-[#1b2133] border-[#ccff00] shadow-md shadow-[#ccff00]/10'
                        : 'bg-[#0e111a] border-[#1e2334] hover:border-gray-500'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <div className="flex items-center gap-1.5 font-bold text-xs text-white">
                        <span className="text-[#ccff00]">#{idx + 1}</span>
                        <span className="truncate">{clip.label || 'Viral Gaming Clip'}</span>
                      </div>
                      <span className="text-[10px] font-mono text-gray-400 bg-[#161a28] px-1.5 py-0.5 rounded">
                        {formatTime(clip.start)} - {formatTime(clip.end)}
                      </span>
                    </div>

                    <p className="text-[11px] text-gray-400 line-clamp-2 mb-2">
                      {clip.reason}
                    </p>

                    <div className="flex items-center justify-between text-[10px] pt-1 border-t border-[#1a1f2e]">
                      <span className="text-[#ccff00] font-mono font-bold">
                        Score: {clip.score}/10
                      </span>
                      <button
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
                ))
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
                onClick={executePreRollTrim}
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
