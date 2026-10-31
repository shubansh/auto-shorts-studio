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
  face_opacity?: number; // 0.0 - 1.0 (default: 1.0)
  face_border?: number; // border width px (default: 0)
  face_rounded?: number; // corner radius px (default: 0)
  blur_intensity?: number; // background blur (default: 20)
  safe_zone?: SafeZoneType;
}

export type SafeZoneType = 'none' | 'youtube' | 'tiktok' | 'instagram';

export interface SceneKeyframe {
  id: string;
  timestamp: number;
  layout_mode: ScreenMode;
  gaming_config: GamingLayoutConfig;
  single_crop_config: SingleCropConfig;
  transition?: 'linear' | 'stepped';
}

export interface WaveformData {
  source_mtime?: number;
  audio_available: boolean;
  duration: number;
  sample_count: number;
  peaks: number[];
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
  active_project_id?: string | null;
  video_path: string | null;
  video_url: string | null;
  filename: string | null;
  meta: VideoMeta | null;
  preview_url: string | null;
  timeline_thumbs: TimelineThumb[];
  discovered_clips: ClipMoment[];
  render_job?: RenderJob;
}

export interface ProjectStateTimeline {
  in_point: number;
  out_point: number;
  pre_roll_cut: number;
  zoom: number;
}

export interface ProjectStateSourceMedia {
  filename: string;
  duration: number;
  width: number;
  height: number;
  fps: number;
}

export interface ProjectStateCaptions {
  theme: SubtitleTheme;
  enable_emojis: boolean;
  corrections?: Record<string, string>;
}

export interface ProjectStateRenderSettings {
  resolution: string;
  fps: number;
  encoder: string;
}

export interface ProjectState {
  version: string;
  source_media: ProjectStateSourceMedia;
  timeline: ProjectStateTimeline;
  layout: {
    mode: ScreenMode;
    gaming_config: GamingLayoutConfig;
    single_crop_config: SingleCropConfig;
  };
  captions: ProjectStateCaptions;
  render_settings: ProjectStateRenderSettings;
  scene_keyframes?: SceneKeyframe[];
}

export interface MediaAsset {
  id: string;
  project_id: string;
  original_path: string;
  filename: string;
  duration: number;
  width: number;
  height: number;
  fps: number;
  codec: string;
  audio_available: number;
  proxy_path?: string | null;
  thumbnail_path?: string | null;
  created_at: string;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  project_state_json: string;
  project_state: ProjectState;
  media_filename?: string;
  media_duration?: number;
  media_width?: number;
  media_height?: number;
  clips_count?: number;
  rendered_count?: number;
  created_at: string;
  updated_at: string;
  media_asset?: MediaAsset | null;
  clips?: ClipMoment[];
}

export interface SystemSettings {
  whisper_model?: string;
  ollama_model?: string;
  preferred_resolution?: string;
  preferred_fps?: number;
  caption_theme?: string;
  enable_emojis?: boolean;
  layout_preset?: string;
  hardware_preferences?: {
    use_nvenc: boolean;
    fallback_cpu: boolean;
    compute_type: string;
  };
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
