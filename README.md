# ⚡ AutoShorts Studio (100% Free & Local AI Platform)

An end-to-end automated platform to repurpose long-form videos (Podcasts, Streams, Talks, YouTube Videos) into high-retention 9:16 Shorts & Reels.

Inspired by **OpusClip** and **Powder.gg**, built to run **100% locally and free** on your computer.

---

## 🚀 Key Features

1. **GPU-Accelerated Transcription (`Faster-Whisper`):**
   - Transcribes audio on your **RTX 3050** using CUDA.
   - Extracts word-level timestamps with VAD (Voice Activity Detection).
2. **AI Highlight Finder (`Ollama` + `Llama 3.2`):**
   - Discovers the top viral hooks and complete thoughts within your target duration (20s - 60s).
   - Generates hook score (1-10) and catchy titles.
3. **Smart 16:9 to 9:16 Auto-Crop (`OpenCV` + Face Detection):**
   - Detects the active speaker's face and keeps them centered smoothly in the vertical 9:16 frame.
4. **Alex Hormozi Style Karaoke Subtitles:**
   - Word-by-word animated yellow/green highlight.
   - High contrast outline with drop shadow for mobile feeds.
5. **Hardware Video Rendering (`FFmpeg NVENC`):**
   - Uses your RTX 3050's hardware encoder (`h264_nvenc`) to export 1080x1920 vertical videos in seconds.
6. **Local Web Dashboard (`Streamlit`):**
   - Drag & drop local videos or paste YouTube URLs.
   - Real-time progress bar, embedded video players, and 1-click download buttons.

---

## 🖥️ How to Run

### Method 1: Double-Click Launcher
Simply double-click on `run.bat` inside the `auto_shorts_studio` folder.

### Method 2: Command Line
Open PowerShell or Terminal in this folder and run:
```bash
streamlit run app.py
```
Then open your browser at **http://localhost:8501**.

---

## 📁 Project Structure

```
auto_shorts_studio/
├── core/
│   ├── audio.py              # FFmpeg audio split & yt-dlp downloader
│   ├── transcriber.py        # Faster-Whisper GPU speech recognition
│   ├── highlight_detector.py # Ollama viral hook detection
│   ├── face_tracker.py       # OpenCV smart 9:16 face cropping
│   ├── subtitle_engine.py    # Animated ASS karaoke subtitles
│   └── video_renderer.py     # FFmpeg NVENC 1080x1920 video exporter
├── app.py                    # Streamlit Web UI
├── pipeline.py               # Central orchestrator
├── run.bat                   # 1-Click launcher
└── storage/
    ├── uploads/              # Uploaded videos
    ├── audio/                # 16kHz WAV audio files
    ├── cache/                # Transcripts & subtitle files
    └── outputs/              # Ready-to-post 9:16 Shorts
```
