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
from PIL import Image, ImageDraw

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
    .gaming-box {
        background: #161a23;
        border: 1px solid #3b82f6;
        border-radius: 8px;
        padding: 15px;
        margin-top: 10px;
        margin-bottom: 15px;
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
        [
            "Smart Face-Crop (Portrait 9:16)",
            "🎮 Powder.gg Gaming Mode (Facecam + Gameplay Stack)",
            "Cinematic Blur Background (Full Frame)"
        ],
        index=0,
        help="'Smart Face-Crop' tracks speaker faces. 'Gaming Mode' stacks streamer facecam on top and gameplay on bottom. 'Cinematic Blur' keeps full 16:9 widescreen frame."
    )
    layout_map = {
        "Smart Face-Crop (Portrait 9:16)": "crop",
        "🎮 Powder.gg Gaming Mode (Facecam + Gameplay Stack)": "gaming_split",
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

# Powder.gg Gaming Layout Selector
gaming_config = None
if layout_map[layout_mode_choice] == "gaming_split":
    st.markdown("""
    <div class="gaming-box">
        <h4 style="margin: 0; color: #60a5fa;">🎮 Powder.gg Gaming Split-Screen Configuration</h4>
        <p style="color: #94a3b8; font-size: 13px; margin-top: 4px;">
            Customize your <b>Facecam Box</b> (top of Short) and <b>Gameplay Box</b> (bottom of Short).
        </p>
    </div>
    """, unsafe_allow_html=True)

    streamer_preset = st.selectbox(
        "🎛️ Streamer Layout Preset",
        [
            "Center-Top Facecam (Like Spyki Plays)",
            "Top-Right Facecam (Scout, Mortal, Dynamo style)",
            "Top-Left Facecam",
            "Bottom-Right Facecam",
            "Bottom-Left Facecam",
            "Custom Manual Selection"
        ],
        index=0
    )

    preset_defaults = {
        "Center-Top Facecam (Like Spyki Plays)": {"fc_x": 28, "fc_y": 15, "fc_w": 44, "fc_h": 45, "gp_x": 15, "gp_y": 0, "gp_w": 70, "gp_h": 100},
        "Top-Right Facecam (Scout, Mortal, Dynamo style)": {"fc_x": 65, "fc_y": 5, "fc_w": 32, "fc_h": 40, "gp_x": 15, "gp_y": 0, "gp_w": 70, "gp_h": 100},
        "Top-Left Facecam": {"fc_x": 5, "fc_y": 5, "fc_w": 32, "fc_h": 40, "gp_x": 15, "gp_y": 0, "gp_w": 70, "gp_h": 100},
        "Bottom-Right Facecam": {"fc_x": 65, "fc_y": 55, "fc_w": 32, "fc_h": 40, "gp_x": 15, "gp_y": 0, "gp_w": 70, "gp_h": 100},
        "Bottom-Left Facecam": {"fc_x": 5, "fc_y": 55, "fc_w": 32, "fc_h": 40, "gp_x": 15, "gp_y": 0, "gp_w": 70, "gp_h": 100},
        "Custom Manual Selection": {"fc_x": 30, "fc_y": 10, "fc_w": 40, "fc_h": 40, "gp_x": 15, "gp_y": 0, "gp_w": 70, "gp_h": 100}
    }

    cur_p = preset_defaults.get(streamer_preset, preset_defaults["Center-Top Facecam (Like Spyki Plays)"])

    col_fc, col_gp = st.columns(2)
    with col_fc:
        st.markdown("**📷 1. Facecam Area (Top 40% of Short)**")
        fc_x = st.slider("Facecam Horizontal X (%)", 0, 100, cur_p["fc_x"])
        fc_y = st.slider("Facecam Vertical Y (%)", 0, 100, cur_p["fc_y"])
        fc_w = st.slider("Facecam Width (%)", 15, 60, cur_p["fc_w"])
        fc_h = st.slider("Facecam Height (%)", 15, 60, cur_p["fc_h"])

    with col_gp:
        st.markdown("**🎯 2. Main Gameplay Area (Bottom 60% of Short)**")
        gp_x = st.slider("Gameplay Center X (%)", 0, 100, cur_p["gp_x"])
        gp_y = st.slider("Gameplay Vertical Y (%)", 0, 100, cur_p["gp_y"])
        gp_w = st.slider("Gameplay Width (%)", 40, 100, cur_p["gp_w"])
        gp_h = st.slider("Gameplay Height (%)", 40, 100, cur_p["gp_h"])

    # Visual Frame Preview with Live Bounding Boxes
    v_w, v_h = 1920, 1080
    fc_pixel_x = int((fc_x / 100.0) * v_w)
    fc_pixel_y = int((fc_y / 100.0) * v_h)
    fc_pixel_w = int((fc_w / 100.0) * v_w)
    fc_pixel_h = int((fc_h / 100.0) * v_h)

    gp_pixel_x = int((gp_x / 100.0) * v_w)
    gp_pixel_y = int((gp_y / 100.0) * v_h)
    gp_pixel_w = int((gp_w / 100.0) * v_w)
    gp_pixel_h = int((gp_h / 100.0) * v_h)

    # Ensure even coordinates for video codecs
    if fc_pixel_x % 2 != 0: fc_pixel_x += 1
    if fc_pixel_y % 2 != 0: fc_pixel_y += 1
    if fc_pixel_w % 2 != 0: fc_pixel_w += 1
    if fc_pixel_h % 2 != 0: fc_pixel_h += 1

    if gp_pixel_x % 2 != 0: gp_pixel_x += 1
    if gp_pixel_y % 2 != 0: gp_pixel_y += 1
    if gp_pixel_w % 2 != 0: gp_pixel_w += 1
    if gp_pixel_h % 2 != 0: gp_pixel_h += 1

    gaming_config = {
        "facecam": {"x": fc_pixel_x, "y": fc_pixel_y, "w": fc_pixel_w, "h": fc_pixel_h},
        "gameplay": {"x": gp_pixel_x, "y": gp_pixel_y, "w": gp_pixel_w, "h": gp_pixel_h},
        "top_height": 760
    }

    # Draw Live Visual Bounding Box Preview
    preview_box_img = Image.new("RGB", (960, 540), color=(20, 24, 33))
    draw = ImageDraw.Draw(preview_box_img)

    # Scale coordinates to preview size (960x540 = 0.5x)
    s_fc_x, s_fc_y = fc_pixel_x // 2, fc_pixel_y // 2
    s_fc_w, s_fc_h = fc_pixel_w // 2, fc_pixel_h // 2
    s_gp_x, s_gp_y = gp_pixel_x // 2, gp_pixel_y // 2
    s_gp_w, s_gp_h = gp_pixel_w // 2, gp_pixel_h // 2

    # Draw gameplay box (Cyan)
    draw.rectangle([s_gp_x, s_gp_y, s_gp_x + s_gp_w, s_gp_y + s_gp_h], outline=(0, 210, 255), width=3)
    draw.text((s_gp_x + 10, s_gp_y + 10), "🎯 GAMEPLAY AREA (Bottom 60%)", fill=(0, 210, 255))

    # Draw facecam box (Neon Green)
    draw.rectangle([s_fc_x, s_fc_y, s_fc_x + s_fc_w, s_fc_y + s_fc_h], outline=(0, 255, 120), width=3)
    draw.text((s_fc_x + 10, s_fc_y + 10), "📷 FACECAM (Top 40%)", fill=(0, 255, 120))

    st.image(preview_box_img, caption="Live Powder.gg Visual Split-Screen Alignment Map (16:9 Screen)", use_container_width=True)

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
                    gaming_config=gaming_config,
                    progress_callback=on_progress
                )

            st.session_state["results"] = results
            st.session_state["pipeline"] = pipeline
            st.session_state["gaming_config"] = gaming_config
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
                    [
                        "Smart Face-Crop (Portrait 9:16)",
                        "🎮 Powder.gg Gaming Mode (Facecam + Gameplay Stack)",
                        "Cinematic Blur Background (Full Frame)"
                    ],
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
                            target_layout = layout_map.get(new_layout, "crop")
                            src_vid = clip.get("source_video_path", clip["video_path"])
                            v_name = clip.get("video_filename", os.path.splitext(os.path.basename(src_vid))[0])
                            
                            ass_file = os.path.join(p.cache_dir, f"re_clip_{clip['clip_number']}.ass")
                            cache_file = os.path.join(p.cache_dir, f"{v_name}_transcript.json")
                            transcript_cache = AudioTranscriber.load_cache(cache_file)
                            segments = transcript_cache.get("segments", []) if transcript_cache else []
                            
                            p.subtitle_engine.generate_ass(segments, new_start, new_end, ass_file)
                            
                            v_meta = get_video_info(src_vid) if os.path.exists(src_vid) else {"width": 1920, "height": 1080}
                            if target_layout == "gaming_split":
                                crop_box = st.session_state.get("gaming_config") or {
                                    "facecam": {"x": 1300, "y": 50, "w": 580, "h": 460},
                                    "gameplay": {"x": 420, "y": 0, "w": 1080, "h": 1080},
                                    "top_height": 760
                                }
                            elif target_layout == "crop":
                                crop_box = p.face_tracker.calculate_crop_window(src_vid, new_start, new_end, v_meta["width"], v_meta["height"])
                            else:
                                crop_box = {}
                            
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
