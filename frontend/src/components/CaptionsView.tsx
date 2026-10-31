import React from 'react';
import {
  Subtitles,
  Sparkles,
  Check
} from 'lucide-react';
import type { SubtitleTheme, ActiveTab } from '../types';

interface CaptionsViewProps {
  currentTheme: SubtitleTheme;
  setTheme: (theme: SubtitleTheme) => void;
  enableEmojis: boolean;
  setEnableEmojis: (enabled: boolean) => void;
  setActiveTab: (tab: ActiveTab) => void;
}

export const CaptionsView: React.FC<CaptionsViewProps> = ({
  currentTheme,
  setTheme,
  enableEmojis,
  setEnableEmojis,
  setActiveTab
}) => {
  const themes: {
    name: SubtitleTheme;
    description: string;
    previewText: string;
    bgClass: string;
    textClass: string;
  }[] = [
    {
      name: 'Hormozi Gold (Viral)',
      description: 'Bold yellow pop with thick black outline. Maximizes TikTok/Shorts watch time.',
      previewText: 'THIS CLUTCH WAS INSANE 🔥',
      bgClass: 'bg-black/90 border-[#ccff00]',
      textClass: 'text-[#ffe600] font-black drop-shadow-[0_2px_4px_rgba(0,0,0,1)]'
    },
    {
      name: 'MrBeast Modern',
      description: 'Ultra-bold animated styling with vivid high-saturation colors and drop shadow.',
      previewText: 'CAN WE HIT THIS SHOT?! 🎯',
      bgClass: 'bg-[#0f172a] border-cyan-400',
      textClass: 'text-cyan-300 font-black drop-shadow-[0_0_12px_rgba(34,211,238,0.8)]'
    },
    {
      name: 'Neon Cyberpunk',
      description: 'Futuristic gamer look with electric cyan text and hot magenta glow outline.',
      previewText: 'HEADSHOT MULTIKILL 💀',
      bgClass: 'bg-black border-fuchsia-500',
      textClass: 'text-[#00ffff] font-extrabold drop-shadow-[0_0_15px_#ff007f]'
    },
    {
      name: 'Mint Clean',
      description: 'Crisp pastel emerald green on dark frosted glass pill.',
      previewText: 'VICTORY ROYALE 👑',
      bgClass: 'bg-[#064e3b]/80 border-emerald-400',
      textClass: 'text-emerald-300 font-extrabold'
    },
    {
      name: 'Clean Minimalist',
      description: 'Understated crisp white subtitles for storytelling and commentary.',
      previewText: 'Watch what happens next...',
      bgClass: 'bg-black/60 border-gray-600',
      textClass: 'text-white font-bold'
    }
  ];

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="bg-[#121522] border border-[#232738] rounded-2xl p-6 shadow-xl space-y-2">
        <h2 className="text-xl font-black text-white tracking-tight flex items-center gap-2">
          <Subtitles className="w-5 h-5 text-[#ccff00]" />
          <span>Viral Subtitle Themes & Word Animations</span>
        </h2>
        <p className="text-xs text-gray-400">
          Subtitles are rendered directly by NVIDIA NVENC using word-level Faster-Whisper timestamps for 100% sync.
        </p>
      </div>

      {/* Auto-Emojis Card */}
      <div className="bg-[#121522] border border-[#232738] rounded-2xl p-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#ccff00]/10 flex items-center justify-center text-[#ccff00]">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="font-extrabold text-sm text-white flex items-center gap-2">
              <span>Auto-Emojis Insertion</span>
              <span className="text-[10px] bg-[#ccff00]/20 text-[#ccff00] px-2 py-0.5 rounded-full font-bold">
                Viral Recommended
              </span>
            </div>
            <div className="text-xs text-gray-400 mt-0.5">
              Automatically detect hype words and attach emojis (🔥, 💀, 👑, 😂, 🎯, ⚡)
            </div>
          </div>
        </div>

        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={enableEmojis}
            onChange={(e) => setEnableEmojis(e.target.checked)}
            className="sr-only peer"
          />
          <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#ccff00]"></div>
        </label>
      </div>

      {/* Theme Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {themes.map((t) => {
          const isSelected = currentTheme === t.name;
          return (
            <div
              key={t.name}
              onClick={() => setTheme(t.name)}
              className={`p-5 rounded-2xl border transition-all cursor-pointer space-y-4 group ${
                isSelected
                  ? 'bg-[#181d2e] border-[#ccff00] ring-1 ring-[#ccff00]/40 shadow-xl'
                  : 'bg-[#121522] border-[#232738] hover:border-gray-500'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-extrabold text-sm text-white group-hover:text-[#ccff00] transition-colors">
                  {t.name}
                </span>
                {isSelected && (
                  <span className="w-5 h-5 rounded-full bg-[#ccff00] text-black flex items-center justify-center text-xs font-black">
                    <Check className="w-3.5 h-3.5 stroke-[3]" />
                  </span>
                )}
              </div>

              <p className="text-xs text-gray-400 leading-relaxed">
                {t.description}
              </p>

              {/* Live Preview Box */}
              <div className={`p-4 rounded-xl border flex items-center justify-center ${t.bgClass}`}>
                <span className={`text-base tracking-wide uppercase text-center ${t.textClass}`}>
                  {t.previewText}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Return Button */}
      <div className="flex justify-end pt-2">
        <button
          onClick={() => setActiveTab('studio')}
          className="px-6 py-3 rounded-xl bg-[#ccff00] hover:bg-[#b8e600] text-black font-extrabold text-xs uppercase tracking-wider transition-all shadow-lg shadow-[#ccff00]/20 flex items-center gap-2 hover:scale-105"
        >
          <Check className="w-4 h-4" />
          <span>Apply Theme & Return to Studio</span>
        </button>
      </div>
    </div>
  );
};
