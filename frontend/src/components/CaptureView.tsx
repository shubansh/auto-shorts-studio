import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  Radio,
  FileVideo,
  CheckCircle,
  AlertCircle,
  RotateCw,
  FolderOpen,
  Play
} from 'lucide-react';
import type { LocalSession, ActiveTab } from '../types';

interface CaptureViewProps {
  localSessions: LocalSession[];
  onSelectLocalSession: (filename: string) => void;
  onImportYouTube: (url: string) => Promise<void>;
  onUploadFile: (file: File) => Promise<void>;
  setActiveTab: (tab: ActiveTab) => void;
}

export const CaptureView: React.FC<CaptureViewProps> = ({
  localSessions,
  onSelectLocalSession,
  onImportYouTube,
  onUploadFile,
  setActiveTab
}) => {
  const [ytUrl, setYtUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleYtSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ytUrl.trim()) return;
    setLoading(true);
    setStatusMsg('Downloading video via yt-dlp with NVENC compatible streams...');
    setErrorMsg('');
    try {
      await onImportYouTube(ytUrl);
      setStatusMsg('Download finished! Opening Studio...');
      setTimeout(() => setActiveTab('studio'), 500);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to download YouTube video.');
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setStatusMsg(`Uploading ${file.name}...`);
    setErrorMsg('');
    try {
      await onUploadFile(file);
      setStatusMsg('Uploaded! Opening Studio...');
      setTimeout(() => setActiveTab('studio'), 500);
    } catch (err: any) {
      setErrorMsg(err.message || 'Upload failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    setLoading(true);
    setStatusMsg(`Uploading ${file.name}...`);
    setErrorMsg('');
    try {
      await onUploadFile(file);
      setStatusMsg('Uploaded! Opening Studio...');
      setTimeout(() => setActiveTab('studio'), 500);
    } catch (err: any) {
      setErrorMsg(err.message || 'Upload failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6 animate-fadeIn">
      {/* Powder Style Ingest Modal Card */}
      <div className="bg-[#121522] border border-[#232738] rounded-2xl p-8 shadow-2xl relative overflow-hidden">
        {/* Header */}
        <div className="text-center space-y-2 mb-8">
          <h2 className="text-2xl font-black text-white tracking-tight">
            Import Gaming Video
          </h2>
          <p className="text-xs text-gray-400">
            Paste a YouTube URL or drop your local MP4 recording to start clipping
          </p>
        </div>

        {/* Top Twitch & YouTube Quick Buttons */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <button
            type="button"
            onClick={() => {
              const sample = 'https://www.youtube.com/watch?v=S1656XwwsYg';
              setYtUrl(sample);
            }}
            className="flex items-center justify-center gap-2.5 py-3 px-4 rounded-xl bg-gradient-to-r from-[#9146ff]/30 to-[#9146ff]/10 hover:from-[#9146ff]/40 hover:to-[#9146ff]/20 border border-[#9146ff]/40 text-purple-200 font-bold text-xs transition-all cursor-pointer"
          >
            <Radio className="w-4 h-4 text-[#9146ff]" />
            <span>Connect Twitch VOD</span>
          </button>

          <button
            type="button"
            onClick={() => {
              const sample = 'https://www.youtube.com/watch?v=S1656XwwsYg';
              setYtUrl(sample);
            }}
            className="flex items-center justify-center gap-2.5 py-3 px-4 rounded-xl bg-gradient-to-r from-red-600/30 to-red-600/10 hover:from-red-600/40 hover:to-red-600/20 border border-red-500/40 text-red-200 font-bold text-xs transition-all cursor-pointer"
          >
            <Play className="w-4 h-4 fill-red-500 text-red-500" />
            <span>Connect YouTube</span>
          </button>
        </div>

        {/* Drag & Drop Zone */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed border-[#2d3248] hover:border-[#ccff00] rounded-2xl p-10 flex flex-col items-center justify-center gap-3 cursor-pointer transition-all bg-[#0d0f17]/50 hover:bg-[#141824]/50 group"
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept="video/mp4,video/mkv,video/mov,video/webm"
            className="hidden"
          />
          <div className="w-16 h-16 rounded-2xl bg-[#1a1f30] flex items-center justify-center text-gray-400 group-hover:text-[#ccff00] group-hover:scale-110 transition-all">
            <UploadCloud className="w-8 h-8" />
          </div>
          <div className="text-center space-y-1">
            <p className="text-xs font-semibold text-gray-200 group-hover:text-white">
              Drag or click to browse your MP4 file
            </p>
            <p className="text-[11px] text-gray-500">
              We'll quickly create exciting clips from your best gaming moments
            </p>
          </div>
        </div>

        {/* Divider */}
        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-[#232738]"></div>
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-[#121522] px-3 text-gray-500 font-bold">or</span>
          </div>
        </div>

        {/* YouTube Link Input */}
        <form onSubmit={handleYtSubmit} className="space-y-3">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Play className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 fill-red-500 text-red-500" />
              <input
                type="url"
                value={ytUrl}
                onChange={(e) => setYtUrl(e.target.value)}
                placeholder="https://www.youtube.com/watch?v=..."
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#0b0d14] border border-[#232738] text-xs text-white placeholder-gray-500 focus:outline-none focus:border-[#ccff00]"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !ytUrl.trim()}
              className="px-5 py-2.5 rounded-xl bg-[#ccff00] text-black font-extrabold text-xs uppercase tracking-wider hover:bg-[#b8e600] disabled:bg-gray-800 disabled:text-gray-500 transition-all shadow-md flex items-center gap-2"
            >
              {loading ? (
                <>
                  <RotateCw className="w-4 h-4 animate-spin text-black" />
                  <span>Downloading...</span>
                </>
              ) : (
                <span>Import Video</span>
              )}
            </button>
          </div>
        </form>

        {/* Status Messages */}
        {statusMsg && (
          <div className="mt-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
            <CheckCircle className="w-4 h-4 shrink-0" />
            <span>{statusMsg}</span>
          </div>
        )}
        {errorMsg && (
          <div className="mt-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}
      </div>

      {/* Select From Local Disk Section */}
      {localSessions.length > 0 && (
        <div className="bg-[#121522] border border-[#232738] rounded-2xl p-6 space-y-3">
          <h3 className="text-xs font-bold text-gray-300 uppercase tracking-wider flex items-center gap-2">
            <FolderOpen className="w-4 h-4 text-[#ccff00]" />
            <span>Or Select from Uploaded Videos</span>
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {localSessions.map((s) => (
              <button
                key={s.filename}
                type="button"
                onClick={() => {
                  onSelectLocalSession(s.filename);
                  setActiveTab('studio');
                }}
                className="flex items-center justify-between p-3 rounded-xl bg-[#0d0f17] border border-[#232738] hover:border-[#ccff00] text-left transition-all group"
              >
                <div className="flex items-center gap-3 truncate">
                  <FileVideo className="w-5 h-5 text-gray-400 group-hover:text-[#ccff00] shrink-0" />
                  <div className="truncate">
                    <div className="text-xs font-bold text-gray-200 group-hover:text-white truncate">
                      {s.filename}
                    </div>
                    <div className="text-[10px] text-gray-500 font-mono">
                      {s.size_mb} MB
                    </div>
                  </div>
                </div>
                <span className="text-[10px] bg-[#1a1f30] group-hover:bg-[#ccff00] text-gray-300 group-hover:text-black font-bold px-2 py-1 rounded transition-colors shrink-0">
                  Select
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
