import React from 'react';
import {
  UploadCloud,
  Film,
  Zap,
  Cpu,
  HardDrive,
  Database,
  Sparkles,
  ChevronRight,
  Play,
  RotateCw,
  AlertTriangle
} from 'lucide-react';
import type { SessionData, LocalSession, ActiveTab, SystemMetrics } from '../types';

interface DashboardViewProps {
  session: SessionData | null;
  localSessions: LocalSession[];
  metrics: SystemMetrics | null;
  metricsLoading: boolean;
  onSelectLocalSession: (filename: string) => void;
  setActiveTab: (tab: ActiveTab) => void;
  onOpenStudio: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  session,
  localSessions,
  metrics,
  metricsLoading,
  onSelectLocalSession,
  setActiveTab,
  onOpenStudio
}) => {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-fadeIn">
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-[#171a29] via-[#141724] to-[#0e1017] border border-[#232738] p-8 shadow-xl">
        <div className="relative z-10 max-w-2xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#ccff00]/10 border border-[#ccff00]/30 text-[#ccff00] text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Automated Gaming Shorts Engine • CapCut Style Editing</span>
          </div>
          <h2 className="text-3xl font-black text-white tracking-tight">
            Create Viral 9:16 Shorts <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#ccff00] to-[#00d2ff]">
              100% Free & Local with RTX 3050 NVENC
            </span>
          </h2>
          <p className="text-sm text-gray-400 leading-relaxed">
            Automatic Facecam & Gameplay visual alignment, Faster-Whisper GPU transcription, Ollama highlight detection, and CapCut-style lossless pre-roll trimming.
          </p>
          <div className="flex items-center gap-4 pt-2">
            <button
              onClick={() => setActiveTab('capture')}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#ccff00] text-black font-extrabold text-xs uppercase tracking-wider hover:bg-[#b8e600] transition-transform hover:scale-105 shadow-lg shadow-[#ccff00]/20"
            >
              <UploadCloud className="w-4 h-4" />
              <span>Import New Gameplay</span>
            </button>
            {session?.video_path && (
              <button
                onClick={onOpenStudio}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#1f2438] text-white font-bold text-xs hover:bg-[#282f48] border border-[#303854] transition-all"
              >
                <Play className="w-4 h-4 text-[#ccff00] fill-[#ccff00]" />
                <span>Continue Studio Session</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 4 REAL SYSTEM TELEMETRY CARDS */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* GPU Telemetry Card */}
        <div className="bg-[#121520] border border-[#202538] rounded-xl p-4 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 shrink-0">
            <Zap className="w-6 h-6" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[11px] text-gray-400 font-medium truncate">
              {metrics?.gpu?.available ? metrics.gpu.name : 'GPU Status'}
            </div>
            {metricsLoading && !metrics ? (
              <div className="h-6 w-24 bg-gray-800 animate-pulse rounded my-1"></div>
            ) : metrics?.gpu?.available ? (
              <div className="text-lg font-black text-white flex items-center gap-2">
                <span>{metrics.gpu.util_pct}% Util</span>
                {metrics.gpu.temp_c !== null && (
                  <span className="text-xs text-purple-300 font-mono font-normal">
                    {metrics.gpu.temp_c}°C
                  </span>
                )}
              </div>
            ) : (
              <div className="text-sm font-bold text-amber-400 flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>CPU Fallback</span>
              </div>
            )}
            <div className="text-[10px] text-purple-300 font-mono truncate">
              {metrics?.gpu?.available
                ? `VRAM: ${metrics.gpu.vram_used_mb} / ${metrics.gpu.vram_total_mb} MB`
                : 'NVENC Offline'}
            </div>
          </div>
        </div>

        {/* CPU Telemetry Card */}
        <div className="bg-[#121520] border border-[#202538] rounded-xl p-4 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-[#ccff00]/10 border border-[#ccff00]/20 flex items-center justify-center text-[#ccff00] shrink-0">
            <Cpu className="w-6 h-6" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[11px] text-gray-400 font-medium">
              CPU ({metrics?.cpu?.cores || 4}C / {metrics?.cpu?.threads || 8}T)
            </div>
            {metricsLoading && !metrics ? (
              <div className="h-6 w-20 bg-gray-800 animate-pulse rounded my-1"></div>
            ) : (
              <div className="text-lg font-black text-white">
                {metrics?.cpu?.util_pct ?? 0}% Util
              </div>
            )}
            <div className="text-[10px] text-emerald-400">
              Multi-Thread Processing
            </div>
          </div>
        </div>

        {/* Host RAM Telemetry Card */}
        <div className="bg-[#121520] border border-[#202538] rounded-xl p-4 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 shrink-0">
            <Database className="w-6 h-6" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[11px] text-gray-400 font-medium">System RAM</div>
            {metricsLoading && !metrics ? (
              <div className="h-6 w-28 bg-gray-800 animate-pulse rounded my-1"></div>
            ) : (
              <div className="text-lg font-black text-white font-mono">
                {metrics?.ram ? `${metrics.ram.used_gb} / ${metrics.ram.total_gb} GB` : '16 GB'}
              </div>
            )}
            <div className="text-[10px] text-cyan-400 font-mono">
              {metrics?.ram ? `${metrics.ram.free_gb} GB Free (${metrics.ram.util_pct}%)` : 'Checking memory...'}
            </div>
          </div>
        </div>

        {/* Local Disk Space Card */}
        <div className="bg-[#121520] border border-[#202538] rounded-xl p-4 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 shrink-0">
            <HardDrive className="w-6 h-6" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[11px] text-gray-400 font-medium">
              Disk ({metrics?.disk?.drive || 'C:'})
            </div>
            {metricsLoading && !metrics ? (
              <div className="h-6 w-24 bg-gray-800 animate-pulse rounded my-1"></div>
            ) : (
              <div className="text-lg font-black text-white font-mono">
                {metrics?.disk ? `${metrics.disk.free_gb} GB Free` : 'Checking disk...'}
              </div>
            )}
            <div className="text-[10px] text-amber-400 font-mono">
              {metrics?.disk ? `${metrics.disk.total_gb} GB Total (${metrics.disk.util_pct}% Used)` : ''}
            </div>
          </div>
        </div>
      </div>

      {/* Available Local Projects Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Film className="w-4 h-4 text-[#ccff00]" />
            <span>Local Video Files ({localSessions.length})</span>
          </h3>
          <button
            onClick={() => setActiveTab('capture')}
            className="text-xs text-[#ccff00] hover:underline flex items-center gap-1"
          >
            <span>Import more</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {localSessions.map((item) => {
            const isCurrent = session?.filename === item.filename;
            return (
              <div
                key={item.filename}
                className={`bg-[#121522] border rounded-xl p-4 transition-all hover:border-[#384160] group ${
                  isCurrent
                    ? 'border-[#ccff00] ring-1 ring-[#ccff00]/40'
                    : 'border-[#202538]'
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div className="font-semibold text-xs text-gray-200 truncate group-hover:text-white" title={item.filename}>
                    {item.filename}
                  </div>
                  {isCurrent && (
                    <span className="shrink-0 text-[10px] bg-[#ccff00]/20 text-[#ccff00] px-2 py-0.5 rounded-full font-bold">
                      Active
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-gray-400 mb-4 font-mono">
                  {item.size_mb} MB
                </div>
                <button
                  onClick={() => {
                    onSelectLocalSession(item.filename);
                    setActiveTab('studio');
                  }}
                  className={`w-full py-2 px-3 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
                    isCurrent
                      ? 'bg-[#ccff00] text-black hover:bg-[#b8e600]'
                      : 'bg-[#1b2030] text-gray-200 hover:bg-[#252b42] hover:text-white'
                  }`}
                >
                  <Play className="w-3 h-3 fill-current" />
                  <span>{isCurrent ? 'Open Studio' : 'Switch Project'}</span>
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
