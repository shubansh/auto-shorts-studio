import React from 'react';
import {
  ChevronLeft,
  Zap,
  Sliders,
  RotateCw
} from 'lucide-react';
import type { SessionData, ActiveTab } from '../types';

interface HeaderProps {
  session: SessionData | null;
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  onTriggerRender: () => void;
  isRendering: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  session,
  activeTab,
  setActiveTab,
  onTriggerRender,
  isRendering
}) => {
  return (
    <header className="h-14 bg-[#0e1017] border-b border-[#1f2333] px-6 flex items-center justify-between shrink-0">
      {/* Left: Project title & Back link */}
      <div className="flex items-center gap-3">
        {activeTab !== 'dashboard' && (
          <button
            onClick={() => setActiveTab('dashboard')}
            className="p-1.5 rounded-lg bg-[#141724] hover:bg-[#1f2333] text-gray-300 transition-colors"
            title="Back to Dashboard"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        )}
        <div>
          <h1 className="text-sm font-bold text-white flex items-center gap-2">
            {session?.filename || 'Untitled Game Session'}
            {session?.meta && (
              <span className="text-[10px] bg-[#1e2333] text-gray-400 px-2 py-0.5 rounded font-mono font-normal">
                {Math.floor(session.meta.duration / 60)}m {Math.floor(session.meta.duration % 60)}s
              </span>
            )}
          </h1>
        </div>
      </div>

      {/* Center: Quick Switcher / Status */}
      <div className="flex items-center gap-2 bg-[#141724] p-1 rounded-lg border border-[#232738]">
        <button
          onClick={() => setActiveTab('studio')}
          className={`px-3 py-1 text-xs font-semibold rounded-md transition-all ${
            activeTab === 'studio'
              ? 'bg-[#23273a] text-white shadow-sm'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Timeline Studio
        </button>
        <button
          onClick={() => setActiveTab('layout')}
          className={`px-3 py-1 text-xs font-semibold rounded-md flex items-center gap-1.5 transition-all ${
            activeTab === 'layout'
              ? 'bg-[#23273a] text-white shadow-sm'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          <Sliders className="w-3.5 h-3.5 text-[#00d2ff]" />
          Edit Layout
        </button>
        <button
          onClick={() => setActiveTab('captions')}
          className={`px-3 py-1 text-xs font-semibold rounded-md transition-all ${
            activeTab === 'captions'
              ? 'bg-[#23273a] text-white shadow-sm'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Subtitles & Style
        </button>
      </div>

      {/* Right: Render / Export CTA */}
      <div className="flex items-center gap-3">
        <button
          disabled={isRendering || !session?.video_path}
          onClick={onTriggerRender}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-extrabold tracking-wide uppercase transition-all shadow-md ${
            isRendering
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 cursor-wait'
              : !session?.video_path
              ? 'bg-gray-800 text-gray-500 cursor-not-allowed'
              : 'bg-[#ccff00] text-black hover:bg-[#b8e600] shadow-[#ccff00]/25 hover:scale-[1.02] active:scale-[0.98]'
          }`}
        >
          {isRendering ? (
            <>
              <RotateCw className="w-3.5 h-3.5 animate-spin text-amber-300" />
              <span>Rendering 60fps...</span>
            </>
          ) : (
            <>
              <Zap className="w-3.5 h-3.5 fill-black" />
              <span>Render Shorts</span>
            </>
          )}
        </button>
      </div>
    </header>
  );
};
