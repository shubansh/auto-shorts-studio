import React from 'react';
import {
  LayoutDashboard,
  Radio,
  Scissors,
  SplitSquareVertical,
  Subtitles,
  FileVideo,
  Settings,
  Cpu,
  Film,
  Zap,
  AlertTriangle
} from 'lucide-react';
import type { ActiveTab, SessionData, SystemMetrics } from '../types';

interface SidebarProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  session: SessionData | null;
  metrics?: SystemMetrics | null;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  session,
  metrics
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'capture', label: 'Capture & Ingest', icon: Radio },
    { id: 'studio', label: 'Studio & Clips', icon: Scissors },
    { id: 'layout', label: 'Layout & Crop', icon: SplitSquareVertical },
    { id: 'captions', label: 'Captions & Styling', icon: Subtitles },
    { id: 'library', label: 'Clips Library', icon: FileVideo },
    { id: 'settings', label: 'Settings & GPU', icon: Settings }
  ] as const;

  const isGpuAvailable = metrics?.gpu?.available ?? true;
  const gpuName = metrics?.gpu?.name || 'RTX 3050 NVENC';

  return (
    <aside className="w-64 bg-[#0e1017] border-r border-[#1f2333] flex flex-col justify-between shrink-0 select-none">
      {/* Brand Header */}
      <div>
        <div className="p-5 flex items-center gap-3 border-b border-[#1b1e2c]">
          <div className="w-9 h-9 rounded-lg bg-[#ccff00] text-black font-black flex items-center justify-center text-xl shadow-lg shadow-[#ccff00]/20">
            P
          </div>
          <div>
            <div className="font-extrabold tracking-wider text-white text-base flex items-center gap-1.5">
              CLIPFORGE <span className="text-[#ccff00] text-xs font-semibold px-1.5 py-0.5 rounded bg-[#ccff00]/10">AI</span>
            </div>
            <div className="text-[11px] text-gray-400 font-medium tracking-tight">
              Local Shorts Studio
            </div>
          </div>
        </div>

        {/* Navigation List */}
        <div className="p-3">
          <div className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider px-3 mb-2">
            Main Product Flow
          </div>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id as ActiveTab)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-[#1b1f2e] text-[#ccff00] font-semibold border-l-3 border-[#ccff00]'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-[#141724]'
                  }`}
                >
                  <Icon
                    className={`w-4 h-4 ${
                      isActive ? 'text-[#ccff00]' : 'text-gray-400'
                    }`}
                  />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Hardware & Active Session Info */}
      <div className="p-3 border-t border-[#1b1e2c] space-y-2">
        {/* Hardware Status Box */}
        <div className="bg-[#141722] border border-[#232738] rounded-xl p-2.5">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1.5 truncate">
              {isGpuAvailable ? (
                <>
                  <span className="relative flex h-2 w-2 shrink-0">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  <span className="text-[11px] font-bold text-gray-200 truncate" title={gpuName}>
                    {gpuName}
                  </span>
                </>
              ) : (
                <>
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                  <span className="text-[11px] font-bold text-amber-300">CPU Mode</span>
                </>
              )}
            </div>
            <span className="text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-1 rounded font-mono shrink-0">
              {isGpuAvailable ? '60 FPS' : 'CPU'}
            </span>
          </div>
          <div className="text-[10px] text-gray-400 flex items-center justify-between">
            <span className="flex items-center gap-1">
              <Cpu className="w-3 h-3 text-[#ccff00]" />
              <span>CUDA 12 Local</span>
            </span>
            {metrics?.gpu?.vram_used_mb !== undefined && (
              <span className="font-mono text-purple-300 text-[9px]">
                {metrics.gpu.vram_used_mb}MB
              </span>
            )}
          </div>
        </div>

        {/* Current Active Video Session */}
        {session?.filename && (
          <div className="bg-[#141722] border border-[#232738] rounded-xl p-2.5">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-gray-500 mb-1 flex items-center gap-1">
              <Film className="w-3 h-3 text-[#00d2ff]" /> Active Project
            </div>
            <div className="text-[11px] font-medium text-white truncate" title={session.filename}>
              {session.filename}
            </div>
            {session.meta && (
              <div className="text-[10px] text-gray-400 font-mono mt-0.5">
                {session.meta.width}x{session.meta.height} • {Math.round(session.meta.duration)}s
              </div>
            )}
          </div>
        )}
      </div>
    </aside>
  );
};
