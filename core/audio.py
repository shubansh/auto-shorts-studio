import os
import subprocess
import json
import logging
import struct
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional
import yt_dlp

logger = logging.getLogger(__name__)

def extract_audio(video_path: str, output_wav_path: str) -> str:
    """
    Extracts 16kHz mono WAV audio from video using FFmpeg.
    Optimized for Whisper speech-to-text.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_wav_path)), exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        output_wav_path
    ]
    logger.info(f"Extracting audio: {' '.join(cmd)}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed: {result.stderr}")
    return output_wav_path

def extract_preview_frame(video_path: str, output_jpg_path: str, timestamp: float = 5.0) -> str:
    """Extracts a single high-quality JPG preview frame from video for visual selection."""
    os.makedirs(os.path.dirname(os.path.abspath(output_jpg_path)), exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{timestamp:.2f}",
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        output_jpg_path
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_jpg_path if os.path.exists(output_jpg_path) else ""

def get_nearest_keyframe(video_path: str, timestamp: float) -> float:
    """
    Finds presentation timestamp of the nearest keyframe at or before the requested timestamp.
    Uses fast interval seek in ffprobe.
    """
    start_seek = max(0.0, timestamp - 10.0)
    end_seek = timestamp + 10.0
    cmd = [
        "ffprobe", "-v", "error",
        "-read_intervals", f"{start_seek}%+{end_seek}",
        "-select_streams", "v:0",
        "-show_entries", "frame=key_frame,pkt_pts_time",
        "-of", "json",
        video_path
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            keyframes = []
            for f in data.get("frames", []):
                if f.get("key_frame") == 1 and "pkt_pts_time" in f:
                    keyframes.append(float(f["pkt_pts_time"]))
            if keyframes:
                prior = [k for k in keyframes if k <= timestamp]
                if prior:
                    return max(prior)
                return min(keyframes, key=lambda k: abs(k - timestamp))
    except Exception as e:
        logger.warning(f"Keyframe detection ffprobe error: {e}")
    return timestamp

def trim_video(
    video_path: str,
    output_path: str,
    start_time: float,
    end_time: float,
    mode: str = "fast"
) -> Dict[str, Any]:
    """
    Trims video with choice of MODE A (Fast Keyframe Trim) or MODE B (Accurate Frame Trim).
    Returns execution details including actual start/end PTS and trim mode.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    actual_start = start_time
    actual_end = end_time

    if mode == "fast":
        # Mode A: Fast Keyframe Trim with FFmpeg stream copy
        nearest_kf = get_nearest_keyframe(video_path, start_time)
        actual_start = nearest_kf

        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{actual_start:.3f}",
            "-to", f"{end_time:.3f}",
            "-i", video_path,
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            output_path
        ]
        logger.info(f"Fast Keyframe Trim: {' '.join(cmd)}")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            logger.warning(f"Fast trim failed: {res.stderr}. Falling back to accurate frame trim.")
            mode = "accurate"

    if mode == "accurate":
        # Mode B: Accurate Frame Trim using NVENC with CPU fallback
        cmd_nvenc = [
            "ffmpeg", "-y",
            "-ss", f"{start_time:.3f}",
            "-to", f"{end_time:.3f}",
            "-i", video_path,
            "-c:v", "h264_nvenc",
            "-preset", "p4",
            "-cq", "19",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path
        ]
        logger.info(f"Accurate Frame Trim (NVENC): {' '.join(cmd_nvenc)}")
        res_nvenc = subprocess.run(cmd_nvenc, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res_nvenc.returncode != 0 or not os.path.exists(output_path):
            logger.warning(f"NVENC accurate trim failed, falling back to libx264 CPU: {res_nvenc.stderr}")
            cmd_cpu = [
                "ffmpeg", "-y",
                "-ss", f"{start_time:.3f}",
                "-to", f"{end_time:.3f}",
                "-i", video_path,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                output_path
            ]
            res_cpu = subprocess.run(cmd_cpu, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res_cpu.returncode != 0:
                raise RuntimeError(f"FFmpeg accurate trim failed: {res_cpu.stderr}")
        actual_start = start_time
        actual_end = end_time

    out_file = output_path if os.path.exists(output_path) else video_path
    return {
        "output_path": out_file,
        "mode": mode,
        "requested_start": start_time,
        "actual_start": actual_start,
        "requested_end": end_time,
        "actual_end": actual_end,
        "duration": max(0.1, actual_end - actual_start)
    }

def generate_audio_waveform(video_path: str, cache_dir: str, num_samples: int = 500) -> Dict[str, Any]:
    """
    Generates normalized audio peak waveform data across the video duration.
    Streams 4000Hz mono PCM via FFmpeg in small chunks without loading full audio into RAM.
    Supports mono, stereo, and videos without audio.
    Caches results with mtime invalidation.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    os.makedirs(cache_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    cache_path = os.path.join(cache_dir, f"{base_name}_waveform_{num_samples}.json")

    # Check cache validity
    source_mtime = os.path.getmtime(video_path)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached.get("source_mtime") == source_mtime and len(cached.get("peaks", [])) == num_samples:
                return cached
        except Exception:
            pass

    # Check if file has audio stream using ffprobe
    has_audio = False
    duration = 60.0
    try:
        probe_cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams", "-show_format",
            video_path
        ]
        res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            meta = json.loads(res.stdout)
            duration = float(meta.get("format", {}).get("duration", 60.0))
            for s in meta.get("streams", []):
                if s.get("codec_type") == "audio":
                    has_audio = True
                    break
    except Exception as e:
        logger.warning(f"ffprobe check failed during waveform generation: {e}")

    if not has_audio:
        result = {
            "source_mtime": source_mtime,
            "audio_available": False,
            "duration": duration,
            "sample_count": num_samples,
            "peaks": [0.0] * min(100, num_samples)
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f)
        return result

    # Stream 4kHz 16-bit mono PCM from FFmpeg in 4KB chunks
    cmd = [
        "ffmpeg", "-v", "error",
        "-i", video_path,
        "-vn",
        "-ac", "1",
        "-ar", "4000",
        "-f", "s16le",
        "pipe:1"
    ]

    peaks = []
    chunk_size = 4096  # bytes
    max_val = 32768.0

    proc = None
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        all_bucket_maxes = []
        current_chunk_samples = []

        while True:
            raw = proc.stdout.read(chunk_size)
            if not raw:
                break
            num_shorts = len(raw) // 2
            if num_shorts > 0:
                shorts = struct.unpack(f"<{num_shorts}h", raw[:num_shorts*2])
                current_chunk_samples.extend(shorts)
                if len(current_chunk_samples) >= 8000:
                    local_max = max(abs(s) for s in current_chunk_samples)
                    all_bucket_maxes.append(local_max / max_val)
                    current_chunk_samples = []

        if current_chunk_samples:
            all_bucket_maxes.append(max(abs(s) for s in current_chunk_samples) / max_val)
        proc.wait()

        if not all_bucket_maxes:
            all_bucket_maxes = [0.0]

        total_pts = len(all_bucket_maxes)
        step = total_pts / float(num_samples)
        for i in range(num_samples):
            idx = min(total_pts - 1, int(i * step))
            val = all_bucket_maxes[idx]
            peaks.append(round(min(1.0, max(0.02, val)), 3))

    except Exception as e:
        logger.error(f"Error streaming audio waveform: {e}")
        peaks = [0.05] * num_samples
    finally:
        if proc:
            if proc.stdout:
                try:
                    proc.stdout.close()
                except Exception:
                    pass
            try:
                proc.wait(timeout=1)
            except Exception:
                proc.kill()

    result = {
        "source_mtime": source_mtime,
        "audio_available": True,
        "duration": duration,
        "sample_count": len(peaks),
        "peaks": peaks
    }

    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f)
    except Exception as ex:
        logger.warning(f"Could not write waveform cache: {ex}")

    return result

def extract_timeline_thumbnails(video_path: str, output_dir: str, duration: float, count: int = 8) -> List[Dict[str, Any]]:
    """
    Extracts evenly spaced thumbnails across the video in batch.
    Uses caching and multi-threaded batch execution for maximum speed.
    """
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    thumbnails = []
    
    if duration <= 0:
        duration = 60.0

    step = duration / (count + 1)
    missing_points = []
    for i in range(1, count + 1):
        ts = round(step * i, 2)
        out_thumb = os.path.join(output_dir, f"{base_name}_thumb_{i}.jpg")
        if os.path.exists(out_thumb) and os.path.getsize(out_thumb) > 0:
            thumbnails.append({"timestamp": ts, "path": out_thumb})
        else:
            missing_points.append((i, ts, out_thumb))

    if missing_points:
        def _extract_one(item):
            _, ts, out_thumb = item
            cmd = [
                "ffmpeg", "-y",
                "-ss", f"{ts:.2f}",
                "-i", video_path,
                "-vframes", "1",
                "-vf", "scale=160:-1",
                "-q:v", "5",
                out_thumb
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(out_thumb):
                return {"timestamp": ts, "path": out_thumb}
            return None

        with ThreadPoolExecutor(max_workers=min(4, len(missing_points))) as pool:
            results = pool.map(_extract_one, missing_points)
            for r in results:
                if r:
                    thumbnails.append(r)

    thumbnails.sort(key=lambda t: t["timestamp"])
    return thumbnails

def get_video_info(video_path: str) -> dict:
    """
    Retrieves video resolution, duration, and frame rate via ffprobe.
    """
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFprobe failed: {result.stderr}")
    
    data = json.loads(result.stdout)
    video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if not video_stream:
        raise ValueError("No video stream found in file.")
    
    width = int(video_stream.get("width", 1920))
    height = int(video_stream.get("height", 1080))
    duration = float(data.get("format", {}).get("duration", video_stream.get("duration", 0.0)))
    
    # Calculate FPS
    r_fps = video_stream.get("r_frame_rate", "30/1")
    if "/" in r_fps:
        num, den = r_fps.split("/")
        fps = float(num) / float(den) if float(den) != 0 else 30.0
    else:
        fps = float(r_fps)

    return {
        "width": width,
        "height": height,
        "duration": duration,
        "fps": fps
    }

def download_youtube_video(url: str, output_dir: str) -> str:
    """
    Downloads YouTube video at best high-definition quality (1080p / 720p).
    Merges best video stream and best audio stream into crystal-clear MP4.
    """
    os.makedirs(output_dir, exist_ok=True)
    out_tmpl = os.path.join(output_dir, "%(id)s.%(ext)s")
    
    ydl_opts = {
        'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
        'outtmpl': out_tmpl,
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        # In case merge changed extension to .mp4
        base, _ = os.path.splitext(filename)
        final_mp4 = f"{base}.mp4"
        if os.path.exists(final_mp4):
            return final_mp4
        return filename
