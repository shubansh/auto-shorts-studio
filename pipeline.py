import os
import sys
import time
import logging

# Ensure UTF-8 output on Windows for multilingual/Hindi console logging
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from core.audio import extract_audio, get_video_info, download_youtube_video
from core.transcriber import AudioTranscriber
from core.highlight_detector import HighlightDetector
from core.face_tracker import FaceTracker
from core.subtitle_engine import SubtitleEngine
from core.video_renderer import VideoRenderer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage")

class ShortsPipeline:
    def __init__(self, base_dir=None, whisper_model="small", ollama_model="llama3.2:latest"):
        self.base_dir = base_dir or DEFAULT_STORAGE_DIR
        self.uploads_dir = os.path.join(self.base_dir, "uploads")
        self.audio_dir = os.path.join(self.base_dir, "audio")
        self.cache_dir = os.path.join(self.base_dir, "cache")
        self.outputs_dir = os.path.join(self.base_dir, "outputs")

        for d in [self.uploads_dir, self.audio_dir, self.cache_dir, self.outputs_dir]:
            os.makedirs(d, exist_ok=True)

        self.whisper_model_name = whisper_model
        self.ollama_model_name = ollama_model
        
        self.transcriber = None
        self.highlight_detector = HighlightDetector(model_name=self.ollama_model_name)
        self.face_tracker = FaceTracker()
        self.subtitle_engine = SubtitleEngine()
        self.renderer = VideoRenderer()

    def process(
        self,
        video_source: str,
        is_youtube=False,
        num_clips=3,
        min_duration=20,
        max_duration=60,
        subtitle_theme="Hormozi Gold (Viral)",
        enable_emojis=True,
        layout_mode="crop",
        gaming_config=None,
        single_crop_config=None,
        preselected_clips=None,
        scan_start=0.0,
        scan_end=None,
        progress_callback=None
    ) -> list:
        """
        Runs the full end-to-end pipeline.
        progress_callback signature: callback(step_title: str, percent: float, status_msg: str)
        """
        def update_progress(title, pct, msg):
            logger.info(f"[{pct:.0f}%] {title}: {msg}")
            if progress_callback:
                progress_callback(title, pct, msg)

        # Step 1: Input Acquisition
        update_progress("Input Ingestion", 5, "Preparing video file...")
        if is_youtube:
            update_progress("YouTube Download", 10, f"Downloading video from {video_source}...")
            video_path = download_youtube_video(video_source, self.uploads_dir)
        else:
            video_path = video_source

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        video_filename = os.path.splitext(os.path.basename(video_path))[0]
        video_info = get_video_info(video_path)
        logger.info(f"Video Info: {video_info['width']}x{video_info['height']}, {video_info['duration']:.1f}s @ {video_info['fps']}fps")

        # Step 2: Audio Extraction
        update_progress("Audio Extraction", 20, "Extracting 16kHz mono audio stream...")
        audio_path = os.path.join(self.audio_dir, f"{video_filename}.wav")
        if not os.path.exists(audio_path):
            extract_audio(video_path, audio_path)

        # Step 3: Transcription (with Caching)
        update_progress("Speech Recognition", 35, f"Transcribing audio with Faster-Whisper ({self.whisper_model_name}) on GPU...")
        cache_file = os.path.join(self.cache_dir, f"{video_filename}_transcript.json")
        transcript_data = AudioTranscriber.load_cache(cache_file)

        if not transcript_data:
            if self.transcriber is None:
                self.transcriber = AudioTranscriber(model_size=self.whisper_model_name)
            transcript_data = self.transcriber.transcribe(audio_path)
            AudioTranscriber.save_cache(transcript_data, cache_file)
        else:
            logger.info("Loaded transcript from cache.")

        # Step 4: Highlight Detection with Ollama
        if preselected_clips and len(preselected_clips) > 0:
            clips = preselected_clips
            logger.info(f"Using {len(clips)} preselected clips from user interface.")
        else:
            update_progress("AI Clip Discovery", 55, f"Finding top viral moments using Ollama ({self.ollama_model_name})...")
            clips = self.highlight_detector.find_highlights(
                transcript_data,
                num_clips=num_clips,
                min_duration=min_duration,
                max_duration=max_duration,
                scan_start=scan_start,
                scan_end=scan_end
            )

        if not clips:
            raise RuntimeError("Could not find any highlight clips from the transcript.")

        logger.info(f"Discovered {len(clips)} candidate clips: {clips}")

        # Step 5: Process & Render Each Short
        output_results = []
        total_clips = len(clips)
        self.subtitle_engine = SubtitleEngine(theme_name=subtitle_theme, enable_emojis=enable_emojis)

        for idx, clip in enumerate(clips):
            clip_idx = idx + 1
            clip_start = clip["start"]
            clip_end = clip["end"]
            clip_title = clip["title"]
            pct_base = 60 + int((idx / total_clips) * 35)

            # Crop / Layout configuration
            crop_info = {"crop_w": 608, "crop_h": 1080, "crop_x": 0, "crop_y": 0}
            if layout_mode == "gaming_split":
                update_progress(
                    f"Applying Gaming Split {clip_idx}/{total_clips}",
                    pct_base,
                    f"Stacking facecam and gameplay for '{clip_title}'..."
                )
                crop_info = gaming_config or {
                    "facecam": {"x": 1300, "y": 50, "w": 580, "h": 460},
                    "gameplay": {"x": 420, "y": 0, "w": 1080, "h": 1080},
                    "top_height": 760
                }
            elif layout_mode == "crop":
                if single_crop_config and single_crop_config.get("mode") == "custom":
                    crop_w = int(video_info["height"] * 9 / 16)
                    if crop_w % 2 != 0: crop_w += 1
                    crop_x = int(single_crop_config.get("crop_x", (video_info["width"] - crop_w) // 2))
                    crop_x = max(0, min(video_info["width"] - crop_w, crop_x))
                    if crop_x % 2 != 0: crop_x += 1
                    update_progress(
                        f"Applying Custom 9:16 Crop {clip_idx}/{total_clips}",
                        pct_base,
                        f"Cropping at X={crop_x} for '{clip_title}'..."
                    )
                    crop_info = {
                        "crop_w": crop_w,
                        "crop_h": video_info["height"],
                        "crop_x": crop_x,
                        "crop_y": 0
                    }
                else:
                    update_progress(
                        f"Face Tracking Clip {clip_idx}/{total_clips}",
                        pct_base,
                        f"Analyzing speaker face position for '{clip_title}'..."
                    )
                    crop_info = self.face_tracker.calculate_crop_window(
                        video_path,
                        clip_start,
                        clip_end,
                        video_info["width"],
                        video_info["height"]
                    )
            else:
                update_progress(
                    f"Preparing Layout {clip_idx}/{total_clips}",
                    pct_base,
                    f"Applying '{layout_mode}' layout for '{clip_title}'..."
                )

            # Generate ASS Subtitles
            update_progress(
                f"Generating Subtitles {clip_idx}/{total_clips}",
                pct_base + 3,
                f"Building word-level karaoke captions..."
            )
            ass_path = os.path.join(self.cache_dir, f"{video_filename}_clip_{clip_idx}.ass")
            self.subtitle_engine.generate_ass(
                transcript_data.get("segments", []),
                clip_start,
                clip_end,
                ass_path,
                video_w=1080,
                video_h=1920
            )

            # Render Short Video with NVENC
            update_progress(
                f"Rendering Short {clip_idx}/{total_clips}",
                pct_base + 6,
                f"Exporting 9:16 Short ({layout_mode}) with GPU NVENC..."
            )
            short_filename = f"Short_{clip_idx}_{int(clip_start)}s_{int(clip_end)}s.mp4"
            short_output_path = os.path.join(self.outputs_dir, short_filename)

            rendered_path = self.renderer.render_short(
                video_path,
                clip_start,
                clip_end,
                crop_info,
                ass_path,
                short_output_path,
                layout_mode=layout_mode
            )

            output_results.append({
                "clip_number": clip_idx,
                "title": clip_title,
                "hook_score": clip.get("hook_score", 8.5),
                "virality_score": clip.get("virality_score", int(clip.get("hook_score", 8.5) * 10)),
                "tags": clip.get("tags", ["🔥 Highlight", "⚡ Clip it"]),
                "reason": clip.get("reason", "Engaging viral moment"),
                "start": clip_start,
                "end": clip_end,
                "duration": round(clip_end - clip_start, 1),
                "video_path": rendered_path,
                "source_video_path": video_path,
                "video_filename": video_filename,
                "filename": short_filename
            })

        update_progress("Complete", 100, f"Successfully generated {len(output_results)} Shorts!")
        return output_results
