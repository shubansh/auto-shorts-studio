export interface VideoMeta {
  width: number;
  height: number;
  duration: number;
  fps: number;
}

export interface TimelineThumb {
  timestamp: number;
  url: string;
}

export interface ClipMoment {
  id?: string;
  start: number;
  end: number;
  score: number;
  reason: string;
  label?: string;
  tags?: string[];
  selected?: boolean;
}

export interface BoxRect {
  x: number; // Percentage 0 - 100
  y: number; // Percentage 0 - 100
  width: number; // Percentage 0 - 100
  height: number; // Percentage 0 - 100
}

export interface GamingLayoutConfig {
  face_x: number;
  face_y: number;
  face_w: number;
  face_h: number;
  game_x: number;
  game_y: number;
  game_w: number;
  game_h: number;
  face_height_pct?: number;
}

export interface SingleCropConfig {
  crop_x: number;
  crop_y: number;
  crop_w: number;
  crop_h: number;
}

export interface RenderJobResult {
  clip_index: number;
  start: number;
  end: number;
  video_path: string;
  video_url: string;
}

export interface RenderJob {
  status: 'idle' | 'running' | 'complete' | 'error';
  progress: number;
  message: string;
  results?: RenderJobResult[];
}

export interface SessionData {
  video_path: string | null;
  video_url: string | null;
  filename: string | null;
  meta: VideoMeta | null;
  preview_url: string | null;
  timeline_thumbs: TimelineThumb[];
  discovered_clips: ClipMoment[];
  render_job?: RenderJob;
}

export interface LocalSession {
  filename: string;
  size_mb: number;
}

export interface LibraryItem {
  filename: string;
  size_mb: number;
  video_url: string;
}

export interface SystemMetrics {
  timestamp: number;
  cpu: {
    cores: number;
    threads: number;
    util_pct: number;
  };
  ram: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    util_pct: number;
  };
  disk: {
    drive: string;
    total_gb: number;
    used_gb: number;
    free_gb: number;
    util_pct: number;
  };
  gpu: {
    available: boolean;
    name: string;
    util_pct: number;
    vram_used_mb: number;
    vram_total_mb: number;
    temp_c: number | null;
    nvenc_supported: boolean;
    cuda_available: boolean;
    status: 'online' | 'unavailable' | 'error';
    error?: string | null;
  };
}

export type ActiveTab =
  | 'dashboard'
  | 'capture'
  | 'studio'
  | 'layout'
  | 'captions'
  | 'library'
  | 'settings';

export type ScreenMode = 'gaming_split' | 'crop' | 'blur_fit';

export type SubtitleTheme =
  | 'Hormozi Gold (Viral)'
  | 'MrBeast Modern'
  | 'Neon Cyberpunk'
  | 'Mint Clean'
  | 'Clean Minimalist';
