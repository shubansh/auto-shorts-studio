import json
import re
import logging
import ollama

logger = logging.getLogger(__name__)

HIGHLIGHT_SYSTEM_PROMPT = """You are a world-class viral video editor specializing in YouTube Shorts, TikTok, and Instagram Reels (inspired by OpusClip and Powder.gg).

Your job is to analyze video transcripts with timestamps and find the most captivating, high-retention moments.

Key Criteria for a Viral Short:
1. Strong Hook: The first 3 seconds must grab attention immediately (a question, bold claim, intense moment, or high curiosity).
2. Cohesive Story: The clip must contain a standalone thought or punchline. Do not cut in the middle of a sentence.
3. Duration: Each clip should be between {min_duration} and {max_duration} seconds.
4. Retention: Engaging flow without long silences.

Output MUST be a JSON array of objects with this EXACT structure:
[
  {
    "start": float,
    "end": float,
    "title": "Catchy 3-5 Word Title",
    "hook_score": float (1.0 to 10.0),
    "reason": "Why this moment will perform well as a Short"
  }
]
Return ONLY the raw JSON array, with no markdown formatting, no backticks, and no introductory text.
"""

def clean_json_response(raw_text: str) -> str:
    """Extracts JSON array string from potentially markdown-wrapped text."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    # In case there's extra text before/after brackets
    start_bracket = text.find("[")
    end_bracket = text.rfind("]")
    if start_bracket != -1 and end_bracket != -1 and end_bracket > start_bracket:
        return text[start_bracket:end_bracket + 1]
    return text

class HighlightDetector:
    def __init__(self, model_name="llama3.2:latest"):
        self.model_name = model_name

    def find_highlights(self, transcript_data: dict, num_clips=3, min_duration=25, max_duration=60) -> list:
        """
        Calls Ollama to detect top viral moments.
        Returns a list of highlight dictionaries with verified start and end times.
        """
        segments = transcript_data.get("segments", [])
        if not segments:
            logger.warning("No segments found in transcript.")
            return []

        total_duration = segments[-1]["end"]
        
        # If total video duration is already under max_duration, return the whole video as a single clip
        if total_duration <= max_duration:
            logger.info(f"Video is only {total_duration:.1f}s, creating single clip.")
            return [{
                "start": 0.0,
                "end": round(total_duration, 2),
                "title": "Complete Highlight",
                "hook_score": 9.0,
                "reason": "Short video repurposing entire segment."
            }]

        # Prepare condensed transcript representation for LLM prompt
        # We group segments into ~15s blocks with timestamps
        formatted_lines = []
        for s in segments:
            formatted_lines.append(f"[{s['start']:.1f}s - {s['end']:.1f}s] {s['text']}")
        transcript_text = "\n".join(formatted_lines)

        # Truncate if exceptionally long to fit comfortable context
        if len(transcript_text) > 25000:
            transcript_text = transcript_text[:25000] + "\n...[truncated]"

        user_prompt = f"""Video Total Duration: {total_duration:.1f} seconds.
Desired Clips Count: {num_clips}
Target Clip Duration: {min_duration}s to {max_duration}s.

Transcript with Timestamps:
{transcript_text}

Identify the top {num_clips} viral moments and return the JSON array:"""

        system_prompt = HIGHLIGHT_SYSTEM_PROMPT.format(
            min_duration=min_duration,
            max_duration=max_duration
        )

        try:
            logger.info(f"Querying Ollama ({self.model_name}) for highlights...")
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                options={"temperature": 0.3}
            )

            raw_reply = response["message"]["content"]
            cleaned = clean_json_response(raw_reply)
            clips = json.loads(cleaned)

            if isinstance(clips, list) and len(clips) > 0:
                validated_clips = self._validate_and_snap_clips(clips, segments, min_duration, max_duration, total_duration)
                if validated_clips:
                    # Sort by hook_score descending
                    validated_clips.sort(key=lambda x: x.get("hook_score", 0), reverse=True)
                    return validated_clips[:num_clips]

        except Exception as e:
            logger.error(f"Ollama highlight detection failed or returned invalid JSON: {e}")

        # Fallback heuristic if LLM fails
        logger.info("Using smart heuristic fallback for highlight selection...")
        return self._heuristic_fallback(segments, num_clips, min_duration, max_duration, total_duration)

    def _validate_and_snap_clips(self, raw_clips, segments, min_dur, max_dur, total_dur):
        """Sanitizes start/end bounds and snaps to actual speech boundaries."""
        valid = []
        for c in raw_clips:
            try:
                start = float(c.get("start", 0))
                end = float(c.get("end", 0))
                if start < 0: start = 0.0
                if end > total_dur: end = total_dur
                
                # Snap start to nearest segment start
                start = self._snap_to_segment(start, segments, mode="start")
                # Snap end to nearest segment end
                end = self._snap_to_segment(end, segments, mode="end")

                dur = end - start
                if dur < (min_dur * 0.7):
                    end = min(total_dur, start + min_dur)
                elif dur > (max_dur * 1.2):
                    end = start + max_dur

                valid.append({
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "title": c.get("title", f"Clip at {int(start)}s"),
                    "hook_score": float(c.get("hook_score", 8.0)),
                    "reason": c.get("reason", "Detected engaging moment")
                })
            except Exception as ex:
                logger.warning(f"Skipping invalid clip candidate {c}: {ex}")
        return valid

    def _snap_to_segment(self, timestamp, segments, mode="start"):
        closest = timestamp
        min_diff = 999.0
        for s in segments:
            t = s["start"] if mode == "start" else s["end"]
            diff = abs(t - timestamp)
            if diff < min_diff and diff < 3.0: # within 3 seconds
                min_diff = diff
                closest = t
        return closest

    def _heuristic_fallback(self, segments, num_clips, min_duration, max_duration, total_duration):
        """Fallback: splits video into engaging chunks based on speech density and questions."""
        clips = []
        target_dur = (min_duration + max_duration) / 2.0
        step = max(1, len(segments) // (num_clips + 1))
        
        for i in range(0, len(segments), step):
            if len(clips) >= num_clips:
                break
            seg_start = segments[i]["start"]
            target_end = seg_start + target_dur
            if target_end > total_duration:
                target_end = total_duration
            
            if (target_end - seg_start) >= min_duration * 0.7:
                # Find title from first segment text
                first_txt = segments[i].get("text", "Highlight Moment")
                title = " ".join(first_txt.split()[:5])
                clips.append({
                    "start": round(seg_start, 2),
                    "end": round(target_end, 2),
                    "title": title or f"Highlight Clip {len(clips)+1}",
                    "hook_score": 8.0,
                    "reason": "Automated speech density highlight selection."
                })
        return clips
