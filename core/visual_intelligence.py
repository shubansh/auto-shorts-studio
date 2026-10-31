import os
import json
import logging
import cv2
import numpy as np
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

GAME_PRESETS: Dict[str, Dict[str, Any]] = {
    "generic": {"motion_thresh": 0.15, "scene_thresh": 0.40, "sample_interval": 1.5},
    "valorant": {"motion_thresh": 0.18, "scene_thresh": 0.45, "sample_interval": 1.2},
    "cs2": {"motion_thresh": 0.18, "scene_thresh": 0.45, "sample_interval": 1.2},
    "fortnite": {"motion_thresh": 0.22, "scene_thresh": 0.38, "sample_interval": 1.2},
    "pubg": {"motion_thresh": 0.16, "scene_thresh": 0.42, "sample_interval": 1.5},
    "minecraft": {"motion_thresh": 0.12, "scene_thresh": 0.35, "sample_interval": 1.8},
    "gtav": {"motion_thresh": 0.15, "scene_thresh": 0.40, "sample_interval": 1.5}
}

def analyze_visual_signals(
    video_path: str,
    cache_dir: str,
    game_type: str = "generic",
    audio_events: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Performs lightweight visual analysis using OpenCV:
      - Adaptive frame sampling (base 1.5s, adaptive around candidate audio events)
      - Downscaled grayscale processing (320x180) for minimal CPU/RAM overhead
      - Motion intensity computation (frame difference flux)
      - Scene change and cut detection (histogram dissimilarity)
      - Action bursts classification
    Caches results to disk with source mtime invalidation.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    os.makedirs(cache_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    cache_path = os.path.join(cache_dir, f"{base_name}_{game_type.lower()}_visual_signals.json")
    source_mtime = os.path.getmtime(video_path)

    # Check cache
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached.get("source_mtime") == source_mtime:
                logger.info(f"Loaded visual intelligence from cache for {base_name}")
                return cached
        except Exception as e:
            logger.warning(f"Could not read visual cache: {e}")

    preset = GAME_PRESETS.get(game_type.lower(), GAME_PRESETS["generic"])
    base_step = preset["sample_interval"]
    motion_thresh = preset["motion_thresh"]
    scene_thresh = preset["scene_thresh"]

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.warning(f"Failed to open video with OpenCV: {video_path}")
        return {
            "source_mtime": source_mtime,
            "duration": 0.0,
            "motion_timeline": [],
            "scene_transitions": [],
            "action_bursts": []
        }

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if total_frames > 0 else 60.0

    # Build adaptive sampling timeline
    # High-density timestamps around audio events, base step elsewhere
    sample_timestamps = set()
    t = 0.0
    while t < duration:
        sample_timestamps.add(round(t, 2))
        t += base_step

    if audio_events:
        for ev in audio_events:
            ev_start = max(0.0, ev.get("start", 0.0) - 2.0)
            ev_end = min(duration, ev.get("end", 0.0) + 2.0)
            cur = ev_start
            while cur <= ev_end:
                sample_timestamps.add(round(cur, 2))
                cur += 0.35 # denser sampling around audio peaks

    sorted_times = sorted(list(sample_timestamps))

    motion_timeline = []
    scene_transitions = []
    action_bursts = []

    prev_gray = None
    prev_hist = None
    prev_t = 0.0

    target_w, target_h = 320, 180

    for cur_t in sorted_times:
        frame_idx = int(cur_t * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            continue

        # Downscale for instant computation
        small = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([gray], [0], None, [32], [0, 256])
        cv2.normalize(hist, hist)

        if prev_gray is not None:
            # 1. Motion Intensity (Normalized mean frame delta)
            diff = cv2.absdiff(gray, prev_gray)
            motion_val = float(np.mean(diff) / 255.0)
            motion_timeline.append({
                "time": cur_t,
                "motion": round(motion_val, 4)
            })

            # 2. Scene Change Detection via histogram correlation
            hist_sim = float(cv2.compareHist(hist, prev_hist, cv2.HISTCMP_CORREL))
            hist_delta = 1.0 - hist_sim
            if hist_delta >= scene_thresh:
                scene_transitions.append({
                    "timestamp": cur_t,
                    "score": round(hist_delta, 3)
                })

            # 3. Action Bursts (High Motion)
            if motion_val >= motion_thresh:
                if not action_bursts or action_bursts[-1]["end"] < prev_t - 0.5:
                    action_bursts.append({
                        "start": round(prev_t, 2),
                        "end": round(cur_t, 2),
                        "intensity": round(motion_val, 3)
                    })
                else:
                    action_bursts[-1]["end"] = round(cur_t, 2)
                    action_bursts[-1]["intensity"] = max(action_bursts[-1]["intensity"], round(motion_val, 3))

        prev_gray = gray
        prev_hist = hist
        prev_t = cur_t

    cap.release()

    # Subsample motion timeline for UI & storage
    sampled_motion = []
    total_pts = len(motion_timeline)
    step = max(1, total_pts // 300)
    for i in range(0, total_pts, step):
        sampled_motion.append(motion_timeline[i])

    result = {
        "source_mtime": source_mtime,
        "duration": round(duration, 2),
        "game_type": game_type,
        "motion_timeline": sampled_motion,
        "scene_transitions": scene_transitions,
        "action_bursts": action_bursts
    }

    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    except Exception as ex:
        logger.warning(f"Could not write visual intelligence cache: {ex}")

    return result
