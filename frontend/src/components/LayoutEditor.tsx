import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  SplitSquareVertical,
  Check,
  Move,
  Clock,
  Eye,
  Plus,
  Trash2,
  Lock,
  Unlock,
  Grid,
  RotateCcw,
  RotateCw,
  Sliders,
  ShieldAlert,
  Smartphone,
  ChevronRight,
  Sparkles
} from 'lucide-react';
import type {
  GamingLayoutConfig,
  SingleCropConfig,
  ScreenMode,
  SessionData,
  ActiveTab,
  SceneKeyframe,
  SafeZoneType
} from '../types';

interface LayoutEditorProps {
  session: SessionData | null;
  screenMode: ScreenMode;
  setScreenMode: (mode: ScreenMode) => void;
  gamingConfig: GamingLayoutConfig;
  setGamingConfig: React.Dispatch<React.SetStateAction<GamingLayoutConfig>>;
  singleCropConfig: SingleCropConfig;
  setSingleCropConfig: React.Dispatch<React.SetStateAction<SingleCropConfig>>;
  sceneKeyframes?: SceneKeyframe[];
  setSceneKeyframes?: (keyframes: SceneKeyframe[]) => void;
  onFetchFrameAtTime: (timestamp: number) => Promise<string>;
  setActiveTab: (tab: ActiveTab) => void;
}

export const LayoutEditor: React.FC<LayoutEditorProps> = ({
  session,
  screenMode,
  setScreenMode,
  gamingConfig,
  setGamingConfig,
  singleCropConfig,
  setSingleCropConfig,
  sceneKeyframes = [],
  setSceneKeyframes,
  onFetchFrameAtTime,
  setActiveTab
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Active frame image URL & scrubbing timestamp
  const [frameUrl, setFrameUrl] = useState<string>(session?.preview_url || '');
  const [frameTimestamp, setFrameTimestamp] = useState<number>(45);

  // Toggles & Helpers
  const [snapToGrid, setSnapToGrid] = useState<boolean>(true);
  const [lockAspect, setLockAspect] = useState<boolean>(false);
  const [safeZone, setSafeZone] = useState<SafeZoneType>('youtube');
  const [showGuides, setShowGuides] = useState<boolean>(false);

  // Styling properties
  const faceOpacity = gamingConfig.face_opacity ?? 1.0;
  const faceBorder = gamingConfig.face_border ?? 2;
  const faceRounded = gamingConfig.face_rounded ?? 8;
  const blurIntensity = gamingConfig.blur_intensity ?? 22;
  const faceHeightPct = gamingConfig.face_height_pct ?? 40;

  // Layout Undo / Redo History
  const [layoutHistory, setLayoutHistory] = useState<{
    gaming: GamingLayoutConfig;
    single: SingleCropConfig;
    mode: ScreenMode;
  }[]>([]);
  const [layoutRedo, setLayoutRedo] = useState<{
    gaming: GamingLayoutConfig;
    single: SingleCropConfig;
    mode: ScreenMode;
  }[]>([]);

  // Drag & Resize State
  const [activeDrag, setActiveDrag] = useState<{
    target: 'face' | 'game' | 'single';
    handle: 'move' | 'nw' | 'ne' | 'se' | 'sw' | 'n' | 's' | 'e' | 'w';
    startX: number;
    startY: number;
    initialX: number;
    initialY: number;
    initialW: number;
    initialH: number;
  } | null>(null);

  const pushLayoutHistory = () => {
    setLayoutHistory((prev) => [
      ...prev,
      { gaming: { ...gamingConfig }, single: { ...singleCropConfig }, mode: screenMode }
    ]);
    setLayoutRedo([]);
  };

  const handleUndoLayout = () => {
    if (layoutHistory.length === 0) return;
    const prev = layoutHistory[layoutHistory.length - 1];
    setLayoutRedo((r) => [
      ...r,
      { gaming: { ...gamingConfig }, single: { ...singleCropConfig }, mode: screenMode }
    ]);
    setLayoutHistory((h) => h.slice(0, h.length - 1));
    setGamingConfig(prev.gaming);
    setSingleCropConfig(prev.single);
    setScreenMode(prev.mode);
  };

  const handleRedoLayout = () => {
    if (layoutRedo.length === 0) return;
    const next = layoutRedo[layoutRedo.length - 1];
    setLayoutHistory((h) => [
      ...h,
      { gaming: { ...gamingConfig }, single: { ...singleCropConfig }, mode: screenMode }
    ]);
    setLayoutRedo((r) => r.slice(0, r.length - 1));
    setGamingConfig(next.gaming);
    setSingleCropConfig(next.single);
    setScreenMode(next.mode);
  };

  const resetToDefaultLayout = () => {
    pushLayoutHistory();
    setGamingConfig({
      face_x: 65,
      face_y: 58,
      face_w: 33,
      face_h: 40,
      game_x: 5,
      game_y: 5,
      game_w: 90,
      game_h: 90,
      face_height_pct: 40,
      face_opacity: 1.0,
      face_border: 2,
      face_rounded: 8,
      blur_intensity: 22
    });
    setSingleCropConfig({
      crop_x: 28,
      crop_y: 0,
      crop_w: 44,
      crop_h: 100
    });
  };

  // Sync session preview_url
  useEffect(() => {
    if (session?.preview_url && !frameUrl) {
      setFrameUrl(session.preview_url);
    }
  }, [session?.preview_url, frameUrl]);

  // Fetch frame at specified timestamp
  const handleLoadFrame = async (timestamp: number) => {
    setFrameTimestamp(timestamp);
    try {
      const url = await onFetchFrameAtTime(timestamp);
      setFrameUrl(url);
    } catch (err) {
      console.error('Failed to load frame snapshot:', err);
    }
  };

  // Streamer Presets
  const applyPreset = (preset: string) => {
    pushLayoutHistory();
    if (preset === 'bottom-right') {
      setGamingConfig((prev) => ({
        ...prev,
        face_x: 65,
        face_y: 60,
        face_w: 33,
        face_h: 38,
        game_x: 10,
        game_y: 5,
        game_w: 80,
        game_h: 90
      }));
    } else if (preset === 'top-right') {
      setGamingConfig((prev) => ({
        ...prev,
        face_x: 65,
        face_y: 5,
        face_w: 33,
        face_h: 38,
        game_x: 5,
        game_y: 5,
        game_w: 80,
        game_h: 90
      }));
    } else if (preset === 'bottom-left') {
      setGamingConfig((prev) => ({
        ...prev,
        face_x: 2,
        face_y: 60,
        face_w: 33,
        face_h: 38,
        game_x: 15,
        game_y: 5,
        game_w: 80,
        game_h: 90
      }));
    } else if (preset === 'center-top') {
      setGamingConfig((prev) => ({
        ...prev,
        face_x: 35,
        face_y: 0,
        face_w: 30,
        face_h: 40,
        game_x: 10,
        game_y: 10,
        game_w: 80,
        game_h: 80
      }));
    }
  };

  // Drag & Multi-Handle Mouse Events
  const handleMouseDown = (
    e: React.MouseEvent,
    target: 'face' | 'game' | 'single',
    handle: 'move' | 'nw' | 'ne' | 'se' | 'sw' | 'n' | 's' | 'e' | 'w'
  ) => {
    e.stopPropagation();
    e.preventDefault();
    if (!containerRef.current) return;
    pushLayoutHistory();

    let initX = 0, initY = 0, initW = 0, initH = 0;
    if (target === 'face') {
      initX = gamingConfig.face_x;
      initY = gamingConfig.face_y;
      initW = gamingConfig.face_w;
      initH = gamingConfig.face_h;
    } else if (target === 'game') {
      initX = gamingConfig.game_x;
      initY = gamingConfig.game_y;
      initW = gamingConfig.game_w;
      initH = gamingConfig.game_h;
    } else {
      initX = singleCropConfig.crop_x;
      initY = singleCropConfig.crop_y;
      initW = singleCropConfig.crop_w;
      initH = singleCropConfig.crop_h;
    }

    setActiveDrag({
      target,
      handle,
      startX: e.clientX,
      startY: e.clientY,
      initialX: initX,
      initialY: initY,
      initialW: initW,
      initialH: initH
    });
    setShowGuides(true);
  };

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!activeDrag || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      let deltaX = ((e.clientX - activeDrag.startX) / rect.width) * 100;
      let deltaY = ((e.clientY - activeDrag.startY) / rect.height) * 100;

      const snap = (val: number, step: number = 2) => (snapToGrid ? Math.round(val / step) * step : val);

      if (activeDrag.handle === 'move') {
        let newX = Math.max(0, Math.min(100 - activeDrag.initialW, activeDrag.initialX + deltaX));
        let newY = Math.max(0, Math.min(100 - activeDrag.initialH, activeDrag.initialY + deltaY));
        newX = snap(newX);
        newY = snap(newY);

        if (activeDrag.target === 'face') {
          setGamingConfig((prev) => ({ ...prev, face_x: newX, face_y: newY }));
        } else if (activeDrag.target === 'game') {
          setGamingConfig((prev) => ({ ...prev, game_x: newX, game_y: newY }));
        } else {
          setSingleCropConfig((prev) => ({ ...prev, crop_x: newX, crop_y: newY }));
        }
      } else {
        // Handle resizing from corners or edges
        let newW = activeDrag.initialW;
        let newH = activeDrag.initialH;
        let newX = activeDrag.initialX;
        let newY = activeDrag.initialY;

        if (activeDrag.handle.includes('e')) {
          newW = Math.max(10, Math.min(100 - activeDrag.initialX, activeDrag.initialW + deltaX));
        }
        if (activeDrag.handle.includes('s')) {
          newH = Math.max(10, Math.min(100 - activeDrag.initialY, activeDrag.initialH + deltaY));
        }
        if (activeDrag.handle.includes('w')) {
          const maxLeftShift = activeDrag.initialX + activeDrag.initialW - 10;
          newX = Math.max(0, Math.min(maxLeftShift, activeDrag.initialX + deltaX));
          newW = activeDrag.initialW - (newX - activeDrag.initialX);
        }
        if (activeDrag.handle.includes('n')) {
          const maxTopShift = activeDrag.initialY + activeDrag.initialH - 10;
          newY = Math.max(0, Math.min(maxTopShift, activeDrag.initialY + deltaY));
          newH = activeDrag.initialH - (newY - activeDrag.initialY);
        }

        if (lockAspect) {
          const ratio = activeDrag.initialW / Math.max(1, activeDrag.initialH);
          newH = newW / ratio;
        }

        newX = snap(newX);
        newY = snap(newY);
        newW = snap(newW);
        newH = snap(newH);

        if (activeDrag.target === 'face') {
          setGamingConfig((prev) => ({ ...prev, face_x: newX, face_y: newY, face_w: newW, face_h: newH }));
        } else if (activeDrag.target === 'game') {
          setGamingConfig((prev) => ({ ...prev, game_x: newX, game_y: newY, game_w: newW, game_h: newH }));
        } else {
          setSingleCropConfig((prev) => ({ ...prev, crop_x: newX, crop_y: newY, crop_w: newW, crop_h: newH }));
        }
      }
    },
    [activeDrag, snapToGrid, lockAspect, setGamingConfig, setSingleCropConfig]
  );

  const handleMouseUp = useCallback(() => {
    setActiveDrag(null);
    setShowGuides(false);
  }, []);

  useEffect(() => {
    if (activeDrag) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [activeDrag, handleMouseMove, handleMouseUp]);

  // Keyframe Actions
  const handleAddKeyframe = () => {
    if (!setSceneKeyframes) return;
    const newKf: SceneKeyframe = {
      id: `kf_${Date.now()}`,
      timestamp: frameTimestamp,
      layout_mode: screenMode,
      gaming_config: { ...gamingConfig },
      single_crop_config: { ...singleCropConfig },
      transition: 'linear'
    };
    const updated = [...sceneKeyframes.filter((k) => Math.abs(k.timestamp - frameTimestamp) > 1), newKf];
    updated.sort((a, b) => a.timestamp - b.timestamp);
    setSceneKeyframes(updated);
  };

  const handleRemoveKeyframe = (id: string) => {
    if (!setSceneKeyframes) return;
    setSceneKeyframes(sceneKeyframes.filter((k) => k.id !== id));
  };

  const handleApplyKeyframe = (kf: SceneKeyframe) => {
    pushLayoutHistory();
    setScreenMode(kf.layout_mode);
    setGamingConfig(kf.gaming_config);
    setSingleCropConfig(kf.single_crop_config);
    handleLoadFrame(kf.timestamp);
  };

  return (
    <div className="p-6 max-w-[1650px] mx-auto space-y-6 animate-fadeIn">
      {/* Top Controls: Mode, Alignment Helpers, History */}
      <div className="bg-[#121522] border border-[#232738] rounded-2xl p-6 shadow-xl space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-black text-white tracking-tight flex items-center gap-2">
              <SplitSquareVertical className="w-5 h-5 text-[#ccff00]" />
              <span>Interactive Layout & Visual Alignment Studio</span>
            </h2>
            <p className="text-xs text-gray-400 mt-1">
              Drag green facecam and cyan gameplay regions directly on your source frame. Live 9:16 phone mockup mirrors rendering exactly.
            </p>
          </div>

          {/* Alignment Tools: Snap, Lock Aspect, Undo/Redo */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSnapToGrid(!snapToGrid)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 border transition-all ${
                snapToGrid
                  ? 'bg-[#ccff00]/15 text-[#ccff00] border-[#ccff00]/40'
                  : 'bg-[#181c2b] text-gray-400 border-[#262c3f]'
              }`}
            >
              <Grid className="w-3.5 h-3.5" />
              <span>Snap (2%)</span>
            </button>

            <button
              onClick={() => setLockAspect(!lockAspect)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 border transition-all ${
                lockAspect
                  ? 'bg-cyan-500/15 text-cyan-400 border-cyan-500/40'
                  : 'bg-[#181c2b] text-gray-400 border-[#262c3f]'
              }`}
            >
              {lockAspect ? <Lock className="w-3.5 h-3.5" /> : <Unlock className="w-3.5 h-3.5" />}
              <span>Lock Aspect</span>
            </button>

            <button
              onClick={handleUndoLayout}
              disabled={layoutHistory.length === 0}
              className="p-1.5 rounded-lg bg-[#181c2b] text-gray-400 hover:text-white disabled:opacity-30 border border-[#262c3f]"
              title="Undo Layout (Ctrl+Z)"
            >
              <RotateCcw className="w-4 h-4" />
            </button>

            <button
              onClick={handleRedoLayout}
              disabled={layoutRedo.length === 0}
              className="p-1.5 rounded-lg bg-[#181c2b] text-gray-400 hover:text-white disabled:opacity-30 border border-[#262c3f]"
              title="Redo Layout (Ctrl+Y)"
            >
              <RotateCw className="w-4 h-4" />
            </button>

            <button
              onClick={resetToDefaultLayout}
              className="px-3 py-1.5 rounded-lg bg-[#181c2b] text-gray-300 hover:text-white border border-[#262c3f] text-xs font-bold"
            >
              Reset
            </button>
          </div>
        </div>

        {/* Screen Mode Tabs */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <button
            type="button"
            onClick={() => {
              pushLayoutHistory();
              setScreenMode('gaming_split');
            }}
            className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
              screenMode === 'gaming_split'
                ? 'bg-[#1a1f30] border-[#ccff00] ring-1 ring-[#ccff00]/40 shadow-lg'
                : 'bg-[#0d0f17] border-[#202538] hover:border-gray-600'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-extrabold text-xs text-white flex items-center gap-1.5">
                🎮 Gaming Split
              </span>
              {screenMode === 'gaming_split' && (
                <span className="text-[10px] bg-[#ccff00] text-black font-black px-1.5 py-0.5 rounded">
                  ACTIVE
                </span>
              )}
            </div>
            <p className="text-[11px] text-gray-400">
              Facecam on Top ({faceHeightPct}%) + Gameplay on Bottom ({100 - faceHeightPct}%)
            </p>
          </button>

          <button
            type="button"
            onClick={() => {
              pushLayoutHistory();
              setScreenMode('crop');
            }}
            className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
              screenMode === 'crop'
                ? 'bg-[#1a1f30] border-[#00d2ff] ring-1 ring-[#00d2ff]/40 shadow-lg'
                : 'bg-[#0d0f17] border-[#202538] hover:border-gray-600'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-extrabold text-xs text-white flex items-center gap-1.5">
                📱 Single Screen 9:16
              </span>
              {screenMode === 'crop' && (
                <span className="text-[10px] bg-[#00d2ff] text-black font-black px-1.5 py-0.5 rounded">
                  ACTIVE
                </span>
              )}
            </div>
            <p className="text-[11px] text-gray-400">
              Full 9:16 portrait crop focused directly on central gaming action
            </p>
          </button>

          <button
            type="button"
            onClick={() => {
              pushLayoutHistory();
              setScreenMode('blur_fit');
            }}
            className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
              screenMode === 'blur_fit'
                ? 'bg-[#1a1f30] border-purple-500 ring-1 ring-purple-500/40 shadow-lg'
                : 'bg-[#0d0f17] border-[#202538] hover:border-gray-600'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-extrabold text-xs text-white flex items-center gap-1.5">
                🎬 Cinematic Blur Fit
              </span>
              {screenMode === 'blur_fit' && (
                <span className="text-[10px] bg-purple-500 text-white font-black px-1.5 py-0.5 rounded">
                  ACTIVE
                </span>
              )}
            </div>
            <p className="text-[11px] text-gray-400">
              16:9 gameplay centered with dynamic ambient background blur
            </p>
          </button>
        </div>

        {/* Streamer Presets & Frame Scrubbing Bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-[#1f2333]">
          {screenMode === 'gaming_split' && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-gray-300">Facecam Presets:</span>
              <div className="flex flex-wrap gap-1.5">
                {[
                  { id: 'bottom-right', label: 'Bottom-Right' },
                  { id: 'top-right', label: 'Top-Right' },
                  { id: 'bottom-left', label: 'Bottom-Left' },
                  { id: 'center-top', label: 'Center-Top' }
                ].map((p) => (
                  <button
                    key={p.id}
                    onClick={() => applyPreset(p.id)}
                    className="px-2.5 py-1 rounded-lg bg-[#1a1f30] hover:bg-[#28314e] text-xs font-semibold text-gray-300 border border-[#2b334d]"
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Frame Time Snapshot Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-gray-300 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-[#ccff00]" />
              <span>Snapshot at:</span>
            </span>
            <div className="flex items-center gap-1.5">
              {[0, 30, 60, 120, 240].map((sec) => (
                <button
                  key={sec}
                  onClick={() => handleLoadFrame(sec)}
                  className={`px-2 py-0.5 rounded text-xs font-mono font-bold ${
                    frameTimestamp === sec
                      ? 'bg-[#ccff00] text-black font-black'
                      : 'bg-[#181c2b] text-gray-400 hover:text-white'
                  }`}
                >
                  {Math.floor(sec / 60)}m {sec % 60}s
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Scene Keyframes Track */}
        <div className="pt-3 border-t border-[#1f2333] space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-bold text-white">
              <Sparkles className="w-4 h-4 text-[#ccff00]" />
              <span>Scene Timestamp Keyframes (Different Layouts at Different Times)</span>
            </div>
            <button
              onClick={handleAddKeyframe}
              className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-[#ccff00]/20 text-[#ccff00] hover:bg-[#ccff00]/30 border border-[#ccff00]/40 text-xs font-bold"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Keyframe at {frameTimestamp}s</span>
            </button>
          </div>

          <div className="flex items-center gap-2 overflow-x-auto py-1">
            {sceneKeyframes.length === 0 ? (
              <span className="text-[11px] text-gray-500 font-mono">
                No keyframes saved. Add a keyframe to change facecam position during gameplay transitions.
              </span>
            ) : (
              sceneKeyframes.map((kf) => (
                <div
                  key={kf.id}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#161a29] border border-[#2b334a] text-xs font-mono"
                >
                  <button
                    onClick={() => handleApplyKeyframe(kf)}
                    className="font-bold text-[#ccff00] hover:underline"
                  >
                    ⏱ {Math.floor(kf.timestamp / 60)}m {kf.timestamp % 60}s ({kf.layout_mode})
                  </button>
                  <button
                    onClick={() => handleRemoveKeyframe(kf.id)}
                    className="text-gray-400 hover:text-red-400"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Dual Visual Canvas: Left 16:9 Frame | Right 9:16 Mockup */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: 16:9 Frame with Interactive Drag Boxes (8 cols) */}
        <div className="lg:col-span-8 space-y-3">
          <div className="flex items-center justify-between text-xs font-bold text-gray-300 px-1">
            <span className="flex items-center gap-1.5">
              <Move className="w-4 h-4 text-[#ccff00]" />
              <span>1. Click & Drag Bounding Boxes on 16:9 Video Frame</span>
            </span>
            <span className="text-[11px] text-gray-400">
              Drag box to reposition • Drag corner & edge handles to resize
            </span>
          </div>

          <div
            ref={containerRef}
            className="relative w-full aspect-video bg-black rounded-2xl overflow-hidden border-2 border-[#2a2f42] shadow-2xl select-none"
          >
            {frameUrl ? (
              <img
                src={frameUrl}
                alt="Source Frame Snapshot"
                className="w-full h-full object-contain pointer-events-none"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-xs text-gray-500 font-mono">
                Loading video frame snapshot...
              </div>
            )}

            {/* Alignment Guides */}
            {showGuides && (
              <>
                <div className="absolute top-0 bottom-0 left-1/2 w-px bg-cyan-400/40 pointer-events-none" />
                <div className="absolute left-0 right-0 top-1/2 h-px bg-cyan-400/40 pointer-events-none" />
              </>
            )}

            {/* GAMING SPLIT: GREEN FACECAM BOX WITH MULTI-HANDLES */}
            {screenMode === 'gaming_split' && (
              <div
                onMouseDown={(e) => handleMouseDown(e, 'face', 'move')}
                className="absolute border-2 border-[#ccff00] bg-[#ccff00]/15 cursor-move rounded-md group shadow-lg"
                style={{
                  left: `${gamingConfig.face_x}%`,
                  top: `${gamingConfig.face_y}%`,
                  width: `${gamingConfig.face_w}%`,
                  height: `${gamingConfig.face_h}%`
                }}
              >
                {/* Header Badge */}
                <div className="absolute -top-6 left-0 bg-[#ccff00] text-black text-[10px] font-black px-1.5 py-0.5 rounded shadow">
                  🟢 Facecam (Top {faceHeightPct}%)
                </div>

                {/* 4 Corner Resize Handles */}
                <div
                  onMouseDown={(e) => handleMouseDown(e, 'face', 'nw')}
                  className="absolute -top-1.5 -left-1.5 w-3.5 h-3.5 bg-[#ccff00] rounded-sm border border-black cursor-nw-resize shadow"
                />
                <div
                  onMouseDown={(e) => handleMouseDown(e, 'face', 'ne')}
                  className="absolute -top-1.5 -right-1.5 w-3.5 h-3.5 bg-[#ccff00] rounded-sm border border-black cursor-ne-resize shadow"
                />
                <div
                  onMouseDown={(e) => handleMouseDown(e, 'face', 'se')}
                  className="absolute -bottom-1.5 -right-1.5 w-4 h-4 bg-[#ccff00] rounded-full border border-black cursor-se-resize shadow ring-2 ring-black/40"
                />
                <div
                  onMouseDown={(e) => handleMouseDown(e, 'face', 'sw')}
                  className="absolute -bottom-1.5 -left-1.5 w-3.5 h-3.5 bg-[#ccff00] rounded-sm border border-black cursor-sw-resize shadow"
                />

                {/* Edge Handles */}
                <div
                  onMouseDown={(e) => handleMouseDown(e, 'face', 'e')}
                  className="absolute top-1/2 -right-1 w-2 h-4 -translate-y-1/2 bg-[#ccff00] rounded cursor-e-resize"
                />
                <div
                  onMouseDown={(e) => handleMouseDown(e, 'face', 's')}
                  className="absolute bottom-[-4px] left-1/2 -translate-x-1/2 w-4 h-2 bg-[#ccff00] rounded cursor-s-resize"
                />
              </div>
            )}

            {/* GAMING SPLIT: CYAN GAMEPLAY BOX WITH MULTI-HANDLES */}
            {screenMode === 'gaming_split' && (
              <div
                onMouseDown={(e) => handleMouseDown(e, 'game', 'move')}
                className="absolute border-2 border-[#00d2ff] bg-[#00d2ff]/15 cursor-move rounded-md group shadow-lg"
                style={{
                  left: `${gamingConfig.game_x}%`,
                  top: `${gamingConfig.game_y}%`,
                  width: `${gamingConfig.game_w}%`,
                  height: `${gamingConfig.game_h}%`
                }}
              >
                <div className="absolute -top-6 left-0 bg-[#00d2ff] text-black text-[10px] font-black px-1.5 py-0.5 rounded shadow">
                  🔵 Main Gameplay (Bottom {100 - faceHeightPct}%)
                </div>

                <div
                  onMouseDown={(e) => handleMouseDown(e, 'game', 'nw')}
                  className="absolute -top-1.5 -left-1.5 w-3.5 h-3.5 bg-[#00d2ff] rounded-sm border border-black cursor-nw-resize shadow"
                />
                <div
                  onMouseDown={(e) => handleMouseDown(e, 'game', 'ne')}
                  className="absolute -top-1.5 -right-1.5 w-3.5 h-3.5 bg-[#00d2ff] rounded-sm border border-black cursor-ne-resize shadow"
                />
                <div
                  onMouseDown={(e) => handleMouseDown(e, 'game', 'se')}
                  className="absolute -bottom-1.5 -right-1.5 w-4 h-4 bg-[#00d2ff] rounded-full border border-black cursor-se-resize shadow ring-2 ring-black/40"
                />
                <div
                  onMouseDown={(e) => handleMouseDown(e, 'game', 'sw')}
                  className="absolute -bottom-1.5 -left-1.5 w-3.5 h-3.5 bg-[#00d2ff] rounded-sm border border-black cursor-sw-resize shadow"
                />

                <div
                  onMouseDown={(e) => handleMouseDown(e, 'game', 'e')}
                  className="absolute top-1/2 -right-1 w-2 h-4 -translate-y-1/2 bg-[#00d2ff] rounded cursor-e-resize"
                />
                <div
                  onMouseDown={(e) => handleMouseDown(e, 'game', 's')}
                  className="absolute bottom-[-4px] left-1/2 -translate-x-1/2 w-4 h-2 bg-[#00d2ff] rounded cursor-s-resize"
                />
              </div>
            )}

            {/* SINGLE SCREEN CROP: 9:16 CYAN BOX */}
            {screenMode === 'crop' && (
              <div
                onMouseDown={(e) => handleMouseDown(e, 'single', 'move')}
                className="absolute border-2 border-[#00d2ff] bg-[#00d2ff]/20 cursor-move rounded-md"
                style={{
                  left: `${singleCropConfig.crop_x}%`,
                  top: `${singleCropConfig.crop_y}%`,
                  width: `${singleCropConfig.crop_w}%`,
                  height: `${singleCropConfig.crop_h}%`
                }}
              >
                <div className="absolute -top-6 left-0 bg-[#00d2ff] text-black text-[10px] font-black px-1.5 py-0.5 rounded shadow">
                  📱 Full 9:16 Portrait Crop
                </div>
                <div
                  onMouseDown={(e) => handleMouseDown(e, 'single', 'se')}
                  className="absolute -bottom-1.5 -right-1.5 w-4 h-4 bg-[#00d2ff] rounded-full border border-black cursor-se-resize shadow"
                />
              </div>
            )}
          </div>

          {/* Advanced Fine-Tuning & Styling Sliders */}
          <div className="bg-[#121522] border border-[#232738] rounded-xl p-4 space-y-4 text-xs">
            {screenMode === 'gaming_split' ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Facecam styling */}
                <div className="space-y-3 bg-[#0d0f17] p-3 rounded-lg border border-[#1f2438]">
                  <div className="font-bold text-[#ccff00] flex items-center justify-between">
                    <span>Facecam Styling</span>
                    <span className="font-mono text-gray-400">
                      {gamingConfig.face_w}% x {gamingConfig.face_h}%
                    </span>
                  </div>

                  <div className="flex items-center gap-2 text-gray-400 text-[11px]">
                    <span className="w-24">Height Split:</span>
                    <input
                      type="range"
                      min="25"
                      max="65"
                      value={faceHeightPct}
                      onChange={(e) =>
                        setGamingConfig((prev) => ({
                          ...prev,
                          face_height_pct: Number(e.target.value)
                        }))
                      }
                      className="flex-1 accent-[#ccff00]"
                    />
                    <span className="font-mono w-10 text-right">{faceHeightPct}%</span>
                  </div>

                  <div className="flex items-center gap-2 text-gray-400 text-[11px]">
                    <span className="w-24">Corner Radius:</span>
                    <input
                      type="range"
                      min="0"
                      max="24"
                      value={faceRounded}
                      onChange={(e) =>
                        setGamingConfig((prev) => ({
                          ...prev,
                          face_rounded: Number(e.target.value)
                        }))
                      }
                      className="flex-1 accent-[#ccff00]"
                    />
                    <span className="font-mono w-10 text-right">{faceRounded}px</span>
                  </div>

                  <div className="flex items-center gap-2 text-gray-400 text-[11px]">
                    <span className="w-24">Border Width:</span>
                    <input
                      type="range"
                      min="0"
                      max="6"
                      value={faceBorder}
                      onChange={(e) =>
                        setGamingConfig((prev) => ({
                          ...prev,
                          face_border: Number(e.target.value)
                        }))
                      }
                      className="flex-1 accent-[#ccff00]"
                    />
                    <span className="font-mono w-10 text-right">{faceBorder}px</span>
                  </div>

                  <div className="flex items-center gap-2 text-gray-400 text-[11px]">
                    <span className="w-24">Opacity:</span>
                    <input
                      type="range"
                      min="0.3"
                      max="1.0"
                      step="0.05"
                      value={faceOpacity}
                      onChange={(e) =>
                        setGamingConfig((prev) => ({
                          ...prev,
                          face_opacity: Number(e.target.value)
                        }))
                      }
                      className="flex-1 accent-[#ccff00]"
                    />
                    <span className="font-mono w-10 text-right">{Math.round(faceOpacity * 100)}%</span>
                  </div>
                </div>

                {/* Gameplay & Canvas Fine Tuning */}
                <div className="space-y-3 bg-[#0d0f17] p-3 rounded-lg border border-[#1f2438]">
                  <div className="font-bold text-[#00d2ff] flex items-center justify-between">
                    <span>Gameplay Region Fine-Tuning</span>
                    <span className="font-mono text-gray-400">
                      {gamingConfig.game_w}% x {gamingConfig.game_h}%
                    </span>
                  </div>

                  <div className="flex items-center gap-2 text-gray-400 text-[11px]">
                    <span className="w-20">Game X:</span>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={gamingConfig.game_x}
                      onChange={(e) =>
                        setGamingConfig((prev) => ({ ...prev, game_x: Number(e.target.value) }))
                      }
                      className="flex-1 accent-[#00d2ff]"
                    />
                    <span className="font-mono w-10 text-right">{gamingConfig.game_x}%</span>
                  </div>

                  <div className="flex items-center gap-2 text-gray-400 text-[11px]">
                    <span className="w-20">Game Y:</span>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={gamingConfig.game_y}
                      onChange={(e) =>
                        setGamingConfig((prev) => ({ ...prev, game_y: Number(e.target.value) }))
                      }
                      className="flex-1 accent-[#00d2ff]"
                    />
                    <span className="font-mono w-10 text-right">{gamingConfig.game_y}%</span>
                  </div>

                  <div className="flex items-center gap-2 text-gray-400 text-[11px]">
                    <span className="w-20">Game Width:</span>
                    <input
                      type="range"
                      min="20"
                      max="100"
                      value={gamingConfig.game_w}
                      onChange={(e) =>
                        setGamingConfig((prev) => ({ ...prev, game_w: Number(e.target.value) }))
                      }
                      className="flex-1 accent-[#00d2ff]"
                    />
                    <span className="font-mono w-10 text-right">{gamingConfig.game_w}%</span>
                  </div>

                  <div className="flex items-center gap-2 text-gray-400 text-[11px]">
                    <span className="w-20">Game Height:</span>
                    <input
                      type="range"
                      min="20"
                      max="100"
                      value={gamingConfig.game_h}
                      onChange={(e) =>
                        setGamingConfig((prev) => ({ ...prev, game_h: Number(e.target.value) }))
                      }
                      className="flex-1 accent-[#00d2ff]"
                    />
                    <span className="font-mono w-10 text-right">{gamingConfig.game_h}%</span>
                  </div>
                </div>
              </div>
            ) : screenMode === 'crop' ? (
              <div className="space-y-3 bg-[#0d0f17] p-3 rounded-lg border border-[#1f2438]">
                <div className="font-bold text-[#00d2ff] flex items-center justify-between">
                  <span>9:16 Portrait Crop Area</span>
                  <span className="font-mono text-gray-400">
                    X: {singleCropConfig.crop_x}%, Width: {singleCropConfig.crop_w}%
                  </span>
                </div>
                <div className="flex items-center gap-2 text-gray-400 text-[11px]">
                  <span className="w-20">Crop X:</span>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={singleCropConfig.crop_x}
                    onChange={(e) =>
                      setSingleCropConfig((prev) => ({ ...prev, crop_x: Number(e.target.value) }))
                    }
                    className="flex-1 accent-[#00d2ff]"
                  />
                  <span className="font-mono w-10 text-right">{singleCropConfig.crop_x}%</span>
                </div>
              </div>
            ) : (
              <div className="space-y-3 bg-[#0d0f17] p-3 rounded-lg border border-[#1f2438]">
                <div className="font-bold text-purple-400 flex items-center justify-between">
                  <span>Cinematic Ambient Blur Settings</span>
                  <span className="font-mono text-gray-400">Intensity: {blurIntensity}</span>
                </div>
                <div className="flex items-center gap-2 text-gray-400 text-[11px]">
                  <span className="w-24">Blur Strength:</span>
                  <input
                    type="range"
                    min="5"
                    max="45"
                    value={blurIntensity}
                    onChange={(e) =>
                      setGamingConfig((prev) => ({ ...prev, blur_intensity: Number(e.target.value) }))
                    }
                    className="flex-1 accent-purple-500"
                  />
                  <span className="font-mono w-10 text-right">{blurIntensity}</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right: Live 9:16 Phone Mockup Preview + Platform Safe Zones (4 cols) */}
        <div className="lg:col-span-4 space-y-3">
          <div className="flex items-center justify-between text-xs font-bold text-gray-300 px-1">
            <span className="flex items-center gap-1.5">
              <Eye className="w-4 h-4 text-[#ccff00]" />
              <span>2. Exact 9:16 Mobile Mockup</span>
            </span>

            {/* Platform Safe-Zone Toggle */}
            <div className="flex items-center gap-1">
              <span className="text-[10px] text-gray-400">Safe:</span>
              <select
                value={safeZone}
                onChange={(e) => setSafeZone(e.target.value as SafeZoneType)}
                className="bg-[#121522] border border-[#232738] text-[10px] font-bold text-[#ccff00] px-1.5 py-0.5 rounded focus:outline-none"
              >
                <option value="none">Off</option>
                <option value="youtube">YouTube</option>
                <option value="tiktok">TikTok</option>
                <option value="instagram">Reels</option>
              </select>
            </div>
          </div>

          <div className="flex flex-col items-center">
            {/* Phone Bezel */}
            <div className="w-[280px] h-[498px] bg-black rounded-[36px] p-3 border-4 border-[#232738] shadow-2xl relative overflow-hidden flex flex-col justify-between">
              {/* Phone Camera Notch */}
              <div className="absolute top-2 left-1/2 -translate-x-1/2 w-20 h-4 bg-[#1a1f30] rounded-full z-30" />

              {/* Rendered Short Content Mockup */}
              <div className="w-full h-full rounded-[24px] overflow-hidden bg-black flex flex-col relative">
                {screenMode === 'gaming_split' ? (
                  <>
                    {/* Top Facecam Region */}
                    <div
                      className="w-full overflow-hidden relative bg-[#121522]"
                      style={{
                        height: `${faceHeightPct}%`,
                        opacity: faceOpacity,
                        borderBottom: `${faceBorder}px solid #ccff00`,
                        borderRadius: `${faceRounded}px`
                      }}
                    >
                      {frameUrl && (
                        <div
                          className="w-full h-full"
                          style={{
                            backgroundImage: `url(${frameUrl})`,
                            backgroundPosition: `${gamingConfig.face_x}% ${gamingConfig.face_y}%`,
                            backgroundSize: `${(100 / Math.max(10, gamingConfig.face_w)) * 100}% ${(100 / Math.max(10, gamingConfig.face_h)) * 100}%`,
                            backgroundRepeat: 'no-repeat'
                          }}
                        />
                      )}
                      <div className="absolute top-2 left-2 text-[8px] bg-black/70 text-[#ccff00] px-1 rounded font-bold shadow">
                        Facecam ({faceHeightPct}%)
                      </div>
                    </div>

                    {/* Bottom Gameplay Region */}
                    <div
                      className="w-full overflow-hidden relative bg-[#0a0d14]"
                      style={{ height: `${100 - faceHeightPct}%` }}
                    >
                      {frameUrl && (
                        <div
                          className="w-full h-full"
                          style={{
                            backgroundImage: `url(${frameUrl})`,
                            backgroundPosition: `${gamingConfig.game_x}% ${gamingConfig.game_y}%`,
                            backgroundSize: `${(100 / Math.max(10, gamingConfig.game_w)) * 100}% ${(100 / Math.max(10, gamingConfig.game_h)) * 100}%`,
                            backgroundRepeat: 'no-repeat'
                          }}
                        />
                      )}
                      <div className="absolute top-2 left-2 text-[8px] bg-black/70 text-[#00d2ff] px-1 rounded font-bold shadow">
                        Gameplay ({100 - faceHeightPct}%)
                      </div>
                    </div>
                  </>
                ) : screenMode === 'crop' ? (
                  <div className="w-full h-full relative overflow-hidden bg-black">
                    {frameUrl && (
                      <div
                        className="w-full h-full"
                        style={{
                          backgroundImage: `url(${frameUrl})`,
                          backgroundPosition: `${singleCropConfig.crop_x}% ${singleCropConfig.crop_y}%`,
                          backgroundSize: `${(100 / Math.max(10, singleCropConfig.crop_w)) * 100}% ${(100 / Math.max(10, singleCropConfig.crop_h)) * 100}%`,
                          backgroundRepeat: 'no-repeat'
                        }}
                      />
                    )}
                  </div>
                ) : (
                  <div className="w-full h-full relative overflow-hidden flex items-center justify-center bg-gray-950">
                    {frameUrl && (
                      <img
                        src={frameUrl}
                        alt="Background blur"
                        className="absolute inset-0 w-full h-full object-cover opacity-45 scale-125"
                        style={{ filter: `blur(${Math.round(blurIntensity / 2)}px)` }}
                      />
                    )}
                    {frameUrl && (
                      <img
                        src={frameUrl}
                        alt="Foreground 16:9"
                        className="relative z-10 w-full aspect-video object-contain shadow-2xl"
                      />
                    )}
                  </div>
                )}

                {/* Subtitle Mockup Banner */}
                <div className="absolute bottom-16 left-0 right-0 text-center px-4 pointer-events-none z-20">
                  <span className="inline-block bg-black/80 text-[#ccff00] text-[10px] font-black px-2 py-0.5 rounded shadow-xl uppercase tracking-wider border border-[#ccff00]/40">
                    🔥 VIRAL CLUTCH MOMENT ⚡
                  </span>
                </div>

                {/* Platform Safe-Zone Overlays */}
                {safeZone === 'youtube' && (
                  <div className="absolute inset-0 pointer-events-none z-25 border border-red-500/30">
                    {/* YouTube Right Action Buttons */}
                    <div className="absolute right-2 bottom-20 flex flex-col items-center gap-2 text-white/70">
                      <div className="w-7 h-7 rounded-full bg-black/50 border border-white/20 flex items-center justify-center text-[9px]">👍</div>
                      <div className="w-7 h-7 rounded-full bg-black/50 border border-white/20 flex items-center justify-center text-[9px]">💬</div>
                      <div className="w-7 h-7 rounded-full bg-black/50 border border-white/20 flex items-center justify-center text-[9px]">↗️</div>
                    </div>
                    {/* YouTube Bottom Title/Channel Safe Area */}
                    <div className="absolute bottom-0 left-0 right-12 h-14 bg-red-500/15 border-t border-red-500/40 flex items-center px-3">
                      <span className="text-[8px] text-red-300 font-mono">YT Safe Zone (Avoid text here)</span>
                    </div>
                  </div>
                )}

                {safeZone === 'tiktok' && (
                  <div className="absolute inset-0 pointer-events-none z-25 border border-cyan-500/30">
                    <div className="absolute right-2 bottom-16 flex flex-col items-center gap-2 text-white/70">
                      <div className="w-7 h-7 rounded-full bg-black/50 border border-white/20 flex items-center justify-center text-[9px]">❤️</div>
                      <div className="w-7 h-7 rounded-full bg-black/50 border border-white/20 flex items-center justify-center text-[9px]">💬</div>
                      <div className="w-7 h-7 rounded-full bg-black/50 border border-white/20 flex items-center justify-center text-[9px]">🔖</div>
                    </div>
                    <div className="absolute bottom-0 left-0 right-12 h-16 bg-cyan-500/15 border-t border-cyan-500/40 flex items-center px-3">
                      <span className="text-[8px] text-cyan-300 font-mono">TikTok Safe Zone</span>
                    </div>
                  </div>
                )}

                {safeZone === 'instagram' && (
                  <div className="absolute inset-0 pointer-events-none z-25 border border-pink-500/30">
                    <div className="absolute right-2 bottom-16 flex flex-col items-center gap-2 text-white/70">
                      <div className="w-7 h-7 rounded-full bg-black/50 border border-white/20 flex items-center justify-center text-[9px]">❤️</div>
                      <div className="w-7 h-7 rounded-full bg-black/50 border border-white/20 flex items-center justify-center text-[9px]">💬</div>
                    </div>
                    <div className="absolute bottom-0 left-0 right-10 h-14 bg-pink-500/15 border-t border-pink-500/40 flex items-center px-3">
                      <span className="text-[8px] text-pink-300 font-mono">Reels Safe Zone</span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Save Layout Button */}
            <button
              onClick={() => setActiveTab('studio')}
              className="mt-4 w-[280px] py-3 rounded-xl bg-[#ccff00] hover:bg-[#b8e600] text-black font-extrabold text-xs uppercase tracking-wider transition-all shadow-lg shadow-[#ccff00]/25 flex items-center justify-center gap-2 hover:scale-105 cursor-pointer"
            >
              <Check className="w-4 h-4" />
              <span>Save & Return to Studio</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
