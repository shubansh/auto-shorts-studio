import logging
import json
import os
import wave
import io
import numpy as np
import torch
import ctranslate2
from faster_whisper import WhisperModel
import faster_whisper.audio
import faster_whisper.transcribe

logger = logging.getLogger(__name__)

def load_wav_file(wav_path: str) -> np.ndarray:
    """Loads 16kHz mono WAV file directly into float32 numpy array without PyAV."""
    with wave.open(wav_path, "rb") as wf:
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        return audio

def safe_decode_audio(input_file, sampling_rate=16000, split_stereo=False):
    """
    Safe replacement for faster_whisper.audio.decode_audio.
    Fixes TypeError: open() got an unexpected keyword argument 'metadata_errors' in PyAV.
    """
    if isinstance(input_file, np.ndarray):
        return input_file

    if isinstance(input_file, str) and input_file.lower().endswith(".wav") and os.path.exists(input_file):
        try:
            return load_wav_file(input_file)
        except Exception as e:
            logger.warning(f"Failed to read WAV via wave module: {e}")

    try:
        import av
        with av.open(input_file, mode="r") as container:
            resampler = av.audio.resampler.AudioResampler(
                format="s16",
                layout="mono" if not split_stereo else "stereo",
                rate=sampling_rate,
            )
            raw_buffer = io.BytesIO()
            dtype = None
            for frame in container.decode(audio=0):
                resampled = resampler.resample(frame)
                for r_frame in resampled:
                    arr = r_frame.to_ndarray()
                    dtype = arr.dtype
                    raw_buffer.write(arr)
            audio = np.frombuffer(raw_buffer.getbuffer(), dtype=dtype).astype(np.float32) / 32768.0
            return audio
    except Exception as ex:
        logger.error(f"Error in safe_decode_audio: {ex}")
        raise ex

# Apply patch to faster_whisper
faster_whisper.audio.decode_audio = safe_decode_audio
faster_whisper.transcribe.decode_audio = safe_decode_audio

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
        Passes loaded float32 numpy array to bypass any PyAV container errors.
        """
        logger.info(f"Starting transcription for {audio_path}...")
        
        # Load audio into numpy array directly
        if os.path.exists(audio_path) and audio_path.lower().endswith(".wav"):
            audio_input = load_wav_file(audio_path)
        else:
            audio_input = audio_path

        segments_generator, info = self.model.transcribe(
            audio_input,
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
