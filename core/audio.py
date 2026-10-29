import os
import subprocess
import json
import logging
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
    Downloads YouTube video at best quality up to 1080p using yt-dlp.
    """
    os.makedirs(output_dir, exist_ok=True)
    out_tmpl = os.path.join(output_dir, "%(id)s.%(ext)s")
    
    ydl_opts = {
        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
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
