import logging
import json
import os
import torch
import ctranslate2
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

class AudioTranscriber:
    def __init__(self, model_size="small", device=None, compute_type=None):
        if device is None:
            if ctranslate2.get_cuda_device_count() > 0:
                self.device = "cuda"
                self.compute_type = "float16" if compute_type is None else compute_type
            else:
                self.device = "cpu"
                self.compute_type = "int8" if compute_type is None else compute_type
        else:
            self.device = device
            self.compute_type = compute_type or ("float16" if device == "cuda" else "int8")

        self.model_size = model_size
        logger.info(f"Initializing WhisperModel({model_size}) on {self.device} ({self.compute_type})")
        self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)

    def transcribe(self, audio_path: str, language=None) -> dict:
        """
        Transcribes audio with word-level timestamps.
        Returns a dictionary with full_text and detailed segments.
        """
        logger.info(f"Starting transcription for {audio_path}...")
        segments_generator, info = self.model.transcribe(
            audio_path,
            language=language,
            word_timestamps=True,
            vad_filter=True, # Skip silences
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        detected_lang = info.language
        lang_prob = info.language_probability
        logger.info(f"Detected language: {detected_lang} (confidence: {lang_prob:.2f})")

        segments_data = []
        full_text_list = []

        for seg in segments_generator:
            words_data = []
            if seg.words:
                for w in seg.words:
                    words_data.append({
                        "word": w.word.strip(),
                        "start": round(w.start, 3),
                        "end": round(w.end, 3),
                        "probability": round(w.probability, 3)
                    })

            segments_data.append({
                "id": seg.id,
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text.strip(),
                "words": words_data
            })
            full_text_list.append(seg.text.strip())

        result = {
            "language": detected_lang,
            "language_probability": round(lang_prob, 3),
            "full_text": " ".join(full_text_list),
            "segments": segments_data
        }
        return result

    @staticmethod
    def save_cache(data: dict, cache_path: str):
        os.makedirs(os.path.dirname(os.path.abspath(cache_path)), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def load_cache(cache_path: str) -> dict:
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
