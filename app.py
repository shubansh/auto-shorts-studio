import os
import sys

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

import streamlit as st

st.set_page_config(
    page_title="AutoShorts Studio AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern SaaS Look
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .metric-card {
        background-color: #1a1c24;
        border: 1px solid #2e3346;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 12px;
    }
    .hook-badge {
        background: linear-gradient(90deg, #ff416c, #ff4b2b);
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 13px;
        display: inline-block;
        margin-bottom: 8px;
    }
    .title-text {
        font-weight: bold;
        font-size: 17px;
        color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ AutoShorts Studio (100% Local & Free)")
st.caption("Repurpose long videos into high-retention 9:16 Shorts & Reels using RTX 3050 GPU, Faster-Whisper, and Ollama.")

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Studio Settings")
    st.success("🟢 NVIDIA RTX 3050 (NVENC Enabled)")

    layout_mode_choice = st.selectbox(
        "📐 Video Layout Style",
        ["Smart Face-Crop (Portrait 9:16)", "Cinematic Blur Background (Full Frame)"],
        index=0,
        help="'Smart Face-Crop' tracks speaker faces. 'Cinematic Blur' shows full 16:9 frame with aesthetic blurred background."
    )
    layout_map = {
        "Smart Face-Crop (Portrait 9:16)": "crop",
        "Cinematic Blur Background (Full Frame)": "blur_fit"
    }

    theme_choice = st.selectbox(
        "🎨 Viral Caption Theme",
        ["Hormozi Gold (Viral)", "MrBeast Hype", "Neon Cyberpunk", "Emerald Mint", "Clean Minimalist"],
        index=0,
        help="Select high-retention typography and karaoke highlight color."
    )

    enable_emojis = st.checkbox(
        "✨ Auto-Emojis (Viral keywords get emojis 💰 🔥 🏆)",
        value=True,
        help="Detects keywords (money, fire, win, secret, etc.) and injects animated emojis automatically."
    )

    st.markdown("---")
    st.subheader("🧠 AI Models & Timing")

    ollama_model = st.selectbox(
        "Highlight AI Model (Ollama)",
        ["llama3.2:latest", "qwen2.5:3b"],
        index=0,
        help="Local LLM used to analyze transcript and select viral hooks."
    )

    whisper_model = st.selectbox(
        "Speech Recognition (Whisper)",
        ["small", "base", "tiny"],
        index=0,
        help="'small' provides high Hindi/English accuracy with word-level timestamps on your GPU."
    )

    num_clips = st.slider("🎬 Shorts to Generate", min_value=1, max_value=5, value=3)

    dur_range = st.slider(
        "⏱️ Target Duration (Seconds)",
        min_value=15,
        max_value=90,
        value=(20, 60),
        step=5
    )

# Main Input Section
input_tab1, input_tab2 = st.tabs(["📁 Upload Video File", "🔗 Paste YouTube URL"])

video_file_path = None
is_youtube = False

with input_tab1:
    uploaded_file = st.file_uploader(
        "Upload a video file (MP4, MOV, MKV, WebM)",
        type=["mp4", "mov", "mkv", "webm"]
    )
    if uploaded_file:
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage", "uploads")
        os.makedirs(temp_dir, exist_ok=True)
        saved_path = os.path.join(temp_dir, uploaded_file.name)
        with open(saved_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        video_file_path = saved_path
        st.success(f"Uploaded: {uploaded_file.name} ({(uploaded_file.size / (1024*1024)):.1f} MB)")

with input_tab2:
    yt_url = st.text_input("Enter YouTube Video Link", placeholder="https://www.youtube.com/watch?v=...")
    if yt_url:
        video_file_path = yt_url
        is_youtube = True

st.markdown("---")

# Generate Action
if st.button("🚀 Generate Shorts Automatically", type="primary", use_container_width=True):
    if not video_file_path:
        st.error("Please upload a video or enter a YouTube URL first!")
    else:
        progress_bar = st.progress(0)
        status_box = st.empty()

        def on_progress(title, pct, msg):
            progress_bar.progress(int(pct))
            status_box.markdown(f"**{title} ({pct:.0f}%):** {msg}")

        try:
            from pipeline import ShortsPipeline
            pipeline = ShortsPipeline(
                whisper_model=whisper_model,
                ollama_model=ollama_model
            )

            with st.spinner("Processing video..."):
                results = pipeline.process(
                    video_source=video_file_path,
                    is_youtube=is_youtube,
                    num_clips=num_clips,
                    min_duration=dur_range[0],
                    max_duration=dur_range[1],
                    subtitle_theme=theme_choice,
                    enable_emojis=enable_emojis,
                    layout_mode=layout_map.get(layout_mode_choice, "crop"),
                    progress_callback=on_progress
                )

            st.session_state["results"] = results
            st.session_state["pipeline"] = pipeline
            st.session_state["video_source"] = video_file_path
            st.balloons()
            st.success(f"🎉 Successfully generated {len(results)} Shorts!")

        except Exception as e:
            st.error(f"Error during generation: {e}")
            st.exception(e)

# Display Output Gallery & In-Browser Trim Editor
if "results" in st.session_state and st.session_state["results"]:
    results = st.session_state["results"]
    st.subheader("📱 Generated 9:16 Shorts & In-Browser Editor")
    cols = st.columns(len(results))

    for i, clip in enumerate(results):
        with cols[i]:
            st.markdown(f"""
            <div class="metric-card">
                <span class="hook-badge">🔥 Hook Score: {clip['hook_score']}/10</span>
                <div class="title-text">{clip['title']}</div>
                <p style="color: #8f9bb3; font-size: 13px; margin-top: 5px;">
                    ⏱️ {clip['duration']}s | Range: {clip['start']}s - {clip['end']}s
                </p>
                <p style="font-size: 12px; color: #a0aec0;"><i>"{clip['reason']}"</i></p>
            </div>
            """, unsafe_allow_html=True)

            if os.path.exists(clip["video_path"]):
                with open(clip["video_path"], "rb") as vf:
                    video_bytes = vf.read()
                    st.video(video_bytes)

                    st.download_button(
                        label=f"⬇️ Download Short #{clip['clip_number']}",
                        data=video_bytes,
                        file_name=clip["filename"],
                        mime="video/mp4",
                        key=f"dl_{i}",
                        use_container_width=True
                    )

            # In-Browser Trim & Re-render Editor
            with st.expander(f"✂️ Edit & Re-render Short #{clip['clip_number']}"):
                col_s, col_e = st.columns(2)
                with col_s:
                    new_start = st.number_input(
                        "Start Time (s)",
                        value=float(clip["start"]),
                        step=1.0,
                        key=f"start_{i}"
                    )
                with col_e:
                    new_end = st.number_input(
                        "End Time (s)",
                        value=float(clip["end"]),
                        step=1.0,
                        key=f"end_{i}"
                    )

                new_layout = st.selectbox(
                    "Layout",
                    ["Smart Face-Crop (Portrait 9:16)", "Cinematic Blur Background (Full Frame)"],
                    key=f"layout_{i}"
                )

                if st.button(f"⚡ Re-render Short #{clip['clip_number']}", key=f"re_{i}"):
                    if new_end <= new_start:
                        st.error("End time must be greater than start time!")
                    else:
                        with st.spinner("Re-rendering clip with NVENC..."):
                            from core.transcriber import AudioTranscriber
                            from core.audio import get_video_info
                            p = st.session_state.get("pipeline")
                            if not p:
                                from pipeline import ShortsPipeline
                                p = ShortsPipeline()

                            # Re-render this specific clip from source video
                            target_layout = "blur_fit" if "Blur" in new_layout else "crop"
                            src_vid = clip.get("source_video_path", clip["video_path"])
                            v_name = clip.get("video_filename", os.path.splitext(os.path.basename(src_vid))[0])
                            
                            ass_file = os.path.join(p.cache_dir, f"re_clip_{clip['clip_number']}.ass")
                            cache_file = os.path.join(p.cache_dir, f"{v_name}_transcript.json")
                            transcript_cache = AudioTranscriber.load_cache(cache_file)
                            segments = transcript_cache.get("segments", []) if transcript_cache else []
                            
                            p.subtitle_engine.generate_ass(segments, new_start, new_end, ass_file)
                            
                            v_meta = get_video_info(src_vid) if os.path.exists(src_vid) else {"width": 1920, "height": 1080}
                            crop_box = p.face_tracker.calculate_crop_window(src_vid, new_start, new_end, v_meta["width"], v_meta["height"]) if target_layout == "crop" else {}
                            
                            new_out_path = os.path.join(p.outputs_dir, f"Edited_Short_{clip['clip_number']}.mp4")
                            rendered = p.renderer.render_short(
                                src_vid,
                                new_start,
                                new_end,
                                crop_box,
                                ass_file,
                                new_out_path,
                                layout_mode=target_layout
                            )
                            clip["video_path"] = rendered
                            clip["start"] = new_start
                            clip["end"] = new_end
                            clip["duration"] = round(new_end - new_start, 1)
                            st.success("Re-rendered successfully!")
                            st.rerun()
