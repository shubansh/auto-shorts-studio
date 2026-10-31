import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  SplitSquareVertical,
  Check,
  Move,
  Clock,
  Eye
} from 'lucide-react';
import type {
  GamingLayoutConfig,
  SingleCropConfig,
  ScreenMode,
  SessionData,
  ActiveTab
} from '../types';

interface LayoutEditorProps {
  session: SessionData | null;
  screenMode: ScreenMode;
  setScreenMode: (mode: ScreenMode) => void;
  gamingConfig: GamingLayoutConfig;
  setGamingConfig: React.Dispatch<React.SetStateAction<GamingLayoutConfig>>;
  singleCropConfig: SingleCropConfig;
  setSingleCropConfig: React.Dispatch<React.SetStateAction<SingleCropConfig>>;
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
  onFetchFrameAtTime,
  setActiveTab
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  // Active frame image URL (can be updated to different timestamps)
  const [frameUrl, setFrameUrl] = useState<string>(session?.preview_url || '');
  const [frameTimestamp, setFrameTimestamp] = useState<number>(45);

  // Mouse drag state for interactive canvas bounding boxes
  const [activeDrag, setActiveDrag] = useState<{
    target: 'face' | 'game' | 'single';
    action: 'move' | 'resize';
    startX: number;
    startY: number;
    initialX: number;
    initialY: number;
    initialW: number;
    initialH: number;
  } | null>(null);

  // When session preview_url changes, update frameUrl
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
      console.error('Failed to load frame', err);
    }
  };

  // Streamer Presets
  const applyPreset = (preset: string) => {
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
    } else if (preset === 'top-left') {
      setGamingConfig((prev) => ({
        ...prev,
        face_x: 2,
        face_y: 5,
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

  // Drag-and-drop mouse event handlers
  const handleMouseDown = (
    e: React.MouseEvent,
    target: 'face' | 'game' | 'single',
    action: 'move' | 'resize'
  ) => {
    e.stopPropagation();
    e.preventDefault();
    if (!containerRef.current) return;

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
      action,
      startX: e.clientX,
      startY: e.clientY,
      initialX: initX,
      initialY: initY,
      initialW: initW,
      initialH: initH
    });
  };

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!activeDrag || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const deltaXPercent = ((e.clientX - activeDrag.startX) / rect.width) * 100;
      const deltaYPercent = ((e.clientY - activeDrag.startY) / rect.height) * 100;

      if (activeDrag.action === 'move') {
        const newX = Math.max(0, Math.min(100 - activeDrag.initialW, activeDrag.initialX + deltaXPercent));
        const newY = Math.max(0, Math.min(100 - activeDrag.initialH, activeDrag.initialY + deltaYPercent));

        if (activeDrag.target === 'face') {
          setGamingConfig((prev) => ({ ...prev, face_x: Math.round(newX), face_y: Math.round(newY) }));
        } else if (activeDrag.target === 'game') {
          setGamingConfig((prev) => ({ ...prev, game_x: Math.round(newX), game_y: Math.round(newY) }));
        } else {
          setSingleCropConfig((prev) => ({ ...prev, crop_x: Math.round(newX), crop_y: Math.round(newY) }));
        }
      } else if (activeDrag.action === 'resize') {
        const newW = Math.max(10, Math.min(100 - activeDrag.initialX, activeDrag.initialW + deltaXPercent));
        const newH = Math.max(10, Math.min(100 - activeDrag.initialY, activeDrag.initialH + deltaYPercent));

        if (activeDrag.target === 'face') {
          setGamingConfig((prev) => ({ ...prev, face_w: Math.round(newW), face_h: Math.round(newH) }));
        } else if (activeDrag.target === 'game') {
          setGamingConfig((prev) => ({ ...prev, game_w: Math.round(newW), game_h: Math.round(newH) }));
        } else {
          setSingleCropConfig((prev) => ({ ...prev, crop_w: Math.round(newW), crop_h: Math.round(newH) }));
        }
      }
    },
    [activeDrag, setGamingConfig, setSingleCropConfig]
  );

  const handleMouseUp = useCallback(() => {
    setActiveDrag(null);
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

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 animate-fadeIn">
      {/* Top Controls: Mode & Presets */}
      <div className="bg-[#121522] border border-[#232738] rounded-2xl p-6 shadow-xl space-y-6">
        <div>
          <h2 className="text-xl font-black text-white tracking-tight flex items-center gap-2">
            <SplitSquareVertical className="w-5 h-5 text-[#ccff00]" />
            <span>Visual Layout & Facecam Alignment</span>
          </h2>
          <p className="text-xs text-gray-400 mt-1">
            Directly drag the green & cyan boxes on your video frame to select exact facecam and gameplay regions.
          </p>
        </div>

        {/* Screen Mode Tabs */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <button
            type="button"
            onClick={() => setScreenMode('gaming_split')}
            className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
              screenMode === 'gaming_split'
                ? 'bg-[#1a1f30] border-[#ccff00] ring-1 ring-[#ccff00]/30 shadow-lg'
                : 'bg-[#0d0f17] border-[#202538] hover:border-gray-600'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-extrabold text-xs text-white flex items-center gap-1.5">
                🎮 Gaming Split
              </span>
              {screenMode === 'gaming_split' && (
                <span className="text-[10px] bg-[#ccff00] text-black font-bold px-1.5 py-0.5 rounded">
                  Active
                </span>
              )}
            </div>
            <p className="text-[11px] text-gray-400">
              Facecam on Top 40% + Main Gameplay on Bottom 60%
            </p>
          </button>

          <button
            type="button"
            onClick={() => setScreenMode('crop')}
            className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
              screenMode === 'crop'
                ? 'bg-[#1a1f30] border-[#00d2ff] ring-1 ring-[#00d2ff]/30 shadow-lg'
                : 'bg-[#0d0f17] border-[#202538] hover:border-gray-600'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-extrabold text-xs text-white flex items-center gap-1.5">
                📱 Single Screen 9:16
              </span>
              {screenMode === 'crop' && (
                <span className="text-[10px] bg-[#00d2ff] text-black font-bold px-1.5 py-0.5 rounded">
                  Active
                </span>
              )}
            </div>
            <p className="text-[11px] text-gray-400">
              Full 9:16 vertical crop (No facecam, only gameplay)
            </p>
          </button>

          <button
            type="button"
            onClick={() => setScreenMode('blur_fit')}
            className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
              screenMode === 'blur_fit'
                ? 'bg-[#1a1f30] border-purple-500 ring-1 ring-purple-500/30 shadow-lg'
                : 'bg-[#0d0f17] border-[#202538] hover:border-gray-600'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-extrabold text-xs text-white flex items-center gap-1.5">
                🎬 Cinematic Blur Fit
              </span>
              {screenMode === 'blur_fit' && (
                <span className="text-[10px] bg-purple-500 text-white font-bold px-1.5 py-0.5 rounded">
                  Active
                </span>
              )}
            </div>
            <p className="text-[11px] text-gray-400">
              Preserve original 16:9 gameplay with blurred ambient background
            </p>
          </button>
        </div>

        {/* Presets & Scene Time Selector */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-[#1f2333]">
          {/* Streamer Presets */}
          {screenMode === 'gaming_split' && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-gray-300">Facecam Presets:</span>
              <div className="flex flex-wrap gap-1.5">
                {[
                  { id: 'bottom-right', label: 'Bottom-Right' },
                  { id: 'top-right', label: 'Top-Right' },
                  { id: 'bottom-left', label: 'Bottom-Left' },
                  { id: 'top-left', label: 'Top-Left' },
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

          {/* Scene Timestamp Scrubber */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-gray-300 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-[#ccff00]" />
              <span>Preview Frame at:</span>
            </span>
            <div className="flex items-center gap-1.5">
              {[0, 45, 120, 240].map((sec) => (
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
      </div>

      {/* Dual Visual Canvas: Left 16:9 Interactive Frame | Right 9:16 Mockup */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: 16:9 Frame with Interactive Drag Boxes (8 cols) */}
        <div className="lg:col-span-8 space-y-3">
          <div className="flex items-center justify-between text-xs font-bold text-gray-300 px-1">
            <span className="flex items-center gap-1.5">
              <Move className="w-4 h-4 text-[#ccff00]" />
              <span>1. Click & Drag Bounding Boxes on 16:9 Video Frame</span>
            </span>
            <span className="text-[11px] text-gray-400">
              Drag box to move • Drag corner handles to resize
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
                Loading video frame...
              </div>
            )}

            {/* GAMING SPLIT: GREEN FACECAM BOX */}
            {screenMode === 'gaming_split' && (
              <div
                onMouseDown={(e) => handleMouseDown(e, 'face', 'move')}
                className="absolute border-2 border-[#ccff00] bg-[#ccff00]/15 cursor-move rounded-md group"
                style={{
                  left: `${gamingConfig.face_x}%`,
                  top: `${gamingConfig.face_y}%`,
                  width: `${gamingConfig.face_w}%`,
                  height: `${gamingConfig.face_h}%`
                }}
              >
                {/* Header Badge */}
                <div className="absolute -top-6 left-0 bg-[#ccff00] text-black text-[10px] font-black px-1.5 py-0.5 rounded shadow">
                  🟢 Facecam (Top 40%)
                </div>

                {/* Resize Handle at Bottom-Right */}
                <div
                  onMouseDown={(e) => handleMouseDown(e, 'face', 'resize')}
                  className="absolute -bottom-1.5 -right-1.5 w-4 h-4 bg-[#ccff00] rounded-full border border-black cursor-se-resize shadow"
                />
              </div>
            )}

            {/* GAMING SPLIT: CYAN GAMEPLAY BOX */}
            {screenMode === 'gaming_split' && (
              <div
                onMouseDown={(e) => handleMouseDown(e, 'game', 'move')}
                className="absolute border-2 border-[#00d2ff] bg-[#00d2ff]/15 cursor-move rounded-md group"
                style={{
                  left: `${gamingConfig.game_x}%`,
                  top: `${gamingConfig.game_y}%`,
                  width: `${gamingConfig.game_w}%`,
                  height: `${gamingConfig.game_h}%`
                }}
              >
                {/* Header Badge */}
                <div className="absolute -top-6 left-0 bg-[#00d2ff] text-black text-[10px] font-black px-1.5 py-0.5 rounded shadow">
                  🔵 Main Gameplay (Bottom 60%)
                </div>

                {/* Resize Handle at Bottom-Right */}
                <div
                  onMouseDown={(e) => handleMouseDown(e, 'game', 'resize')}
                  className="absolute -bottom-1.5 -right-1.5 w-4 h-4 bg-[#00d2ff] rounded-full border border-black cursor-se-resize shadow"
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
                  onMouseDown={(e) => handleMouseDown(e, 'single', 'resize')}
                  className="absolute -bottom-1.5 -right-1.5 w-4 h-4 bg-[#00d2ff] rounded-full border border-black cursor-se-resize shadow"
                />
              </div>
            )}
          </div>

          {/* Numeric Position Sliders (Fine-Tuning) */}
          <div className="bg-[#121522] border border-[#232738] rounded-xl p-4 grid grid-cols-2 gap-4 text-xs">
            {screenMode === 'gaming_split' ? (
              <>
                <div className="space-y-2">
                  <div className="font-bold text-[#ccff00] flex items-center justify-between">
                    <span>Facecam Position & Size</span>
                    <span className="font-mono text-gray-400">
                      {gamingConfig.face_w}% x {gamingConfig.face_h}%
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-400 text-[11px]">
                    <span className="w-6">X:</span>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={gamingConfig.face_x}
                      onChange={(e) =>
                        setGamingConfig((prev) => ({ ...prev, face_x: Number(e.target.value) }))
                      }
                      className="flex-1 accent-[#ccff00]"
                    />
                    <span className="font-mono w-8">{gamingConfig.face_x}%</span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-400 text-[11px]">
                    <span className="w-6">Y:</span>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={gamingConfig.face_y}
                      onChange={(e) =>
                        setGamingConfig((prev) => ({ ...prev, face_y: Number(e.target.value) }))
                      }
                      className="flex-1 accent-[#ccff00]"
                    />
                    <span className="font-mono w-8">{gamingConfig.face_y}%</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="font-bold text-[#00d2ff] flex items-center justify-between">
                    <span>Gameplay Position & Size</span>
                    <span className="font-mono text-gray-400">
                      {gamingConfig.game_w}% x {gamingConfig.game_h}%
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-400 text-[11px]">
                    <span className="w-6">X:</span>
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
                    <span className="font-mono w-8">{gamingConfig.game_x}%</span>
                  </div>
                  <div className="flex items-center gap-2 text-gray-400 text-[11px]">
                    <span className="w-6">Y:</span>
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
                    <span className="font-mono w-8">{gamingConfig.game_y}%</span>
                  </div>
                </div>
              </>
            ) : (
              <div className="col-span-2 space-y-2">
                <div className="font-bold text-[#00d2ff] flex items-center justify-between">
                  <span>9:16 Portrait Crop Area</span>
                  <span className="font-mono text-gray-400">
                    X: {singleCropConfig.crop_x}%, Width: {singleCropConfig.crop_w}%
                  </span>
                </div>
                <div className="flex items-center gap-2 text-gray-400 text-[11px]">
                  <span className="w-12">Crop X:</span>
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
                  <span className="font-mono w-8">{singleCropConfig.crop_x}%</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right: 9:16 Phone Mockup Preview (4 cols) */}
        <div className="lg:col-span-4 space-y-3">
          <div className="text-xs font-bold text-gray-300 px-1 flex items-center gap-1.5">
            <Eye className="w-4 h-4 text-[#ccff00]" />
            <span>2. Exact 9:16 Vertical Short Mockup</span>
          </div>

          <div className="flex flex-col items-center">
            {/* Phone Bezel */}
            <div className="w-[280px] h-[498px] bg-black rounded-[36px] p-3 border-4 border-[#232738] shadow-2xl relative overflow-hidden flex flex-col justify-between">
              {/* Phone Camera Notch */}
              <div className="absolute top-2 left-1/2 -translate-x-1/2 w-20 h-4 bg-[#1a1f30] rounded-full z-30"></div>

              {/* Rendered Short Content Mockup */}
              <div className="w-full h-full rounded-[24px] overflow-hidden bg-black flex flex-col relative">
                {screenMode === 'gaming_split' ? (
                  <>
                    {/* Top 40% Facecam Region */}
                    <div className="h-[40%] w-full overflow-hidden relative bg-[#121522] border-b-2 border-[#ccff00]">
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
                      <div className="absolute top-2 left-2 text-[8px] bg-black/60 text-[#ccff00] px-1 rounded font-bold">
                        Facecam (40%)
                      </div>
                    </div>

                    {/* Bottom 60% Gameplay Region */}
                    <div className="h-[60%] w-full overflow-hidden relative bg-[#0a0d14]">
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
                      <div className="absolute top-2 left-2 text-[8px] bg-black/60 text-[#00d2ff] px-1 rounded font-bold">
                        Gameplay (60%)
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
                  /* Blur Fit Mockup */
                  <div className="w-full h-full relative overflow-hidden flex items-center justify-center bg-gray-950">
                    {frameUrl && (
                      <img
                        src={frameUrl}
                        alt="Background blur"
                        className="absolute inset-0 w-full h-full object-cover blur-md opacity-40 scale-125"
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

                {/* Subtitle Mockup Overlay */}
                <div className="absolute bottom-12 left-0 right-0 text-center px-4 pointer-events-none z-20">
                  <span className="inline-block bg-black/70 text-[#ccff00] text-[11px] font-black px-2 py-1 rounded shadow-lg uppercase tracking-wide border border-[#ccff00]/30">
                    🔥 HEADSHOT KILL 💀
                  </span>
                </div>
              </div>
            </div>

            {/* Save Layout Button */}
            <button
              onClick={() => setActiveTab('studio')}
              className="mt-4 w-[280px] py-3 rounded-xl bg-[#ccff00] hover:bg-[#b8e600] text-black font-extrabold text-xs uppercase tracking-wider transition-all shadow-lg shadow-[#ccff00]/20 flex items-center justify-center gap-2 hover:scale-105"
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
