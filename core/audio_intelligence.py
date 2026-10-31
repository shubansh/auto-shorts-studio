import os
import subprocess
import json
import logging
import struct
import math
import numpy as np
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

def analyze_audio_signals(
    video_or_audio_path: str,
    cache_dir: str,
    chunk_duration_sec: float = 0.5,
    silence_thresh_db: float = -38.0
) -> Dict[str, Any]:
    """
    Performs multi-signal audio intelligence analysis on a video/audio file:
      - RMS Energy & Short-term Loudness curve
      - Silence & Dead Air Detection
      - Reaction Detection (Screaming, Shouting, Laughter)
      - Sudden Audio Spikes (Gunshots, Explosions, Impact cues)
    Uses efficient chunked PCM streaming to avoid loading large files into RAM.
    Results are cached with source file modification time invalidation.
    """
    if not os.path.exists(video_or_audio_path):
        raise FileNotFoundError(f"Source media not found: {video_or_audio_path}")

    os.makedirs(cache_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(video_or_audio_path))[0]
    cache_path = os.path.join(cache_dir, f"{base_name}_audio_signals.json")
    source_mtime = os.path.getmtime(video_or_audio_path)

    # Check cache
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached.get("source_mtime") == source_mtime:
                logger.info(f"Loaded audio intelligence from cache for {base_name}")
                if "silence_intervals" not in cached and "silence_segments" in cached:
                    cached["silence_intervals"] = [[s["start"], s["end"]] for s in cached["silence_segments"]]
                if "mean_rms_db" not in cached and "mean_rms" in cached:
                    cached["mean_rms_db"] = round(20 * math.log10(max(1e-5, cached["mean_rms"])), 1)
                return cached
        except Exception as e:
            logger.warning(f"Failed to read audio signal cache: {e}")

    # Check if stream has audio and get duration
    has_audio = False
    duration = 60.0
    try:
        probe_cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams", "-show_format",
            video_or_audio_path
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
        logger.warning(f"Could not probe audio stream: {e}")

    if not has_audio:
        logger.info(f"No audio stream detected in {video_or_audio_path}")
        result = {
            "source_mtime": source_mtime,
            "audio_available": False,
            "duration": duration,
            "energy_timeline": [],
            "audio_events": [],
            "silence_segments": []
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f)
        return result

    # Stream 16000Hz mono 16-bit PCM audio via FFmpeg pipe
    sample_rate = 16000
    samples_per_chunk = int(sample_rate * chunk_duration_sec)
    bytes_per_chunk = samples_per_chunk * 2  # 16-bit = 2 bytes per sample

    cmd = [
        "ffmpeg", "-y",
        "-i", video_or_audio_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", "1",
        "-f", "s16le",
        "-"
    ]

    proc = None
    rms_timeline = []
    hf_ratio_timeline = []
    chunk_index = 0

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        while True:
            raw = proc.stdout.read(bytes_per_chunk)
            if not raw or len(raw) < 100:
                break

            num_samples = len(raw) // 2
            samples = np.frombuffer(raw[:num_samples*2], dtype=np.int16).astype(np.float32) / 32768.0

            # 1. RMS Energy
            rms = float(np.sqrt(np.mean(samples ** 2)))
            timestamp = round(chunk_index * chunk_duration_sec, 2)

            # 2. High frequency energy ratio (above 1200Hz vs total) using FFT
            hf_ratio = 0.0
            if rms > 0.02 and len(samples) >= 512:
                fft_vals = np.abs(np.fft.rfft(samples[:1024]))
                freqs = np.fft.rfftfreq(1024, 1.0 / sample_rate)
                total_energy = float(np.sum(fft_vals))
                if total_energy > 1e-4:
                    hf_energy = float(np.sum(fft_vals[freqs >= 1200]))
                    hf_ratio = hf_energy / total_energy

            rms_timeline.append({"time": timestamp, "rms": rms})
            hf_ratio_timeline.append(hf_ratio)
            chunk_index += 1

        proc.wait()
    except Exception as e:
        logger.error(f"Error streaming audio signals: {e}")
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

    if not rms_timeline:
        return {
            "source_mtime": source_mtime,
            "audio_available": False,
            "duration": duration,
            "energy_timeline": [],
            "audio_events": [],
            "silence_segments": []
        }

    all_rms = np.array([x["rms"] for x in rms_timeline])
    mean_rms = float(np.mean(all_rms)) if len(all_rms) > 0 else 0.05
    std_rms = float(np.std(all_rms)) if len(all_rms) > 0 else 0.02
    peak_threshold = max(0.12, mean_rms + 1.2 * std_rms)
    silence_threshold = min(0.018, max(0.005, mean_rms * 0.3))

    # Identify Events: Loud Reactions, Screams, Laughter, Audio Spikes, and Silences
    audio_events = []
    silence_segments = []

    # Detect Silences (dead air >= 2.0 seconds)
    in_silence = False
    silence_start = 0.0
    for pt in rms_timeline:
        t = pt["time"]
        val = pt["rms"]
        if val <= silence_threshold:
            if not in_silence:
                in_silence = True
                silence_start = t
        else:
            if in_silence:
                in_silence = False
                sil_dur = t - silence_start
                if sil_dur >= 2.0:
                    silence_segments.append({
                        "start": round(silence_start, 2),
                        "end": round(t, 2),
                        "duration": round(sil_dur, 2)
                    })
    if in_silence and (duration - silence_start) >= 2.0:
        silence_segments.append({
            "start": round(silence_start, 2),
            "end": round(duration, 2),
            "duration": round(duration - silence_start, 2)
        })

    # Detect Reaction Events (high energy windows)
    in_reaction = False
    rx_start = 0.0
    rx_peak_time = 0.0
    rx_peak_val = 0.0
    rx_hf_vals = []

    for idx, pt in enumerate(rms_timeline):
        t = pt["time"]
        val = pt["rms"]
        hf = hf_ratio_timeline[idx] if idx < len(hf_ratio_timeline) else 0.0

        if val >= peak_threshold:
            if not in_reaction:
                in_reaction = True
                rx_start = t
                rx_peak_time = t
                rx_peak_val = val
                rx_hf_vals = [hf]
            else:
                rx_hf_vals.append(hf)
                if val > rx_peak_val:
                    rx_peak_val = val
                    rx_peak_time = t
        else:
            if in_reaction:
                in_reaction = False
                rx_end = t
                rx_dur = rx_end - rx_start
                if rx_dur >= 0.8: # Sustained reaction
                    avg_hf = float(np.mean(rx_hf_vals)) if rx_hf_vals else 0.0
                    intensity = min(1.0, rx_peak_val / (peak_threshold * 2.2))

                    # Classify reaction type based on spectral flux & peak
                    if avg_hf > 0.45 and rx_peak_val > peak_threshold * 1.3:
                        evt_type = "scream"
                        desc = "Streamer scream or loud shouting reaction"
                    elif 0.28 <= avg_hf <= 0.45 and rx_dur >= 1.5:
                        evt_type = "laughter"
                        desc = "Laughter or excited giggling"
                    elif rx_dur < 1.2 and rx_peak_val > peak_threshold * 1.5:
                        evt_type = "audio_spike"
                        desc = "Sudden transient audio burst (gunshot / explosion)"
                    else:
                        evt_type = "loud_reaction"
                        desc = "High energy vocal reaction"

                    audio_events.append({
                        "type": evt_type,
                        "start": round(max(0.0, rx_start - 0.5), 2),
                        "end": round(rx_end + 0.5, 2),
                        "peak_time": round(rx_peak_time, 2),
                        "intensity": round(intensity, 3),
                        "description": desc
                    })

    # Merge nearby events within 2.0s to avoid fragmented highlights
    merged_events = []
    for ev in audio_events:
        if not merged_events:
            merged_events.append(ev)
        else:
            prev = merged_events[-1]
            if ev["start"] <= prev["end"] + 2.0:
                # Merge
                prev["end"] = max(prev["end"], ev["end"])
                prev["intensity"] = max(prev["intensity"], ev["intensity"])
                if ev["intensity"] > prev["intensity"] * 0.9:
                    prev["type"] = ev["type"]
                    prev["description"] = ev["description"]
                    prev["peak_time"] = ev["peak_time"]
            else:
                merged_events.append(ev)

    # Subsample energy timeline to ~300 points for UI & caching efficiency
    sampled_energy = []
    total_chunks = len(rms_timeline)
    step = max(1, total_chunks // 300)
    for i in range(0, total_chunks, step):
        sampled_energy.append({
            "time": rms_timeline[i]["time"],
            "rms": round(rms_timeline[i]["rms"], 4)
        })

    mean_db = round(20 * math.log10(max(1e-5, mean_rms)), 1)
    silence_intervals = [[s["start"], s["end"]] for s in silence_segments]

    result = {
        "source_mtime": source_mtime,
        "audio_available": True,
        "duration": duration,
        "mean_rms": round(mean_rms, 4),
        "mean_rms_db": mean_db,
        "peak_threshold": round(peak_threshold, 4),
        "energy_timeline": sampled_energy,
        "audio_events": merged_events,
        "silence_segments": silence_segments,
        "silence_intervals": silence_intervals
    }

    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    except Exception as ex:
        logger.warning(f"Could not write audio intelligence cache: {ex}")

    return result
