import os
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
        margin-bottom: 15px;
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
        font-size: 18px;
        color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ AutoShorts Studio (100% Local & Free)")
st.caption("Repurpose long videos into high-retention 9:16 Shorts & Reels using RTX 3050 GPU, Faster-Whisper, and Ollama.")

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Settings & Hardware")
    st.success("🟢 NVIDIA RTX 3050 (NVENC Enabled)")

    ollama_model = st.selectbox(
        "🧠 AI Highlight Model (Ollama)",
        ["llama3.2:latest", "qwen2.5:3b"],
        index=0,
        help="Local LLM used to analyze transcript and select viral hooks."
    )

    whisper_model = st.selectbox(
        "🎙️ Speech Recognition (Whisper)",
        ["small", "base", "tiny"],
        index=0,
        help="'small' provides high Hindi/English accuracy with word-level timestamps on your GPU."
    )

    num_clips = st.slider("🎬 Number of Shorts to Generate", min_value=1, max_value=5, value=3)

    dur_range = st.slider(
        "⏱️ Target Duration (Seconds)",
        min_value=15,
        max_value=90,
        value=(20, 60),
        step=5
    )

    color_choice = st.selectbox(
        "🎨 Subtitle Karaoke Color",
        ["Bright Yellow", "Neon Green", "Electric Cyan", "Vibrant Pink"],
        index=0
    )

    color_map = {
        "Bright Yellow": "&H0000FFFF",
        "Neon Green": "&H0000FF00",
        "Electric Cyan": "&H00FFFF00",
        "Vibrant Pink": "&H00FF00FF"
    }

# Main Input Section
input_tab1, input_tab2 = st.tabs(["📁 Upload Video File", "🔗 Paste YouTube URL"])

video_file_path = None
is_youtube = False

with input_tab1:
    uploaded_file = st.file_uploader(
        "Upload a long video (MP4, MOV, MKV, WebM)",
        type=["mp4", "mov", "mkv", "webm"]
    )
    if uploaded_file:
        temp_dir = os.path.join("storage", "uploads")
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
                    highlight_color=color_map.get(color_choice, "&H0000FFFF"),
                    progress_callback=on_progress
                )

            st.balloons()
            st.success(f"🎉 Successfully generated {len(results)} Shorts!")

            # Display Output Gallery
            st.subheader("📱 Generated 9:16 Shorts")
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

        except Exception as e:
            st.error(f"Error during generation: {e}")
            st.exception(e)
