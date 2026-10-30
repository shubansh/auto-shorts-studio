import os
import re
import logging

logger = logging.getLogger(__name__)

# Color mapping in ASS &HAABBGGRR format
SUBTITLE_THEMES = {
    "Hormozi Gold (Viral)": {
        "primary": "&H00FFFFFF",     # White
        "highlight": "&H0000FFFF",   # Bright Gold / Yellow
        "outline": "&H00000000",     # Solid Black
        "outline_size": 5,
        "shadow_size": 2,
        "font": "Nirmala UI",
        "size": 54
    },
    "MrBeast Hype": {
        "primary": "&H0000FFFF",     # Bright Yellow
        "highlight": "&H000000FF",   # Punchy Red
        "outline": "&H00000000",     # Deep Black Outline
        "outline_size": 6,
        "shadow_size": 3,
        "font": "Nirmala UI",
        "size": 56
    },
    "Neon Cyberpunk": {
        "primary": "&H00FFFF00",     # Electric Cyan
        "highlight": "&H00FF00FF",   # Hot Neon Pink
        "outline": "&H00100505",     # Dark Navy
        "outline_size": 5,
        "shadow_size": 2,
        "font": "Segoe UI",
        "size": 52
    },
    "Emerald Mint": {
        "primary": "&H00FFFFFF",     # White
        "highlight": "&H0000FF66",   # Neon Mint Green
        "outline": "&H00000000",     # Solid Black
        "outline_size": 5,
        "shadow_size": 2,
        "font": "Nirmala UI",
        "size": 52
    },
    "Clean Minimalist": {
        "primary": "&H00DDDDDD",     # Muted White
        "highlight": "&H00FFFFFF",   # Pure White
        "outline": "&H00222222",     # Charcoal Border
        "outline_size": 3,
        "shadow_size": 1,
        "font": "Segoe UI",
        "size": 48
    }
}

# Auto-Emoji Keyword Mapping (English + Hindi / Hinglish)
EMOJI_KEYWORDS = {
    # Wealth & Money
    r"\b(money|paisa|paise|rupee|rupees|crore|lakh|rich|dollar|cash|ameer|daulat)\b": "💰",
    # Fire & Hype
    r"\b(fire|hot|aag|viral|crazy|insane|killer|banger)\b": "🔥",
    # Love & Emotion
    r"\b(love|pyar|dil|heart|ishq|mohabbat)\b": "❤️",
    # Winning & Success
    r"\b(win|winner|won|jeet|jeeta|trophy|champion|number 1|first)\b": "🏆",
    # Growth & Future
    r"\b(rocket|grow|growth|success|future|tarakki)\b": "🚀",
    # Secret & Mystery
    r"\b(secret|raaz|mystery|hack|hacks|trick|tricks)\b": "🤫",
    # Mind & Thinking
    r"\b(mind|brain|dimag|soch|think|thinking|idea)\b": "🧠",
    # Warning & Danger
    r"\b(danger|khatra|warning|shock|shocking|scam|dhokha)\b": "⚠️",
    # Stop & Pause
    r"\b(stop|wait|ruk|ruko|pause|suno)\b": "🛑",
    # Gaming & Play
    r"\b(game|gaming|khel|player|play)\b": "🎮",
    # Music & Song
    r"\b(music|gana|song|sing|singer|dhun)\b": "🎵",
    # Laugh & Comedy
    r"\b(laugh|funny|joke|hasi|mazaak)\b": "😂",
    # Car & Speed
    r"\b(car|gaadi|drive|speed|fast|bhag)\b": "🏎️",
    # Target & Focus
    r"\b(target|goal|focus|aim|lakshya)\b": "🎯",
    # Dog / Animals
    r"\b(dog|doggy|kutte|kutta|puppy)\b": "🐶",
    # Food & Drink
    r"\b(food|khana|khao|eat|eating|burger|chai|coffee)\b": "🍔",
    # Phone & Tech
    r"\b(phone|mobile|call|iphone|android)\b": "📱"
}

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

def get_word_emoji(word: str) -> str:
    """Returns an emoji if word matches viral keywords, else empty string."""
    clean_w = re.sub(r"[^\w]", "", word).lower()
    for pattern, emoji in EMOJI_KEYWORDS.items():
        if re.search(pattern, clean_w):
            return emoji
    return ""

class SubtitleEngine:
    def __init__(self, theme_name="Hormozi Gold (Viral)", enable_emojis=True):
        theme = SUBTITLE_THEMES.get(theme_name, SUBTITLE_THEMES["Hormozi Gold (Viral)"])
        self.theme_name = theme_name
        self.font_name = theme["font"]
        self.font_size = theme["size"]
        self.primary_color = theme["primary"]
        self.highlight_color = theme["highlight"]
        self.outline_color = theme["outline"]
        self.outline_size = theme["outline_size"]
        self.shadow_size = theme["shadow_size"]
        self.enable_emojis = enable_emojis

    def generate_ass(self, segments: list, clip_start: float, clip_end: float, output_ass_path: str, video_w=1080, video_h=1920) -> str:
        """
        Creates an Advanced SubStation Alpha (.ass) subtitle file with word-by-word karaoke highlight
        and optional auto-emoji injections for the given clip time range.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_ass_path)), exist_ok=True)

        # Extract words that fall inside [clip_start, clip_end]
        clip_words = []
        for seg in segments:
            for w in seg.get("words", []):
                w_start = w["start"]
                w_end = w["end"]
                if w_end > clip_start and w_start < clip_end:
                    adj_start = max(0.0, w_start - clip_start)
                    adj_end = max(adj_start + 0.1, min(clip_end - clip_start, w_end - clip_start))
                    
                    word_text = w["word"].strip()
                    # Optionally attach auto-emoji
                    if self.enable_emojis:
                        emoji = get_word_emoji(word_text)
                        if emoji:
                            word_text = f"{word_text} {emoji}"

                    clip_words.append({
                        "word": word_text.upper(),
                        "start": adj_start,
                        "end": adj_end
                    })

        # Group words into 3-4 word punchy phrases
        phrases = []
        curr_phrase = []
        for i, cw in enumerate(clip_words):
            curr_phrase.append(cw)
            is_pause = False
            if i + 1 < len(clip_words):
                if clip_words[i+1]["start"] - cw["end"] > 0.4:
                    is_pause = True
            
            if len(curr_phrase) >= 4 or is_pause or i == len(clip_words) - 1:
                phrases.append(curr_phrase)
                curr_phrase = []

        # ASS Header with high quality style configuration
        ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_w}
PlayResY: {video_h}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ViralStyle,{self.font_name},{self.font_size},{self.primary_color},{self.highlight_color},{self.outline_color},&H80000000,-1,0,0,0,100,100,1.5,0,1,{self.outline_size},{self.shadow_size},2,40,40,380,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        # Generate Dialogue lines with karaoke tags
        for phrase in phrases:
            if not phrase:
                continue
            line_start = phrase[0]["start"]
            line_end = phrase[-1]["end"]
            
            karaoke_text = ""
            for pw in phrase:
                dur_cs = max(1, int(round((pw["end"] - pw["start"]) * 100)))
                karaoke_text += f"{{\\k{dur_cs}}}{pw['word']} "
            
            start_str = format_ass_time(line_start)
            end_str = format_ass_time(line_end)
            
            ass_content += f"Dialogue: 0,{start_str},{end_str},ViralStyle,,0,0,0,,{karaoke_text.strip()}\n"

        with open(output_ass_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

        logger.info(f"Generated ASS subtitle file: {output_ass_path} ({len(phrases)} phrases, theme={self.theme_name})")
        return output_ass_path
