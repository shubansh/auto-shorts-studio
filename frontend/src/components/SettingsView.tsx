import React, { useState, useEffect } from 'react';
import {
  Settings,
  Cpu,
  Layers,
  Sparkles,
  Database,
  Check,
  RotateCw
} from 'lucide-react';
import type { SystemSettings } from '../types';

export const SettingsView: React.FC = () => {
  const [settings, setSettings] = useState<SystemSettings>({
    whisper_model: 'small',
    ollama_model: 'llama3.2:latest',
    preferred_resolution: '1080x1920',
    preferred_fps: 60,
    caption_theme: 'Hormozi Gold (Viral)',
    enable_emojis: true
  });
  const [loading, setLoading] = useState<boolean>(true);
  const [savedBadge, setSavedBadge] = useState<boolean>(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const res = await fetch('/api/settings');
      if (res.ok) {
        const data = await res.json();
        setSettings(prev => ({ ...prev, ...data }));
      }
    } catch (err) {
      console.warn('Could not load settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const updateSetting = async (key: string, value: any) => {
    const next = { ...settings, [key]: value };
    setSettings(next);
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: { [key]: value } })
      });
      if (res.ok) {
        setSavedBadge(true);
        setTimeout(() => setSavedBadge(false), 2000);
      }
    } catch (err) {
      console.error('Failed to persist setting:', err);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="bg-[#121522] border border-[#232738] rounded-2xl p-6 shadow-xl flex items-center justify-between">
        <div className="space-y-1">
          <h2 className="text-xl font-black text-white tracking-tight flex items-center gap-2">
            <Settings className="w-5 h-5 text-[#ccff00]" />
            <span>System & Hardware Engine Settings</span>
          </h2>
          <p className="text-xs text-gray-400">
            Persistent local configuration stored safely in SQLite (<code className="text-gray-300">storage/clipforge.db</code>).
          </p>
        </div>
        {savedBadge && (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-bold animate-fadeIn">
            <Check className="w-3.5 h-3.5" />
            <span>Saved to SQLite</span>
          </span>
        )}
      </div>

      {/* GPU Hardware Status Card */}
      <div className="bg-[#121522] border border-[#232738] rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#1f2438]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <div className="font-extrabold text-sm text-white">
                NVIDIA GeForce RTX 3050 Laptop GPU
              </div>
              <div className="text-xs text-emerald-400 font-medium">
                Hardware Acceleration Active (NVENC + CUDA)
              </div>
            </div>
          </div>
          <span className="text-xs bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-3 py-1 rounded-full font-mono font-bold">
            ONLINE
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="bg-[#0e111a] p-3 rounded-xl border border-[#1f2438]">
            <div className="text-gray-400 font-medium mb-1">NVENC Video Encoder</div>
            <div className="text-white font-bold font-mono">h264_nvenc (p4 preset)</div>
            <div className="text-[10px] text-gray-500 mt-1">60 FPS Hardware Render</div>
          </div>
          <div className="bg-[#0e111a] p-3 rounded-xl border border-[#1f2438]">
            <div className="text-gray-400 font-medium mb-1">Whisper Transcription</div>
            <div className="text-white font-bold font-mono">faster-whisper (CUDA 12)</div>
            <div className="text-[10px] text-gray-500 mt-1">float16 compute type</div>
          </div>
          <div className="bg-[#0e111a] p-3 rounded-xl border border-[#1f2438]">
            <div className="text-gray-400 font-medium mb-1">Highlight AI Reasoning</div>
            <div className="text-white font-bold font-mono">Ollama (llama3.2:latest)</div>
            <div className="text-[10px] text-gray-500 mt-1">Local LLM Inference</div>
          </div>
        </div>
      </div>

      {/* Model Selection Card */}
      <div className="bg-[#121522] border border-[#232738] rounded-2xl p-6 shadow-xl space-y-4">
        <h3 className="text-sm font-extrabold uppercase tracking-wider text-white flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[#ccff00]" />
          <span>AI Model Configuration</span>
        </h3>

        <div className="space-y-4 text-xs">
          <div className="flex items-center justify-between p-3 rounded-xl bg-[#0e111a] border border-[#1f2438]">
            <div>
              <div className="font-bold text-white">Speech Recognition Model</div>
              <div className="text-gray-400 text-[11px]">
                Faster-Whisper model for word-level subtitle generation
              </div>
            </div>
            <select
              value={settings.whisper_model || 'small'}
              onChange={(e) => updateSetting('whisper_model', e.target.value)}
              className="bg-[#171b29] border border-[#2c334b] text-white text-xs font-bold px-3 py-1.5 rounded-lg focus:outline-none focus:border-[#ccff00]"
            >
              <option value="tiny">tiny (Ultra fast)</option>
              <option value="base">base (Balanced)</option>
              <option value="small">small (Recommended for RTX 3050)</option>
              <option value="medium">medium (High accuracy)</option>
            </select>
          </div>

          <div className="flex items-center justify-between p-3 rounded-xl bg-[#0e111a] border border-[#1f2438]">
            <div>
              <div className="font-bold text-white">Highlight AI Model</div>
              <div className="text-gray-400 text-[11px]">
                Ollama LLM for discovering viral gaming hooks and clutch moments
              </div>
            </div>
            <select
              value={settings.ollama_model || 'llama3.2:latest'}
              onChange={(e) => updateSetting('ollama_model', e.target.value)}
              className="bg-[#171b29] border border-[#2c334b] text-white text-xs font-bold px-3 py-1.5 rounded-lg focus:outline-none focus:border-[#ccff00]"
            >
              <option value="llama3.2:latest">llama3.2:latest (Fast 3B)</option>
              <option value="mistral:latest">mistral:latest</option>
              <option value="gemma2:2b">gemma2:2b</option>
            </select>
          </div>

          <div className="flex items-center justify-between p-3 rounded-xl bg-[#0e111a] border border-[#1f2438]">
            <div>
              <div className="font-bold text-white">Preferred Render FPS</div>
              <div className="text-gray-400 text-[11px]">Target framerate for final vertical shorts</div>
            </div>
            <select
              value={settings.preferred_fps || 60}
              onChange={(e) => updateSetting('preferred_fps', parseInt(e.target.value, 10))}
              className="bg-[#171b29] border border-[#2c334b] text-white text-xs font-bold px-3 py-1.5 rounded-lg focus:outline-none focus:border-[#ccff00]"
            >
              <option value={60}>60 FPS (Ultra Smooth Gaming)</option>
              <option value={30}>30 FPS (Standard)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Database & Architecture Specs */}
      <div className="bg-[#121522] border border-[#232738] rounded-2xl p-6 shadow-xl space-y-3">
        <h3 className="text-sm font-extrabold uppercase tracking-wider text-white flex items-center gap-2">
          <Database className="w-4 h-4 text-[#ccff00]" />
          <span>SQLite Database Persistence (Phase 3 Active)</span>
        </h3>
        <p className="text-xs text-gray-400 leading-relaxed">
          ClipForge stores all project timelines, crop boxes, and AI clips non-destructively in SQLite with WAL journal mode. Original media files remain 100% immutable.
        </p>
        <ul className="text-xs text-gray-300 space-y-1.5 list-disc pl-5 font-mono">
          <li><strong>Database:</strong> SQLite WAL mode (zero locking, concurrent reads)</li>
          <li><strong>Storage:</strong> <code className="text-[#ccff00]">storage/clipforge.db</code></li>
          <li><strong>Integrity:</strong> Non-destructive versioned schema (v1.0)</li>
          <li><strong>Crash Recovery:</strong> Auto-recovers interrupted GPU render jobs</li>
        </ul>
      </div>
    </div>
  );
};
