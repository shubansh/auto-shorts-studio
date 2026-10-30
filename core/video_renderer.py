import os
import subprocess
import logging

logger = logging.getLogger(__name__)

class VideoRenderer:
    def __init__(self, target_width=1080, target_height=1920):
        self.target_width = target_width
        self.target_height = target_height

    def render_short(
        self,
        video_path: str,
        clip_start: float,
        clip_end: float,
        crop_info: dict,
        ass_subtitle_path: str,
        output_path: str,
        layout_mode: str = "crop"
    ) -> str:
        """
        Renders a 9:16 Short (1080x1920) with subtitle burn-in.
        layout_mode options:
          - 'crop': Smart face-centered vertical crop
          - 'blur_fit': Original 16:9 in center with blurred 9:16 dynamic background
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        ass_dir = os.path.dirname(os.path.abspath(ass_subtitle_path))
        ass_filename = os.path.basename(ass_subtitle_path)

        abs_video_path = os.path.abspath(video_path)
        abs_output_path = os.path.abspath(output_path)

        # Build filter based on layout mode
        if layout_mode == "blur_fit":
            filter_args = [
                "-filter_complex",
                f"[0:v]scale={self.target_width}:{self.target_height}:force_original_aspect_ratio=increase,crop={self.target_width}:{self.target_height},boxblur=22:5[bg];"
                f"[0:v]scale={self.target_width}:-2:flags=lanczos[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2,ass=filename={ass_filename}[v]",
                "-map", "[v]",
                "-map", "0:a?"
            ]
        elif layout_mode == "gaming_split":
            # Powder.gg gaming layout: Facecam on top, Gameplay on bottom
            facecam = crop_info.get("facecam", {"x": 1300, "y": 50, "w": 580, "h": 460})
            gameplay = crop_info.get("gameplay", {"x": 420, "y": 0, "w": 1080, "h": 1080})
            
            # Retrieve video dimensions to guarantee valid crop bounds
            from core.audio import get_video_info
            try:
                v_meta = get_video_info(abs_video_path)
                in_w, in_h = v_meta["width"], v_meta["height"]
            except Exception:
                in_w, in_h = 1920, 1080

            fx = max(0, min(in_w - 50, int(facecam.get("x", 1300))))
            fy = max(0, min(in_h - 50, int(facecam.get("y", 50))))
            fw = max(50, min(in_w - fx, int(facecam.get("w", 580))))
            fh = max(50, min(in_h - fy, int(facecam.get("h", 460))))

            gx = max(0, min(in_w - 50, int(gameplay.get("x", 420))))
            gy = max(0, min(in_h - 50, int(gameplay.get("y", 0))))
            gw = max(50, min(in_w - gx, int(gameplay.get("w", 1080))))
            gh = max(50, min(in_h - gy, int(gameplay.get("h", 1080))))

            # Make dimensions even
            if fw % 2 != 0: fw -= 1
            if fh % 2 != 0: fh -= 1
            if gw % 2 != 0: gw -= 1
            if gh % 2 != 0: gh -= 1

            top_h = int(crop_info.get("top_height", 760))
            if top_h % 2 != 0: top_h += 1
            bot_h = self.target_height - top_h
            if bot_h % 2 != 0: bot_h -= 1

            filter_args = [
                "-filter_complex",
                f"[0:v]crop={fw}:{fh}:{fx}:{fy},scale={self.target_width}:{top_h}:flags=lanczos[cam];"
                f"[0:v]crop={gw}:{gh}:{gx}:{gy},scale={self.target_width}:{bot_h}:flags=lanczos[game];"
                f"[cam][game]vstack=inputs=2,ass=filename={ass_filename}[v]",
                "-map", "[v]",
                "-map", "0:a?"
            ]
        else:
            # Smart crop mode
            crop_w = crop_info.get("crop_w", 608)
            crop_h = crop_info.get("crop_h", 1080)
            crop_x = crop_info.get("crop_x", 0)
            crop_y = crop_info.get("crop_y", 0)

            filter_str = (
                f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},"
                f"scale={self.target_width}:{self.target_height}:flags=lanczos,"
                f"ass=filename={ass_filename}"
            )
            filter_args = ["-vf", filter_str]

        # 1. Attempt GPU Acceleration with h264_nvenc
        cmd_gpu = [
            "ffmpeg", "-y",
            "-ss", f"{clip_start:.3f}",
            "-to", f"{clip_end:.3f}",
            "-i", abs_video_path,
            *filter_args,
            "-c:v", "h264_nvenc",
            "-preset", "p6",
            "-tune", "hq",
            "-rc", "vbr",
            "-cq", "19",
            "-b:v", "14M",
            "-maxrate", "18M",
            "-bufsize", "28M",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "256k",
            abs_output_path
        ]

        logger.info(f"Rendering short with GPU NVENC (mode={layout_mode}): {' '.join(cmd_gpu)}")
        res = subprocess.run(cmd_gpu, cwd=ass_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if res.returncode == 0 and os.path.exists(abs_output_path) and os.path.getsize(abs_output_path) > 0:
            logger.info(f"Short rendered successfully using GPU NVENC: {output_path}")
            return abs_output_path

        logger.warning(f"GPU render failed or NVENC unavailable. Stderr: {res.stderr}\nFalling back to CPU (libx264)...")

        # 2. CPU Fallback with libx264
        cmd_cpu = [
            "ffmpeg", "-y",
            "-ss", f"{clip_start:.3f}",
            "-to", f"{clip_end:.3f}",
            "-i", abs_video_path,
            *filter_args,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "256k",
            abs_output_path
        ]

        res_cpu = subprocess.run(cmd_cpu, cwd=ass_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res_cpu.returncode != 0:
            raise RuntimeError(f"FFmpeg CPU render failed: {res_cpu.stderr}")

        logger.info(f"Short rendered successfully using CPU: {output_path}")
        return abs_output_path
