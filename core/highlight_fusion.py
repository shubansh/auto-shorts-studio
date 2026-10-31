import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Gaming excitement keywords across English, Hindi, and Hinglish
GAMING_KEYWORDS = {
    "kill": ["kill", "headshot", "mara", "mar diya", "died", "dead", "shoot", "knock", "knocked", "eliminated", "snipe", "shot"],
    "victory": ["win", "won", "victory", "jeet", "jeet gaye", "booyah", "chicken dinner", "champion", "gg", "ez"],
    "clutch": ["clutch", "1v4", "1v3", "1v2", "1v1", "rush", "save", "save kiya", "bach gaya", "last man", "intense"],
    "reaction": ["bhai", "aag", "omg", "what", "bro", "are yaar", "teri toh", "shout", "chillao", "loud", "wah", "dekho", "kya baat", "no way"],
    "laughter": ["haha", "lmao", "lol", "hasna", "funny", "joke", "comedy", "hasi", "rofl", "gadbad"]
}

def calculate_hqs(
    hook_strength: float,
    audio_intensity: float,
    event_type_weight: float,
    context_coherence: float,
    visual_motion: float
) -> tuple[float, dict]:
    """
    Computes the Explainable Highlight Quality Score (HQS: 0 - 100) and weighted sub-scores:
      - Hook Strength: 25% (max 25 pts)
      - Audio Intensity: 20% (max 20 pts)
      - In-Game Event: 25% (max 25 pts)
      - Context Coherence: 20% (max 20 pts)
      - Visual Motion: 10% (max 10 pts)
    """
    # Normalize inputs to 0.0 - 10.0 scale if passed as 0.0 - 1.0
    h_s = hook_strength * 10.0 if hook_strength <= 1.0 else hook_strength
    a_s = audio_intensity * 10.0 if audio_intensity <= 1.0 else audio_intensity
    e_s = event_type_weight * 10.0 if event_type_weight <= 1.0 else event_type_weight
    c_s = context_coherence * 10.0 if context_coherence <= 1.0 else context_coherence
    v_s = visual_motion * 10.0 if visual_motion <= 1.0 else visual_motion

    w_hook = round((h_s / 10.0) * 25.0, 1)
    w_audio = round((a_s / 10.0) * 20.0, 1)
    w_event = round((e_s / 10.0) * 25.0, 1)
    w_context = round((c_s / 10.0) * 20.0, 1)
    w_visual = round((v_s / 10.0) * 10.0, 1)

    hqs = round(w_hook + w_audio + w_event + w_context + w_visual, 1)
    hqs = max(0.0, min(100.0, hqs))

    breakdown = {
        "hook": w_hook,
        "audio": w_audio,
        "event": w_event,
        "context": w_context,
        "visual": w_visual
    }
    return hqs, breakdown

def merge_overlapping_windows(windows: List[Dict[str, Any]], iou_threshold: float = 0.45) -> List[Dict[str, Any]]:
    """Performs Non-Maximum Suppression (NMS) deduplication on candidate time windows."""
    if not windows:
        return []
    sorted_wins = sorted(windows, key=lambda w: w.get("hqs", w.get("score", 0.0)), reverse=True)
    deduped = []
    for win in sorted_wins:
        w_start = win["start"]
        w_end = win["end"]
        w_dur = win.get("duration", w_end - w_start)
        overlap = False
        for kept in deduped:
            k_start = kept["start"]
            k_end = kept["end"]
            k_dur = kept.get("duration", k_end - k_start)
            inter_start = max(w_start, k_start)
            inter_end = min(w_end, k_end)
            if inter_end > inter_start:
                inter_dur = inter_end - inter_start
                shorter_dur = min(w_dur, k_dur)
                if shorter_dur > 0 and (inter_dur / shorter_dur) > iou_threshold:
                    overlap = True
                    break
        if not overlap:
            deduped.append(win)
    return deduped

def snap_to_speech_boundary(timestamp: float, segments: List[Dict[str, Any]], mode: str = "start", max_delta: float = 2.5) -> float:
    """Snaps a timestamp to the nearest natural sentence/word boundary."""
    if not segments:
        return timestamp
    best = timestamp
    min_diff = max_delta
    for seg in segments:
        target = seg["start"] if mode == "start" else seg["end"]
        diff = abs(target - timestamp)
        if diff < min_diff:
            min_diff = diff
            best = target
    return best

def fuse_multimodal_candidates(
    audio_signals: Dict[str, Any],
    visual_signals: Dict[str, Any],
    transcript_data: Dict[str, Any],
    total_duration: float,
    num_clips: int = 3,
    min_duration: float = 20.0,
    max_duration: float = 50.0,
    scan_start: float = 0.0,
    game_type: str = "generic",
    sensitivity: float = 1.0
) -> List[Dict[str, Any]]:
    """
    Fuses Audio, Visual, and Speech signals into optimized candidate highlight windows:
      1. Collects seed event timestamps (reactions, bursts, keywords).
      2. Builds coherent pre-roll + climax + post-roll reaction windows.
      3. Snaps boundaries to Whisper sentence boundaries.
      4. Calculates Explainable Highlight Quality Score (HQS).
      5. Performs Non-Maximum Suppression (NMS) deduplication.
    """
    segments = transcript_data.get("segments", [])
    audio_events = audio_signals.get("audio_events", [])
    silences = audio_signals.get("silence_segments", [])
    action_bursts = visual_signals.get("action_bursts", [])
    scene_cuts = visual_signals.get("scene_transitions", [])

    candidates = []

    # 1. Seed Generation from Audio Reactions
    for a_ev in audio_events:
        if "peak_time" in a_ev:
            t_peak = a_ev["peak_time"]
        elif "timestamp" in a_ev:
            t_peak = a_ev["timestamp"]
        elif "start" in a_ev and "end" in a_ev:
            t_peak = (a_ev["start"] + a_ev["end"]) / 2.0
        elif "start" in a_ev:
            t_peak = a_ev["start"]
        else:
            continue

        if t_peak < scan_start:
            continue
        candidates.append({
            "seed_type": a_ev.get("type", "audio_reaction"),
            "seed_time": t_peak,
            "seed_intensity": a_ev.get("intensity", 0.7),
            "primary_signal": "audio",
            "description": a_ev.get("description", "Audio reaction")
        })

    # 2. Seed Generation from Transcript Keywords
    for seg in segments:
        seg_start = seg.get("start", 0.0)
        if seg_start < scan_start:
            continue
        txt = seg.get("text", "").lower()
        matched_cat = None
        for cat, kw_list in GAMING_KEYWORDS.items():
            if any(k in txt for k in kw_list):
                matched_cat = cat
                break
        if matched_cat:
            candidates.append({
                "seed_type": f"keyword_{matched_cat}",
                "seed_time": seg_start,
                "seed_intensity": 0.75,
                "primary_signal": "speech",
                "description": f"Streamer commentary: '{seg.get('text', '')[:40]}...'"
            })

    # 3. Seed Generation from Visual Action Bursts
    for v_ev in action_bursts:
        if "start" in v_ev and "end" in v_ev:
            v_mid = (v_ev["start"] + v_ev["end"]) / 2.0
        elif "timestamp" in v_ev:
            v_mid = v_ev["timestamp"]
        else:
            continue

        if v_mid < scan_start:
            continue
        candidates.append({
            "seed_type": "visual_action",
            "seed_time": v_mid,
            "seed_intensity": v_ev.get("intensity", v_ev.get("motion_score", 0.6)),
            "primary_signal": "visual",
            "description": "High visual motion and action burst"
        })

    # If no seeds found (e.g. silent recording), create evenly spaced fallback seeds
    if not candidates:
        step = max(30.0, (total_duration - scan_start) / max(1, num_clips + 1))
        t = scan_start + step * 0.5
        while t < total_duration - 15.0:
            candidates.append({
                "seed_type": "pacing_seed",
                "seed_time": t,
                "seed_intensity": 0.5,
                "primary_signal": "pacing",
                "description": "Pacing interval"
            })
            t += step

    # 4. Form candidate windows around each seed with pre-roll and post-roll
    target_dur = (min_duration + max_duration) / 2.0
    pre_roll = 4.0   # Context before the key event
    post_roll = 6.0  # Reaction payoff after the key event

    raw_windows = []
    for cand in candidates:
        t_key = cand["seed_time"]
        raw_start = max(scan_start, t_key - pre_roll)
        raw_end = min(total_duration, t_key + (target_dur - pre_roll))

        # Adjust length
        if (raw_end - raw_start) < min_duration:
            raw_end = min(total_duration, raw_start + min_duration)
        if (raw_end - raw_start) > max_duration:
            raw_end = raw_start + max_duration

        # Snap to speech boundaries
        snapped_start = snap_to_speech_boundary(raw_start, segments, mode="start")
        snapped_end = snap_to_speech_boundary(raw_end, segments, mode="end")

        final_start = round(max(scan_start, snapped_start), 2)
        final_end = round(min(total_duration, max(final_start + min_duration * 0.8, snapped_end)), 2)

        raw_windows.append({
            "key_time": round(t_key, 2),
            "start": final_start,
            "end": final_end,
            "duration": round(final_end - final_start, 2),
            "seed": cand
        })

    # 5. Non-Maximum Suppression (NMS) Deduplication
    raw_windows.sort(key=lambda w: w["seed"]["seed_intensity"], reverse=True)
    deduped_windows = []

    for win in raw_windows:
        overlap = False
        for kept in deduped_windows:
            inter_start = max(win["start"], kept["start"])
            inter_end = min(win["end"], kept["end"])
            if inter_end > inter_start:
                inter_dur = inter_end - inter_start
                shorter_dur = min(win["duration"], kept["duration"])
                if (inter_dur / shorter_dur) > 0.45:
                    overlap = True
                    break
        if not overlap:
            deduped_windows.append(win)

    # 6. Calculate Explainable Highlight Quality Score (HQS)
    scored_candidates = []
    for win in deduped_windows:
        w_start = win["start"]
        w_end = win["end"]

        # A. Transcript Text in window
        words_in_window = []
        for s in segments:
            if s["end"] >= w_start and s["start"] <= w_end:
                words_in_window.append(s.get("text", ""))
        transcript_snippet = " ".join(words_in_window).strip()

        # B. Hook Potential (0.0 - 10.0)
        # First 3 seconds of the clip: question, high energy, punchline
        first_3s_text = " ".join([s.get("text", "") for s in segments if s["start"] <= w_start + 3.5 and s["end"] >= w_start]).lower()
        hook_score = 7.0
        if any(q in first_3s_text for q in ["kya", "why", "how", "what", "dekh", "watch", "bhai", "omg", "wait"]):
            hook_score += 2.0
        if any(a.get("start", a.get("timestamp", 0.0)) <= w_start + 3.0 and a.get("end", a.get("timestamp", 0.0)) >= w_start for a in audio_events):
            hook_score += 1.0
        hook_score = min(10.0, max(5.0, hook_score * sensitivity))

        # C. Audio Energy & Reaction Score (0.0 - 10.0)
        rx_in_window = [
            a for a in audio_events
            if a.get("end", a.get("timestamp", 0.0)) >= w_start and a.get("start", a.get("timestamp", 0.0)) <= w_end
        ]
        audio_score = 6.0
        if rx_in_window:
            max_intensity = max(a.get("intensity", 0.5) for a in rx_in_window)
            audio_score += max_intensity * 3.5
            if any(a.get("type") in ["scream", "laughter"] for a in rx_in_window):
                audio_score += 0.8
        audio_score = min(10.0, max(4.0, audio_score))

        # D. Event Significance (0.0 - 10.0)
        event_score = 6.5
        tags = []
        txt_lower = transcript_snippet.lower()
        if any(k in txt_lower for k in GAMING_KEYWORDS["kill"]):
            event_score += 2.0
            tags.append("💀 Kill")
        if any(k in txt_lower for k in GAMING_KEYWORDS["victory"]):
            event_score += 2.5
            tags.append("👑 Victory")
        if any(k in txt_lower for k in GAMING_KEYWORDS["clutch"]):
            event_score += 2.0
            tags.append("⚡ Clutch")
        if any(k in txt_lower for k in GAMING_KEYWORDS["laughter"]) or any(a.get("type") == "laughter" for a in rx_in_window):
            tags.append("😂 Laughter")
        if any(a.get("type") == "scream" for a in rx_in_window) or any(k in txt_lower for k in GAMING_KEYWORDS["reaction"]):
            tags.append("🔊 Loud Reaction")
        if not tags:
            tags = ["🔥 Highlight", "⚡ Clip it"]
        event_score = min(10.0, max(5.0, event_score))

        # E. Context & Understandability (0.0 - 10.0)
        context_score = 8.5
        # Penalize excessive dead air / silences inside window
        sil_in_window = []
        for s in silences:
            s_start = s[0] if isinstance(s, (list, tuple)) else s.get("start", 0.0)
            s_end = s[1] if isinstance(s, (list, tuple)) else s.get("end", 0.0)
            if s_end >= w_start and s_start <= w_end:
                sil_in_window.append((s_start, s_end))
        total_sil = sum(min(w_end, s_e) - max(w_start, s_s) for s_s, s_e in sil_in_window)
        if total_sil > 3.0:
            context_score -= min(3.5, total_sil * 0.8)
        context_score = min(10.0, max(4.0, context_score))

        # F. Visual Activity Score (0.0 - 10.0)
        motion_in_window = [
            v for v in action_bursts
            if v.get("end", v.get("timestamp", 0.0)) >= w_start and v.get("start", v.get("timestamp", 0.0)) <= w_end
        ]
        visual_score = 6.5
        if motion_in_window:
            visual_score += min(3.0, len(motion_in_window) * 1.2)
        visual_score = min(10.0, max(5.0, visual_score))

        # G. Composite Highlight Quality Score (0 - 100)
        hqs, hqs_breakdown = calculate_hqs(hook_score, audio_score, event_score, context_score, visual_score)

        # Human-readable explanation
        reasons = []
        if audio_score >= 8.0:
            reasons.append("Intense vocal reaction")
        if event_score >= 8.0:
            reasons.append("Major gameplay event")
        if visual_score >= 8.0:
            reasons.append("High visual motion")
        if hook_score >= 8.5:
            reasons.append("Strong opening hook")
        explanation = " + ".join(reasons) if reasons else "Consistent engagement and pacing"

        first_words = " ".join(transcript_snippet.split()[:5])
        title = first_words if first_words else f"Highlight at {int(w_start)}s"

        scored_candidates.append({
            "start": w_start,
            "end": w_end,
            "duration": win["duration"],
            "title": title,
            "hook_score": round(hook_score, 1),
            "hqs": hqs,
            "score": round(hqs / 10.0, 1),
            "tags": tags[:3],
            "reason": explanation,
            "transcript_snippet": transcript_snippet[:150],
            "hqs_breakdown": hqs_breakdown,
            "confidence": round(min(0.98, max(0.65, 0.70 + (hqs / 400.0))), 2)
        })

    # Sort candidates by HQS descending
    scored_candidates.sort(key=lambda c: c["hqs"], reverse=True)
    return scored_candidates[:num_clips]
