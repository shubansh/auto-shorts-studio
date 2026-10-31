import React, { useState, useEffect } from 'react';
import {
  FileVideo,
  Download,
  Play,
  Film,
  RefreshCw,
  X
} from 'lucide-react';
import type { LibraryItem, ActiveTab } from '../types';

interface LibraryViewProps {
  libraryItems: LibraryItem[];
  onRefreshLibrary: () => Promise<void>;
  setActiveTab: (tab: ActiveTab) => void;
}

export const LibraryView: React.FC<LibraryViewProps> = ({
  libraryItems,
  onRefreshLibrary,
  setActiveTab
}) => {
  const [activeVideoUrl, setActiveVideoUrl] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    onRefreshLibrary();
  }, []);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await onRefreshLibrary();
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="bg-[#121522] border border-[#232738] rounded-2xl p-6 shadow-xl flex items-center justify-between">
        <div>
          <h2 className="text-xl font-black text-white tracking-tight flex items-center gap-2">
            <FileVideo className="w-5 h-5 text-[#ccff00]" />
            <span>Rendered Shorts Library</span>
          </h2>
          <p className="text-xs text-gray-400 mt-1">
            All finished 9:16 vertical MP4s encoded with NVIDIA RTX 3050 NVENC 60fps.
          </p>
        </div>

        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#1b2030] hover:bg-[#252b42] text-xs font-bold text-gray-200 border border-[#2f3750] transition-all"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Grid of Rendered Shorts */}
      {libraryItems.length === 0 ? (
        <div className="bg-[#121522] border border-[#232738] rounded-2xl p-16 text-center space-y-4">
          <Film className="w-12 h-12 mx-auto text-gray-600" />
          <h3 className="text-base font-bold text-white">No Rendered Shorts Yet</h3>
          <p className="text-xs text-gray-400 max-w-md mx-auto">
            Discover highlights or cut a clip in the Studio, then click 'Create Clips' to render your first 9:16 vertical short!
          </p>
          <button
            onClick={() => setActiveTab('studio')}
            className="px-5 py-2.5 rounded-xl bg-[#ccff00] text-black font-extrabold text-xs uppercase tracking-wider hover:bg-[#b8e600] transition-all"
          >
            Go to Studio
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {libraryItems.map((item) => (
            <div
              key={item.filename}
              className="bg-[#121522] border border-[#232738] rounded-2xl overflow-hidden shadow-xl hover:border-[#ccff00]/60 transition-all group flex flex-col justify-between"
            >
              {/* Short Video Thumbnail / Preview Area */}
              <div
                onClick={() => setActiveVideoUrl(item.video_url)}
                className="relative aspect-[9/16] bg-black cursor-pointer overflow-hidden flex items-center justify-center group-hover:opacity-95"
              >
                <video
                  src={item.video_url}
                  className="w-full h-full object-cover pointer-events-none"
                  preload="metadata"
                />
                {/* Play Button Overlay */}
                <div className="absolute inset-0 bg-black/40 group-hover:bg-black/20 flex items-center justify-center transition-all">
                  <div className="w-12 h-12 rounded-full bg-[#ccff00] text-black flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
                    <Play className="w-6 h-6 fill-black translate-x-0.5" />
                  </div>
                </div>

                {/* Top Badges */}
                <div className="absolute top-2 left-2 flex gap-1">
                  <span className="text-[9px] bg-black/70 text-[#ccff00] px-1.5 py-0.5 rounded font-black">
                    9:16
                  </span>
                  <span className="text-[9px] bg-emerald-500/80 text-black px-1.5 py-0.5 rounded font-black">
                    60 FPS
                  </span>
                </div>
              </div>

              {/* Card Footer */}
              <div className="p-4 space-y-3 bg-[#0f111a] border-t border-[#1f2438]">
                <div>
                  <div className="font-bold text-xs text-white truncate" title={item.filename}>
                    {item.filename}
                  </div>
                  <div className="text-[11px] text-gray-400 font-mono mt-0.5">
                    {item.size_mb} MB • Ready for TikTok / Shorts / Reels
                  </div>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => setActiveVideoUrl(item.video_url)}
                    className="flex-1 py-2 px-3 rounded-xl bg-[#1b2030] hover:bg-[#262c42] text-xs font-bold text-white transition-all flex items-center justify-center gap-1.5"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>Watch</span>
                  </button>

                  <a
                    href={item.video_url}
                    download={item.filename}
                    className="p-2 rounded-xl bg-[#ccff00] hover:bg-[#b8e600] text-black font-extrabold transition-all flex items-center justify-center shadow-md shadow-[#ccff00]/10"
                    title="Download MP4"
                  >
                    <Download className="w-4 h-4" />
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Video Modal Player */}
      {activeVideoUrl && (
        <div
          onClick={() => setActiveVideoUrl(null)}
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 animate-fadeIn"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="relative bg-[#121522] border border-[#232738] rounded-2xl overflow-hidden max-w-sm w-full shadow-2xl flex flex-col"
          >
            <div className="p-3 bg-[#0f111a] border-b border-[#1f2438] flex items-center justify-between text-white text-xs font-bold">
              <span>Short Playback</span>
              <button
                onClick={() => setActiveVideoUrl(null)}
                className="p-1 rounded-lg hover:bg-white/10"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="aspect-[9/16] bg-black">
              <video
                src={activeVideoUrl}
                controls
                autoPlay
                className="w-full h-full object-contain"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
