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
from core.audio import extract_preview_frame, get_video_info, download_youtube_video

st.set_page_config(
    page_title="AutoShorts Studio AI (Powder.gg Edition)",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom High-End Gaming SaaS CSS (Inspired by Powder.gg & OpusClip)
st.markdown("""
<style>
    .main {
        background: #0b0e14;
        color: #f1f5f9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .step-banner {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 12px;
        padding: 12px 24px;
        margin-bottom: 20px;
    }
    .step-pill {
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
    }
    .step-active {
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        color: white;
    }
    .step-idle {
        background: #1f2937;
        color: #94a3b8;
    }
    .glass-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 18px;
    }
    .glass-card-accent {
        background: #111827;
        border: 1px solid #3b82f6;
        box-shadow: 0 0 15px rgba(59, 130, 246, 0.15);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 18px;
    }
    .hook-badge {
        background: linear-gradient(90deg, #ec4899, #f43f5e);
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 12px;
        display: inline-block;
        margin-bottom: 8px;
    }
    .title-text {
        font-weight: 700;
        font-size: 16px;
        color: #f8fafc;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ AutoShorts Studio (Powder.gg & OpusClip Edition)")
st.caption("100% Free & Local AI Platform with Interactive Visual Facecam & Gameplay Alignment")

# Session state initialization
if "video_path" not in st.session_state:
    st.session_state["video_path"] = None
if "preview_frame" not in st.session_state:
    st.session_state["preview_frame"] = None
if "video_meta" not in st.session_state:
    st.session_state["video_meta"] = {"width": 1920, "height": 1080}
if "results" not in st.session_state:
    st.session_state["results"] = []

# Step status tracker
step_num = 1
if st.session_state["video_path"] and st.session_state["preview_frame"]:
    step_num = 2
if st.session_state["results"]:
    step_num = 3

s1_cls = "step-active" if step_num == 1 else "step-idle"
s2_cls = "step-active" if step_num == 2 else "step-idle"
s3_cls = "step-active" if step_num == 3 else "step-idle"

st.markdown(f"""
<div class="step-banner">
    <div class="step-pill {s1_cls}">1. Ingest Video</div>
    <div style="color: #475569;">━━━━━</div>
    <div class="step-pill {s2_cls}">2. Visual Crop Alignment (Powder.gg)</div>
    <div style="color: #475569;">━━━━━</div>
    <div class="step-pill {s3_cls}">3. AI Shorts Studio</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# STEP 1: INGEST VIDEO
# ==========================================
with st.container():
    st.markdown("### 📥 Step 1: Load Video")
    tab_url, tab_upload = st.tabs(["🔗 Paste YouTube URL", "📁 Upload Local Video File"])
    
    selected_source = None
    is_yt = False

    with tab_url:
        yt_input = st.text_input("YouTube Video URL", placeholder="https://www.youtube.com/watch?v=...", key="yt_in")
        if yt_input:
            selected_source = yt_input
            is_yt = True

    with tab_upload:
        file_input = st.file_uploader("Upload video file (MP4, MKV, MOV, WebM)", type=["mp4", "mov", "mkv", "webm"], key="file_in")
        if file_input:
            upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage", "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            local_target = os.path.join(upload_dir, file_input.name)
            with open(local_target, "wb") as f:
                f.write(file_input.getbuffer())
            selected_source = local_target
            is_yt = False

    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        if st.button("📥 Load & Extract Preview", type="primary", use_container_width=True):
            if not selected_source:
                st.error("Please enter a YouTube link or upload a video file first!")
            else:
                with st.spinner("Downloading/Loading video in Full HD and extracting frame..."):
                    try:
                        upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage", "uploads")
                        if is_yt:
                            v_path = download_youtube_video(selected_source, upload_dir)
                        else:
                            v_path = selected_source

                        st.session_state["video_path"] = v_path
                        meta = get_video_info(v_path)
                        st.session_state["video_meta"] = meta

                        # Extract frame at 10s (or 20% duration)
                        cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage", "cache")
                        v_base = os.path.splitext(os.path.basename(v_path))[0]
                        frame_path = os.path.join(cache_dir, f"{v_base}_preview.jpg")
                        extract_preview_frame(v_path, frame_path, timestamp=10.0)
                        st.session_state["preview_frame"] = frame_path
                        st.session_state["is_youtube"] = is_yt

                        st.success(f"Video Loaded: {meta['width']}x{meta['height']} ({meta['duration']:.1f}s)")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error loading video: {e}")

    with col_info:
        if st.session_state["video_path"]:
            v_m = st.session_state["video_meta"]
            st.info(f"Loaded: `{os.path.basename(st.session_state['video_path'])}` | Resolution: **{v_m['width']}x{v_m['height']}** | GPU NVENC Ready")

st.markdown("---")

# ==========================================
# STEP 2: VISUAL ALIGNMENT & POWDER.GG CONTROLS
# ==========================================
if st.session_state["video_path"] and st.session_state["preview_frame"]:
    st.markdown("### 🎯 Step 2: Choose Layout & Align Crop Windows")
    st.caption("Inspect your ACTUAL video frame below and choose exactly what goes into your 9:16 Short.")

    layout_col, settings_col = st.columns([1, 1])

    with layout_col:
        layout_choice = st.radio(
            "📐 Select Screen Layout Style:",
            [
                "🎮 Powder.gg Gaming Split (Facecam on Top + Gameplay on Bottom)",
                "📱 Single Screen 9:16 (Full Portrait Crop)",
                "🎬 Cinematic Blur Fit (Original 16:9 with Blurred Background)"
            ],
            index=0
        )

    with settings_col:
        theme_choice = st.selectbox(
            "🎨 Viral Caption Theme",
            ["Hormozi Gold (Viral)", "MrBeast Hype", "Neon Cyberpunk", "Emerald Mint", "Clean Minimalist"],
            index=0
        )
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            enable_emojis = st.checkbox("✨ Auto-Emojis (💰 🔥 🏆)", value=True)
            num_clips = st.slider("Clips Count", 1, 5, 3)
        with col_c2:
            dur_range = st.slider("Duration (s)", 15, 90, (20, 60), step=5)

    v_w = st.session_state["video_meta"]["width"]
    v_h = st.session_state["video_meta"]["height"]

    gaming_config = None
    single_crop_config = None
    layout_mode_arg = "crop"

    # Case A: Powder.gg Gaming Split Screen
    if "Gaming Split" in layout_choice:
        layout_mode_arg = "gaming_split"
        st.markdown("""
        <div class="glass-card-accent">
            <h4 style="margin: 0; color: #60a5fa;">🎮 Powder.gg Gaming Alignment Controls</h4>
            <p style="color: #94a3b8; font-size: 13px; margin: 5px 0 12px 0;">
                Adjust the <b style="color: #00ff78;">Green Box (Facecam)</b> and <b style="color: #00d2ff;">Cyan Box (Gameplay)</b> on your real video screenshot.
            </p>
        </div>
        """, unsafe_allow_html=True)

        preset_col, fine_tune = st.columns([1, 2])
        with preset_col:
            streamer_preset = st.selectbox(
                "🎛️ Streamer Preset",
                [
                    "Center-Top Facecam (Like Spyki Plays)",
                    "Top-Right Facecam (Scout, Mortal, Dynamo)",
                    "Top-Left Facecam",
                    "Bottom-Right Facecam",
                    "Bottom-Left Facecam",
                    "Custom Manual Sliders"
                ],
                index=0
            )

        presets = {
            "Center-Top Facecam (Like Spyki Plays)": {"fc_x": 28, "fc_y": 15, "fc_w": 44, "fc_h": 45, "gp_x": 15, "gp_y": 0, "gp_w": 70, "gp_h": 100},
            "Top-Right Facecam (Scout, Mortal, Dynamo)": {"fc_x": 65, "fc_y": 5, "fc_w": 32, "fc_h": 40, "gp_x": 15, "gp_y": 0, "gp_w": 70, "gp_h": 100},
            "Top-Left Facecam": {"fc_x": 5, "fc_y": 5, "fc_w": 32, "fc_h": 40, "gp_x": 15, "gp_y": 0, "gp_w": 70, "gp_h": 100},
            "Bottom-Right Facecam": {"fc_x": 65, "fc_y": 55, "fc_w": 32, "fc_h": 40, "gp_x": 15, "gp_y": 0, "gp_w": 70, "gp_h": 100},
            "Bottom-Left Facecam": {"fc_x": 5, "fc_y": 55, "fc_w": 32, "fc_h": 40, "gp_x": 15, "gp_y": 0, "gp_w": 70, "gp_h": 100},
            "Custom Manual Sliders": {"fc_x": 30, "fc_y": 10, "fc_w": 40, "fc_h": 40, "gp_x": 15, "gp_y": 0, "gp_w": 70, "gp_h": 100}
        }
        cur_p = presets[streamer_preset]

        with fine_tune:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.markdown("<b style='color: #00ff78;'>📷 Facecam Box (Top 40%)</b>", unsafe_allow_html=True)
                fc_x = st.slider("Facecam X (%)", 0, 100, cur_p["fc_x"], key="sl_fc_x")
                fc_y = st.slider("Facecam Y (%)", 0, 100, cur_p["fc_y"], key="sl_fc_y")
                fc_w = st.slider("Facecam Width (%)", 15, 60, cur_p["fc_w"], key="sl_fc_w")
                fc_h = st.slider("Facecam Height (%)", 15, 60, cur_p["fc_h"], key="sl_fc_h")

            with col_f2:
                st.markdown("<b style='color: #00d2ff;'>🎯 Gameplay Box (Bottom 60%)</b>", unsafe_allow_html=True)
                gp_x = st.slider("Gameplay Center X (%)", 0, 100, cur_p["gp_x"], key="sl_gp_x")
                gp_y = st.slider("Gameplay Vertical Y (%)", 0, 100, cur_p["gp_y"], key="sl_gp_y")
                gp_w = st.slider("Gameplay Width (%)", 40, 100, cur_p["gp_w"], key="sl_gp_w")
                gp_h = st.slider("Gameplay Height (%)", 40, 100, cur_p["gp_h"], key="sl_gp_h")

        # Compute Pixel Coordinates
        fc_px = int((fc_x / 100.0) * v_w)
        fc_py = int((fc_y / 100.0) * v_h)
        fc_pw = int((fc_w / 100.0) * v_w)
        fc_ph = int((fc_h / 100.0) * v_h)

        gp_px = int((gp_x / 100.0) * v_w)
        gp_py = int((gp_y / 100.0) * v_h)
        gp_pw = int((gp_w / 100.0) * v_w)
        gp_ph = int((gp_h / 100.0) * v_h)

        if fc_px % 2 != 0: fc_px += 1
        if fc_py % 2 != 0: fc_py += 1
        if fc_pw % 2 != 0: fc_pw += 1
        if fc_ph % 2 != 0: fc_ph += 1

        if gp_px % 2 != 0: gp_px += 1
        if gp_py % 2 != 0: gp_py += 1
        if gp_pw % 2 != 0: gp_pw += 1
        if gp_ph % 2 != 0: gp_ph += 1

        gaming_config = {
            "facecam": {"x": fc_px, "y": fc_py, "w": fc_pw, "h": fc_ph},
            "gameplay": {"x": gp_px, "y": gp_py, "w": gp_pw, "h": gp_ph},
            "top_height": 760
        }

        # Draw Live Boxes on the ACTUAL Video Screenshot
        if os.path.exists(st.session_state["preview_frame"]):
            actual_img = Image.open(st.session_state["preview_frame"]).convert("RGB")
            draw = ImageDraw.Draw(actual_img)
            # Draw Gameplay Box (Cyan)
            draw.rectangle([gp_px, gp_py, gp_px + gp_pw, gp_py + gp_ph], outline=(0, 210, 255), width=6)
            draw.text((gp_px + 15, gp_py + 15), "TARGET GAMEPLAY AREA (Bottom 60%)", fill=(0, 210, 255))
            # Draw Facecam Box (Neon Green)
            draw.rectangle([fc_px, fc_py, fc_px + fc_pw, fc_py + fc_ph], outline=(0, 255, 120), width=6)
            draw.text((fc_px + 15, fc_py + 15), "FACECAM AREA (Top 40%)", fill=(0, 255, 120))

            st.image(actual_img, caption="Live Powder.gg Interactive Video Alignment Map", use_container_width=True)

    # Case B: Single Screen 9:16
    elif "Single Screen" in layout_choice:
        layout_mode_arg = "crop"
        st.markdown("""
        <div class="glass-card-accent">
            <h4 style="margin: 0; color: #eab308;">📱 Single Screen Portrait Options</h4>
            <p style="color: #94a3b8; font-size: 13px; margin: 5px 0 12px 0;">
                Choose whether you want AI face-tracking or a manual/center crop window.
            </p>
        </div>
        """, unsafe_allow_html=True)

        sc_col1, sc_col2 = st.columns([1, 2])
        with sc_col1:
            single_mode = st.radio(
                "Facecam / Speaker Tracking:",
                ["Yes, Auto-Track Speaker Face", "No Facecam (Custom / Center Gameplay Crop)"],
                index=0
            )

        crop_w_target = int(v_h * 9 / 16)
        if crop_w_target % 2 != 0: crop_w_target += 1

        with sc_col2:
            if "No Facecam" in single_mode:
                st.markdown("<b style='color: #eab308;'>🟡 9:16 Vertical Window Position</b>", unsafe_allow_html=True)
                horiz_pct = st.slider("Horizontal Screen Position (%)", 0, 100, 50, help="50% is exact center crop.")
                max_x = v_w - crop_w_target
                target_crop_x = int((horiz_pct / 100.0) * max_x)
                if target_crop_x % 2 != 0: target_crop_x += 1
                single_crop_config = {"mode": "custom", "crop_x": target_crop_x}

                if os.path.exists(st.session_state["preview_frame"]):
                    actual_img = Image.open(st.session_state["preview_frame"]).convert("RGB")
                    draw = ImageDraw.Draw(actual_img)
                    draw.rectangle([target_crop_x, 0, target_crop_x + crop_w_target, v_h], outline=(255, 230, 0), width=6)
                    draw.text((target_crop_x + 15, 25), "9:16 SHORT CROP WINDOW", fill=(255, 230, 0))
                    st.image(actual_img, caption="Live 9:16 Vertical Crop Alignment Map", use_container_width=True)
            else:
                single_crop_config = {"mode": "auto_face"}
                st.info("AI will track speaker faces smoothly in each clip and center the camera on them.")

    # Case C: Cinematic Blur Fit
    else:
        layout_mode_arg = "blur_fit"
        st.markdown("""
        <div class="glass-card-accent">
            <h4 style="margin: 0; color: #ec4899;">🎬 Cinematic Blur Fit Mode</h4>
            <p style="color: #94a3b8; font-size: 13px; margin: 5px 0 12px 0;">
                Full 16:9 widescreen video stays crisp in center with aesthetic blurred ambient background bars on top and bottom. Zero parts of your screen are cut off!
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ==========================================
    # ACTION: GENERATE SHORTS
    # ==========================================
    if st.button("🚀 Generate Shorts with Verified Alignment", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_box = st.empty()

        def on_progress(title, pct, msg):
            progress_bar.progress(int(pct))
            status_box.markdown(f"**{title} ({pct:.0f}%):** {msg}")

        try:
            from pipeline import ShortsPipeline
            pipeline = ShortsPipeline()

            with st.spinner("Generating viral shorts with verified crop alignment..."):
                results = pipeline.process(
                    video_source=st.session_state["video_path"],
                    is_youtube=False, # already downloaded locally
                    num_clips=num_clips,
                    min_duration=dur_range[0],
                    max_duration=dur_range[1],
                    subtitle_theme=theme_choice,
                    enable_emojis=enable_emojis,
                    layout_mode=layout_mode_arg,
                    gaming_config=gaming_config,
                    single_crop_config=single_crop_config,
                    progress_callback=on_progress
                )

            st.session_state["results"] = results
            st.session_state["pipeline"] = pipeline
            st.session_state["active_layout"] = layout_mode_arg
            st.session_state["active_gaming_config"] = gaming_config
            st.session_state["active_single_config"] = single_crop_config
            st.balloons()
            st.success(f"🎉 Generated {len(results)} Shorts with Exact Alignment!")
            st.rerun()

        except Exception as e:
            st.error(f"Error during generation: {e}")
            st.exception(e)

# ==========================================
# STEP 3: SHORTS GALLERY & IN-BROWSER TRIM EDITOR
# ==========================================
if st.session_state.get("results"):
    results = st.session_state["results"]
    st.markdown("### 📱 Step 3: Generated 9:16 Shorts")
    cols = st.columns(len(results))

    for i, clip in enumerate(results):
        with cols[i]:
            st.markdown(f"""
            <div class="glass-card">
                <span class="hook-badge">🔥 Hook Score: {clip['hook_score']}/10</span>
                <div class="title-text">{clip['title']}</div>
                <p style="color: #94a3b8; font-size: 13px; margin-top: 5px;">
                    ⏱️ {clip['duration']}s | Range: {clip['start']}s - {clip['end']}s
                </p>
                <p style="font-size: 12px; color: #cbd5e1;"><i>"{clip['reason']}"</i></p>
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
                        key=f"dl_gal_{i}",
                        use_container_width=True
                    )

            # In-Browser Quick Trim Editor
            with st.expander(f"✂️ Fine-Tune Short #{clip['clip_number']}"):
                col_s, col_e = st.columns(2)
                with col_s:
                    new_start = st.number_input("Start (s)", value=float(clip["start"]), step=1.0, key=f"t_s_{i}")
                with col_e:
                    new_end = st.number_input("End (s)", value=float(clip["end"]), step=1.0, key=f"t_e_{i}")

                if st.button(f"⚡ Re-render #{clip['clip_number']}", key=f"re_btn_{i}"):
                    if new_end <= new_start:
                        st.error("End must be greater than start!")
                    else:
                        with st.spinner("Re-rendering with GPU NVENC..."):
                            from core.transcriber import AudioTranscriber
                            from core.audio import get_video_info
                            p = st.session_state.get("pipeline")
                            if not p:
                                from pipeline import ShortsPipeline
                                p = ShortsPipeline()

                            src_vid = clip.get("source_video_path", clip["video_path"])
                            v_name = clip.get("video_filename", os.path.splitext(os.path.basename(src_vid))[0])
                            
                            ass_file = os.path.join(p.cache_dir, f"re_clip_{clip['clip_number']}.ass")
                            cache_file = os.path.join(p.cache_dir, f"{v_name}_transcript.json")
                            t_data = AudioTranscriber.load_cache(cache_file)
                            segs = t_data.get("segments", []) if t_data else []
                            
                            p.subtitle_engine.generate_ass(segs, new_start, new_end, ass_file)
                            
                            active_layout = st.session_state.get("active_layout", "crop")
                            if active_layout == "gaming_split":
                                crop_info = st.session_state.get("active_gaming_config", {})
                            elif active_layout == "crop":
                                sc_cfg = st.session_state.get("active_single_config")
                                if sc_cfg and sc_cfg.get("mode") == "custom":
                                    crop_w = int(v_h * 9 / 16)
                                    crop_info = {"crop_w": crop_w, "crop_h": v_h, "crop_x": sc_cfg.get("crop_x", 0), "crop_y": 0}
                                else:
                                    crop_info = p.face_tracker.calculate_crop_window(src_vid, new_start, new_end, v_w, v_h)
                            else:
                                crop_info = {}

                            new_out = os.path.join(p.outputs_dir, f"Edited_Short_{clip['clip_number']}.mp4")
                            rendered = p.renderer.render_short(
                                src_vid,
                                new_start,
                                new_end,
                                crop_info,
                                ass_file,
                                new_out,
                                layout_mode=active_layout
                            )
                            clip["video_path"] = rendered
                            clip["start"] = new_start
                            clip["end"] = new_end
                            clip["duration"] = round(new_end - new_start, 1)
                            st.success("Re-rendered successfully!")
                            st.rerun()
