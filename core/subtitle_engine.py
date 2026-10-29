import os
import logging

logger = logging.getLogger(__name__)

def format_ass_time(seconds: float) -> str:
    """Formats float seconds into ASS subtitle timestamp: H:MM:SS.cs"""
    if seconds < 0:
        seconds = 0.0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

class SubtitleEngine:
    def __init__(self, font_name="Arial", font_size=20, primary_color="&H00FFFFFF", highlight_color="&H0000FFFF"):
        """
        Colors are in ASS &HAABBGGRR format:
        &H00FFFFFF = Solid White
        &H0000FFFF = Solid Bright Yellow
        &H0000FF00 = Neon Green
        """
        self.font_name = font_name
        self.font_size = font_size
        self.primary_color = primary_color
        self.highlight_color = highlight_color

    def generate_ass(self, segments: list, clip_start: float, clip_end: float, output_ass_path: str, video_w=1080, video_h=1920) -> str:
        """
        Creates an Advanced SubStation Alpha (.ass) subtitle file with word-by-word karaoke highlight
        for the given clip time range.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_ass_path)), exist_ok=True)

        # Extract words that fall inside [clip_start, clip_end]
        clip_words = []
        for seg in segments:
            for w in seg.get("words", []):
                w_start = w["start"]
                w_end = w["end"]
                if w_end > clip_start and w_start < clip_end:
                    # Clip boundaries
                    adj_start = max(0.0, w_start - clip_start)
                    adj_end = max(adj_start + 0.1, min(clip_end - clip_start, w_end - clip_start))
                    clip_words.append({
                        "word": w["word"].upper().strip(),
                        "start": adj_start,
                        "end": adj_end
                    })

        # Group words into 3-4 word phrases
        phrases = []
        curr_phrase = []
        for i, cw in enumerate(clip_words):
            curr_phrase.append(cw)
            # Break condition: 4 words or big pause > 0.4s
            is_pause = False
            if i + 1 < len(clip_words):
                if clip_words[i+1]["start"] - cw["end"] > 0.4:
                    is_pause = True
            
            if len(curr_phrase) >= 4 or is_pause or i == len(clip_words) - 1:
                phrases.append(curr_phrase)
                curr_phrase = []

        # ASS Header with 9:16 target resolution and stylish bold typography
        # Alignment 2 = bottom-center, MarginV = 320 (comfortably above TikTok/Reels UI)
        ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_w}
PlayResY: {video_h}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hormozi,{self.font_name},52,{self.primary_color},{self.highlight_color},&H00000000,&H80000000,-1,0,0,0,100,100,1.5,0,1,5,2,2,40,40,380,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        # Generate Dialogue lines with karaoke tags
        for phrase in phrases:
            if not phrase:
                continue
            line_start = phrase[0]["start"]
            line_end = phrase[-1]["end"]
            
            # Karaoke string builder
            karaoke_text = ""
            for pw in phrase:
                dur_cs = max(1, int(round((pw["end"] - pw["start"]) * 100)))
                # ASS karaoke tag: \k<centiseconds>
                karaoke_text += f"{{\\k{dur_cs}}}{pw['word']} "
            
            start_str = format_ass_time(line_start)
            end_str = format_ass_time(line_end)
            
            ass_content += f"Dialogue: 0,{start_str},{end_str},Hormozi,,0,0,0,,{karaoke_text.strip()}\n"

        with open(output_ass_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

        logger.info(f"Generated ASS subtitle file: {output_ass_path} ({len(phrases)} phrases)")
        return output_ass_path
