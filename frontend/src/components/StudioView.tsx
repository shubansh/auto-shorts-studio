import React, { useState, useRef } from 'react';
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
  RefreshCw
} from 'lucide-react';
import type { SessionData, ClipMoment, ActiveTab } from '../types';

interface StudioViewProps {
  session: SessionData | null;
  onScanHighlights: (numClips: number, minDur: number, maxDur: number, scanStart: number) => Promise<void>;
  onTrimVideo: (startTime: number, endTime: number) => Promise<void>;
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
  const timelineRef = useRef<HTMLDivElement>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isMuted, setIsMuted] = useState(false);

  // In / Out Trim Markers (for CapCut-style manual clipping)
  const [inPoint, setInPoint] = useState<number>(0);
  const [outPoint, setOutPoint] = useState<number>(30);

  // AI Scan settings
  const [numClips, setNumClips] = useState(3);
  const [ignoreIntro, setIgnoreIntro] = useState(true);
  const [introSeconds, setIntroSeconds] = useState(45);
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [isTrimming, setIsTrimming] = useState(false);

  const totalDur = session?.meta?.duration || duration || 1;

  // Format seconds to mm:ss
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Video playback time update
  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      const d = videoRef.current.duration;
      setDuration(d);
      setOutPoint(Math.min(30, d));
    }
  };

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

  const seekRelative = (delta: number) => {
    if (!videoRef.current) return;
    const target = Math.max(0, Math.min(totalDur, videoRef.current.currentTime + delta));
    videoRef.current.currentTime = target;
    setCurrentTime(target);
  };

  const seekTo = (time: number) => {
    if (!videoRef.current) return;
    videoRef.current.currentTime = Math.max(0, Math.min(totalDur, time));
    setCurrentTime(time);
  };

  // Timeline click or drag
  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!timelineRef.current) return;
    const rect = timelineRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const pct = Math.max(0, Math.min(1, clickX / rect.width));
    seekTo(pct * totalDur);
  };

  // Mark In & Out
  const handleSetInPoint = () => {
    setInPoint(currentTime);
    if (outPoint <= currentTime) {
      setOutPoint(Math.min(totalDur, currentTime + 30));
    }
  };

  const handleSetOutPoint = () => {
    if (currentTime > inPoint) {
      setOutPoint(currentTime);
    }
  };

  // CapCut-style Ripple Delete Intro (Cut Left of Playhead)
  const handleRippleDeleteIntro = async () => {
    if (currentTime <= 1) {
      alert('Move playhead forward past the talking intro before cutting!');
      return;
    }
    const confirmCut = window.confirm(
      `✂️ RIPPLE DELETE INTRO:\n\nThis will permanently delete the pre-roll intro from 00:00 to ${formatTime(currentTime)} (${Math.round(currentTime)} seconds).\n\nThe video will start cleanly from this moment in 0.1s! Proceed?`
    );
    if (!confirmCut) return;

    setIsTrimming(true);
    try {
      await onTrimVideo(currentTime, totalDur);
      seekTo(0);
    } catch (err: any) {
      alert(`Cut failed: ${err.message}`);
    } finally {
      setIsTrimming(false);
    }
  };

  const clips = session?.discovered_clips || [];
  const selectedClipsCount = clips.filter((c) => c.selected !== false).length;

  return (
    <div className="p-6 max-w-[1600px] mx-auto space-y-6 animate-fadeIn">
      {/* Main Grid: Left Video Player & Timeline (65%) | Right AI Clips Panel (35%) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Player + CapCut NLE Timeline (8 cols) */}
        <div className="lg:col-span-8 space-y-4">
          {/* 16:9 Video Player Container */}
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
                  className="mt-3 px-4 py-2 bg-[#ccff00] text-black text-xs font-bold rounded-lg"
                >
                  Import Video
                </button>
              </div>
            )}

            {/* In-Video Overlay Buttons */}
            <div className="absolute top-4 right-4 flex items-center gap-2">
              <button
                onClick={() => setActiveTab('layout')}
                className="px-3 py-1.5 rounded-lg bg-black/60 hover:bg-black/90 backdrop-blur-md text-white text-xs font-semibold flex items-center gap-1.5 border border-white/10 shadow-lg"
              >
                <Sliders className="w-3.5 h-3.5 text-[#00d2ff]" />
                <span>Adjust 9:16 Crop</span>
              </button>
            </div>

            {/* Bottom In-Player Controls */}
            <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/90 via-black/40 to-transparent flex items-center justify-between text-white text-xs">
              <div className="flex items-center gap-3">
                <button
                  onClick={togglePlay}
                  className="p-1.5 rounded-lg hover:bg-white/20 transition-colors"
                >
                  {isPlaying ? (
                    <Pause className="w-4 h-4 fill-white" />
                  ) : (
                    <Play className="w-4 h-4 fill-white" />
                  )}
                </button>
                <button
                  onClick={() => {
                    if (videoRef.current) {
                      videoRef.current.muted = !isMuted;
                      setIsMuted(!isMuted);
                    }
                  }}
                  className="p-1.5 rounded-lg hover:bg-white/20 transition-colors"
                >
                  {isMuted ? (
                    <VolumeX className="w-4 h-4 text-red-400" />
                  ) : (
                    <Volume2 className="w-4 h-4" />
                  )}
                </button>
                <span className="font-mono text-xs text-gray-300">
                  {formatTime(currentTime)} / {formatTime(totalDur)}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[10px] bg-[#ccff00]/20 text-[#ccff00] px-2 py-0.5 rounded font-bold uppercase">
                  1080p 60fps Source
                </span>
              </div>
            </div>
          </div>

          {/* ======================================================== */}
          {/* CAPCUT / PREMIERE STYLE NLE TIMELINE SCRUBBER           */}
          {/* ======================================================== */}
          <div className="bg-[#121522] border border-[#232738] rounded-2xl p-5 space-y-4 shadow-xl">
            {/* Timeline Header & Transport Controls */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs font-black uppercase tracking-wider text-gray-300 flex items-center gap-1.5">
                  <Scissors className="w-4 h-4 text-[#ccff00]" />
                  <span>Timeline Editor</span>
                </span>
                <span className="text-xs font-mono bg-[#1a1f30] text-[#ccff00] px-2.5 py-0.5 rounded-md font-bold">
                  {formatTime(currentTime)}
                </span>
              </div>

              {/* Seek Transport Buttons */}
              <div className="flex items-center gap-1 bg-[#0d0f17] p-1 rounded-xl border border-[#202538]">
                <button
                  onClick={() => seekTo(0)}
                  className="px-2 py-1 text-[11px] font-bold text-gray-400 hover:text-white rounded hover:bg-[#1a1f30]"
                  title="Go to Start"
                >
                  ⏮ 0:00
                </button>
                <button
                  onClick={() => seekRelative(-10)}
                  className="px-2 py-1 text-[11px] font-bold text-gray-400 hover:text-white rounded hover:bg-[#1a1f30]"
                >
                  -10s
                </button>
                <button
                  onClick={() => seekRelative(-2)}
                  className="px-2 py-1 text-[11px] font-bold text-gray-400 hover:text-white rounded hover:bg-[#1a1f30]"
                >
                  -2s
                </button>
                <button
                  onClick={togglePlay}
                  className="px-3 py-1 bg-[#ccff00] text-black font-extrabold rounded text-xs hover:bg-[#b8e600]"
                >
                  {isPlaying ? 'PAUSE' : 'PLAY'}
                </button>
                <button
                  onClick={() => seekRelative(2)}
                  className="px-2 py-1 text-[11px] font-bold text-gray-400 hover:text-white rounded hover:bg-[#1a1f30]"
                >
                  +2s
                </button>
                <button
                  onClick={() => seekRelative(10)}
                  className="px-2 py-1 text-[11px] font-bold text-gray-400 hover:text-white rounded hover:bg-[#1a1f30]"
                >
                  +10s
                </button>
              </div>

              {/* In / Out Buttons */}
              <div className="flex items-center gap-1.5">
                <button
                  onClick={handleSetInPoint}
                  className="px-2.5 py-1 text-xs font-bold rounded-lg bg-[#1a1f30] hover:bg-[#252c44] text-gray-300 border border-[#2b334d]"
                  title="Set In Marker at Playhead"
                >
                  [ Mark In ({formatTime(inPoint)})
                </button>
                <button
                  onClick={handleSetOutPoint}
                  className="px-2.5 py-1 text-xs font-bold rounded-lg bg-[#1a1f30] hover:bg-[#252c44] text-gray-300 border border-[#2b334d]"
                  title="Set Out Marker at Playhead"
                >
                  Mark Out ({formatTime(outPoint)}) ]
                </button>
              </div>
            </div>

            {/* Filmstrip Track with Playhead & In/Out Shading */}
            <div
              ref={timelineRef}
              onClick={handleTimelineClick}
              className="relative h-20 bg-[#090b10] rounded-xl overflow-hidden border border-[#252b3e] cursor-pointer select-none group"
            >
              {/* Filmstrip Thumbnails Background */}
              <div className="absolute inset-0 flex opacity-75 group-hover:opacity-90 transition-opacity">
                {session?.timeline_thumbs && session.timeline_thumbs.length > 0 ? (
                  session.timeline_thumbs.map((thumb, idx) => (
                    <div
                      key={idx}
                      className="flex-1 h-full border-r border-[#1a1f30] overflow-hidden relative"
                    >
                      <img
                        src={thumb.url}
                        alt={`Thumb ${idx}`}
                        className="w-full h-full object-cover"
                      />
                      <span className="absolute bottom-1 right-1 text-[9px] bg-black/70 text-gray-300 px-1 rounded font-mono">
                        {formatTime(thumb.timestamp)}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-xs text-gray-600 font-mono">
                    Filmstrip Track (Scrub anywhere to seek)
                  </div>
                )}
              </div>

              {/* Marked Region Highlight (Between In and Out) */}
              {outPoint > inPoint && (
                <div
                  className="absolute top-0 bottom-0 bg-[#ccff00]/15 border-x-2 border-[#ccff00] pointer-events-none"
                  style={{
                    left: `${(inPoint / totalDur) * 100}%`,
                    width: `${((outPoint - inPoint) / totalDur) * 100}%`
                  }}
                >
                  <div className="absolute top-1 left-1.5 text-[9px] font-bold text-[#ccff00] bg-black/60 px-1 rounded">
                    Selected Clip: {Math.round(outPoint - inPoint)}s
                  </div>
                </div>
              )}

              {/* AI Discovered Clips Markers on Timeline */}
              {clips.map((clip, idx) => (
                <div
                  key={idx}
                  onClick={(e) => {
                    e.stopPropagation();
                    seekTo(clip.start);
                  }}
                  className="absolute top-0 bottom-0 bg-purple-500/20 hover:bg-purple-500/40 border-x border-purple-400 cursor-pointer pointer-events-auto"
                  style={{
                    left: `${(clip.start / totalDur) * 100}%`,
                    width: `${((clip.end - clip.start) / totalDur) * 100}%`
                  }}
                  title={`AI Clip #${idx + 1}: ${clip.reason}`}
                >
                  <div className="absolute bottom-1 left-1 text-[8px] bg-purple-900/80 text-purple-200 px-1 rounded font-bold">
                    ⚡ #{idx + 1}
                  </div>
                </div>
              ))}

              {/* Red Playhead Needle */}
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-20 pointer-events-none shadow-[0_0_8px_rgba(239,68,68,0.8)]"
                style={{ left: `${(currentTime / totalDur) * 100}%` }}
              >
                <div className="w-3.5 h-3.5 -ml-1.5 bg-red-500 rounded-sm rotate-45 transform -translate-y-1/2 shadow-md"></div>
              </div>
            </div>

            {/* Quick Editing Actions: Split & Ripple Delete */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
              {/* Ripple Delete Intro Button */}
              <button
                onClick={handleRippleDeleteIntro}
                disabled={isTrimming || currentTime < 1}
                className={`flex items-center justify-center gap-2 p-3 rounded-xl border text-xs font-bold transition-all ${
                  currentTime >= 1
                    ? 'bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border-rose-500/30 hover:border-rose-500/50 cursor-pointer'
                    : 'bg-[#151824] text-gray-500 border-[#232738] cursor-not-allowed'
                }`}
              >
                <Trash2 className="w-4 h-4 text-rose-400 shrink-0" />
                <div className="text-left">
                  <div className="font-extrabold flex items-center gap-1.5">
                    <span>✂️ Cut & Delete Pre-Roll Intro</span>
                    <span className="text-[9px] bg-rose-500/20 px-1 rounded font-mono">0.1s Fast</span>
                  </div>
                  <div className="text-[10px] text-gray-400 font-normal">
                    Delete 00:00 to {formatTime(currentTime)} & start video cleanly from playhead
                  </div>
                </div>
              </button>

              {/* Export Selected In-Out Range as Short */}
              <button
                onClick={() => {
                  onSelectClipForPreview({
                    start: inPoint,
                    end: outPoint,
                    score: 95,
                    reason: `Custom timeline cut (${formatTime(inPoint)} - ${formatTime(outPoint)})`
                  });
                  onTriggerRender();
                }}
                disabled={isRendering || outPoint <= inPoint}
                className="flex items-center justify-center gap-2 p-3 rounded-xl bg-gradient-to-r from-[#ccff00]/20 to-[#00d2ff]/20 hover:from-[#ccff00]/30 hover:to-[#00d2ff]/30 text-white border border-[#ccff00]/40 text-xs font-bold transition-all cursor-pointer shadow-lg shadow-[#ccff00]/5"
              >
                <Zap className="w-4 h-4 text-[#ccff00] fill-[#ccff00] shrink-0" />
                <div className="text-left">
                  <div className="font-extrabold text-[#ccff00]">
                    Export In/Out Range ({Math.round(outPoint - inPoint)}s)
                  </div>
                  <div className="text-[10px] text-gray-300 font-normal">
                    Instantly render selection with 9:16 crop & subtitles
                  </div>
                </div>
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: AI Highlight Moments & Clip Discovery (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-[#121522] border border-[#232738] rounded-2xl p-5 shadow-xl space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between pb-3 border-b border-[#1f2438]">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[#ccff00]" />
                <h3 className="text-sm font-black uppercase tracking-wider text-white">
                  AI Highlight Moments
                </h3>
              </div>
              <span className="text-xs bg-[#1f2438] text-gray-300 font-bold px-2 py-0.5 rounded-full">
                {clips.length} Found
              </span>
            </div>

            {/* AI Highlight Scan Config Box */}
            <div className="bg-[#0e111a] p-3.5 rounded-xl border border-[#202538] space-y-3">
              <div className="flex items-center justify-between text-xs font-bold text-gray-300">
                <span>Moments to Detect:</span>
                <div className="flex gap-1.5">
                  {[2, 3, 5].map((cnt) => (
                    <button
                      key={cnt}
                      onClick={() => setNumClips(cnt)}
                      className={`px-2 py-0.5 rounded text-xs font-bold ${
                        numClips === cnt
                          ? 'bg-[#ccff00] text-black font-black'
                          : 'bg-[#181c2b] text-gray-400 hover:text-white'
                      }`}
                    >
                      {cnt}
                    </button>
                  ))}
                </div>
              </div>

              {/* Pre-Roll Intro Ignore Checkbox */}
              <div className="pt-1 border-t border-[#1b2030] space-y-2">
                <label className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={ignoreIntro}
                    onChange={(e) => setIgnoreIntro(e.target.checked)}
                    className="rounded border-gray-700 text-[#ccff00] focus:ring-[#ccff00]"
                  />
                  <span>Ignore talking webcam intro in scan</span>
                </label>
                {ignoreIntro && (
                  <div className="flex items-center justify-between text-[11px] text-gray-400 pl-5">
                    <span>Start scan after:</span>
                    <div className="flex items-center gap-1 font-mono">
                      <input
                        type="number"
                        min="0"
                        max={Math.floor(totalDur)}
                        value={introSeconds}
                        onChange={(e) => setIntroSeconds(Number(e.target.value))}
                        className="w-14 px-2 py-0.5 rounded bg-[#161a29] border border-[#282f48] text-white text-center font-bold"
                      />
                      <span>sec ({formatTime(introSeconds)})</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Scan Trigger Button */}
              <button
                disabled={isScanning || !session?.video_path}
                onClick={() =>
                  onScanHighlights(numClips, 20, 50, ignoreIntro ? introSeconds : 0)
                }
                className="w-full py-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-extrabold text-xs uppercase tracking-wider transition-all shadow-md flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isScanning ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin text-white" />
                    <span>Whisper + Ollama Scanning...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 text-[#ccff00]" />
                    <span>Scan & Discover Viral Moments</span>
                  </>
                )}
              </button>
            </div>

            {/* Powder-Style Moment Filter Chips */}
            {clips.length > 0 && (
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-[11px]">
                <button
                  onClick={() => setActiveFilter('all')}
                  className={`px-2.5 py-1 rounded-full font-bold transition-all shrink-0 ${
                    activeFilter === 'all'
                      ? 'bg-white text-black'
                      : 'bg-[#181c2b] text-gray-400 hover:text-white'
                  }`}
                >
                  All ({clips.length})
                </button>
                <button
                  onClick={() => setActiveFilter('kills')}
                  className={`px-2.5 py-1 rounded-full font-bold transition-all shrink-0 ${
                    activeFilter === 'kills'
                      ? 'bg-purple-600 text-white'
                      : 'bg-[#181c2b] text-gray-400 hover:text-white'
                  }`}
                >
                  💀 Kills
                </button>
                <button
                  onClick={() => setActiveFilter('victory')}
                  className={`px-2.5 py-1 rounded-full font-bold transition-all shrink-0 ${
                    activeFilter === 'victory'
                      ? 'bg-emerald-600 text-white'
                      : 'bg-[#181c2b] text-gray-400 hover:text-white'
                  }`}
                >
                  👑 Victory
                </button>
                <button
                  onClick={() => setActiveFilter('laughter')}
                  className={`px-2.5 py-1 rounded-full font-bold transition-all shrink-0 ${
                    activeFilter === 'laughter'
                      ? 'bg-amber-600 text-white'
                      : 'bg-[#181c2b] text-gray-400 hover:text-white'
                  }`}
                >
                  😂 Laughter
                </button>
              </div>
            )}

            {/* List of Discovered Highlight Cards */}
            <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
              {clips.length === 0 ? (
                <div className="p-8 text-center border border-dashed border-[#232738] rounded-xl text-gray-500 space-y-2">
                  <Flame className="w-8 h-8 mx-auto text-gray-600" />
                  <p className="text-xs font-semibold">No highlights discovered yet</p>
                  <p className="text-[11px] text-gray-600">
                    Click 'Scan & Discover Viral Moments' above or select clips manually on the timeline!
                  </p>
                </div>
              ) : (
                clips.map((clip, index) => {
                  const isSelected = clip.selected !== false;
                  return (
                    <div
                      key={index}
                      onClick={() => seekTo(clip.start)}
                      className={`p-3.5 rounded-xl border transition-all cursor-pointer group ${
                        isSelected
                          ? 'bg-[#161a29] border-purple-500/50 ring-1 ring-purple-500/30'
                          : 'bg-[#0d0f17] border-[#202538] opacity-70 hover:opacity-100'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              onToggleClipSelection(index);
                            }}
                            className="text-purple-400 hover:text-purple-300"
                          >
                            {isSelected ? (
                              <CheckSquare className="w-4 h-4 fill-purple-500/30 text-purple-400" />
                            ) : (
                              <Square className="w-4 h-4 text-gray-500" />
                            )}
                          </button>
                          <span className="font-extrabold text-xs text-white">
                            Moment #{index + 1}
                          </span>
                          <span className="text-[10px] bg-purple-500/20 text-purple-300 border border-purple-500/30 px-1.5 py-0.5 rounded font-mono font-bold flex items-center gap-1">
                            <Zap className="w-3 h-3 fill-current" />
                            {clip.score}
                          </span>
                        </div>
                        <span className="text-[11px] font-mono text-gray-400">
                          {formatTime(clip.start)} - {formatTime(clip.end)} ({Math.round(clip.end - clip.start)}s)
                        </span>
                      </div>

                      <p className="text-xs text-gray-300 line-clamp-2 mb-3">
                        {clip.reason}
                      </p>

                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-gray-500 flex items-center gap-1">
                          <Play className="w-3 h-3 text-[#ccff00]" /> Click to preview
                        </span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            seekTo(clip.start);
                            setInPoint(clip.start);
                            setOutPoint(clip.end);
                          }}
                          className="text-[10px] bg-[#22283e] hover:bg-[#2e3754] text-gray-200 px-2 py-1 rounded font-bold"
                        >
                          Load into Timeline
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Bottom Render CTA */}
            {clips.length > 0 && (
              <div className="pt-2">
                <button
                  disabled={isRendering || selectedClipsCount === 0}
                  onClick={onTriggerRender}
                  className="w-full py-3.5 rounded-xl bg-[#ccff00] hover:bg-[#b8e600] text-black font-black text-sm uppercase tracking-wider transition-all shadow-xl shadow-[#ccff00]/25 flex items-center justify-center gap-2 hover:scale-[1.02] active:scale-[0.98] disabled:bg-gray-800 disabled:text-gray-500 disabled:shadow-none"
                >
                  <Zap className="w-5 h-5 fill-black" />
                  <span>
                    CREATE {selectedClipsCount} {selectedClipsCount === 1 ? 'CLIP' : 'CLIPS'}
                  </span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
