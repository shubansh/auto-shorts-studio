import os
import sys
import json
import logging
from PIL import Image, ImageDraw

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
from core.audio import extract_preview_frame, extract_timeline_thumbnails, get_video_info, download_youtube_video

# -------------------------------------------------------------
# STREAMLIT PAGE CONFIG (POWDER.GG AESTHETIC)
# -------------------------------------------------------------
st.set_page_config(
    page_title="POWDER Studio AI - Gaming & Viral Shorts",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# HIGH-FIDELITY POWDER.GG CUSTOM CSS
# -------------------------------------------------------------
st.markdown("""
<style>
    /* Dark Gaming Theme Palette */
    :root {
        --powder-bg: #0c0d12;
        --powder-card: #131622;
        --powder-card-hover: #1a1e2e;
        --powder-border: #1e2436;
        --powder-neon: #ccff00;
        --powder-neon-hover: #b3e600;
        --powder-purple: #8b5cf6;
        --powder-red: #ef4444;
        --powder-cyan: #00d2ff;
        --powder-text: #f1f5f9;
        --powder-muted: #94a3b8;
    }

    .stApp {
        background-color: var(--powder-bg) !important;
        color: var(--powder-text) !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
    }

    /* Left Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #08090d !important;
        border-right: 1px solid var(--powder-border) !important;
    }

    .powder-logo-wrap {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 0 20px 0;
        border-bottom: 1px solid var(--powder-border);
        margin-bottom: 20px;
    }

    .powder-logo-badge {
        background: var(--powder-neon);
        color: #000;
        font-weight: 900;
        font-size: 20px;
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
    }

    .powder-logo-title {
        font-size: 22px;
        font-weight: 800;
        letter-spacing: 1.5px;
        color: #ffffff;
        margin: 0;
    }

    .sidebar-section-title {
        color: var(--powder-muted);
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        margin: 15px 0 8px 0;
    }

    /* Top Studio Header */
    .studio-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0 16px 0;
        border-bottom: 1px solid var(--powder-border);
        margin-bottom: 16px;
    }

    .studio-title-box {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .video-title {
        font-size: 20px;
        font-weight: 700;
        color: #ffffff;
        margin: 0;
    }

    .gpu-badge {
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.4);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    /* Powder.gg Cards */
    .powder-card {
        background: var(--powder-card);
        border: 1px solid var(--powder-border);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        transition: all 0.2s ease;
    }
    .powder-card:hover {
        border-color: #2e374f;
        background: var(--powder-card-hover);
    }

    .clip-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }

    .virality-score {
        background: rgba(204, 255, 0, 0.15);
        color: var(--powder-neon);
        font-weight: 800;
        font-size: 13px;
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid rgba(204, 255, 0, 0.3);
    }

    .event-tag {
        background: #1c2132;
        color: #cbd5e1;
        font-size: 11px;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 14px;
        display: inline-block;
        margin-right: 4px;
        margin-bottom: 4px;
        border: 1px solid #2d354d;
    }

    .event-tag-purple {
        background: rgba(139, 92, 246, 0.15);
        color: #c4b5fd;
        border: 1px solid rgba(139, 92, 246, 0.4);
    }

    /* Import Source Dropzone (Image 2) */
    .dropzone-box {
        background: #111420;
        border: 2px dashed #2a334a;
        border-radius: 16px;
        padding: 40px 20px;
        text-align: center;
        margin-bottom: 24px;
        transition: border 0.3s;
    }
    .dropzone-box:hover {
        border-color: var(--powder-neon);
    }

    /* Layout Editor Drawer */
    .layout-drawer {
        background: #131726;
        border: 1px solid #2a334d;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
    }

    /* Filmstrip Timeline Container */
    .timeline-container {
        display: flex;
        gap: 6px;
        overflow-x: auto;
        padding: 8px;
        background: #090a0f;
        border-radius: 8px;
        border: 1px solid #1a1e2b;
        margin: 10px 0;
    }
    .timeline-thumb {
        border-radius: 4px;
        border: 1px solid #262b3d;
        height: 60px;
        width: 106px;
        object-fit: cover;
    }

    /* Neon Action Buttons */
    .stButton>button[kind="primary"] {
        background-color: var(--powder-neon) !important;
        color: #000000 !important;
        font-weight: 800 !important;
        font-size: 15px !important;
        border-radius: 24px !important;
        border: none !important;
        padding: 10px 24px !important;
        box-shadow: 0 4px 16px rgba(204, 255, 0, 0.25) !important;
        transition: transform 0.15s, background-color 0.15s !important;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: var(--powder-neon-hover) !important;
        transform: translateY(-1px) !important;
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #10131d;
        border-radius: 8px;
        padding: 4px;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94a3b8 !important;
        font-weight: 600;
        border-radius: 6px;
        padding: 6px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f2538 !important;
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -------------------------------------------------------------
if "current_nav" not in st.session_state:
    st.session_state["current_nav"] = "Studio"
if "video_path" not in st.session_state:
    st.session_state["video_path"] = None
if "preview_frame" not in st.session_state:
    st.session_state["preview_frame"] = None
if "timeline_thumbs" not in st.session_state:
    st.session_state["timeline_thumbs"] = []
if "video_meta" not in st.session_state:
    st.session_state["video_meta"] = {"width": 1920, "height": 1080, "duration": 0.0}
if "discovered_clips" not in st.session_state:
    st.session_state["discovered_clips"] = []
if "selected_clip_indices" not in st.session_state:
    st.session_state["selected_clip_indices"] = []
if "results" not in st.session_state:
    st.session_state["results"] = []
if "show_layout_editor" not in st.session_state:
    st.session_state["show_layout_editor"] = False

# -------------------------------------------------------------
# HELPER: GENERATE REALTIME 9:16 MOBILE MOCKUP
# -------------------------------------------------------------
def generate_mobile_preview(frame_path: str, gaming_config: dict, target_w: int = 320, target_h: int = 568) -> Image.Image:
    """
    Simulates the exact 9:16 mobile output by cropping the user's facecam box
    and gameplay box, stacking them, and adding a subtle preview overlay.
    """
    if not frame_path or not os.path.exists(frame_path):
        return None
    try:
        raw_img = Image.open(frame_path).convert("RGB")
        w_orig, h_orig = raw_img.size

        fc = gaming_config.get("facecam", {"x": 0, "y": 0, "w": w_orig, "h": int(h_orig * 0.4)})
        gp = gaming_config.get("gameplay", {"x": 0, "y": 0, "w": w_orig, "h": h_orig})

        # Clamp facecam bounds
        fx = max(0, min(w_orig - 20, int(fc["x"])))
        fy = max(0, min(h_orig - 20, int(fc["y"])))
        fw = max(20, min(w_orig - fx, int(fc["w"])))
        fh = max(20, min(h_orig - fy, int(fc["h"])))
        fc_crop = raw_img.crop((fx, fy, fx + fw, fy + fh))

        # Clamp gameplay bounds
        gx = max(0, min(w_orig - 20, int(gp["x"])))
        gy = max(0, min(h_orig - 20, int(gp["y"])))
        gw = max(20, min(w_orig - gx, int(gp["w"])))
        gh = max(20, min(h_orig - gy, int(gp["h"])))
        gp_crop = raw_img.crop((gx, gy, gx + gw, gy + gh))

        # 40% top for Facecam, 60% bottom for Gameplay
        top_h = int(target_h * 0.40)
        bot_h = target_h - top_h

        fc_scaled = fc_crop.resize((target_w, top_h), Image.Resampling.LANCZOS)
        gp_scaled = gp_crop.resize((target_w, bot_h), Image.Resampling.LANCZOS)

        canvas = Image.new("RGB", (target_w, target_h), (12, 13, 18))
        canvas.paste(fc_scaled, (0, 0))
        canvas.paste(gp_scaled, (0, top_h))

        draw = ImageDraw.Draw(canvas)
        # Separator line
        draw.line([(0, top_h), (target_w, top_h)], fill=(204, 255, 0), width=3)
        # Sample Subtitle badge
        sub_y = target_h - 100
        draw.rectangle([target_w // 2 - 100, sub_y, target_w // 2 + 100, sub_y + 32], fill=(0, 0, 0), outline=(204, 255, 0), width=2)
        draw.text((target_w // 2 - 72, sub_y + 7), "VIRAL KARAOKE 🔥", fill=(255, 255, 0))

        return canvas
    except Exception as e:
        logging.error(f"Failed to generate mobile preview: {e}")
        return None

# -------------------------------------------------------------
# SIDEBAR NAVIGATION (POWDER.GG DESIGN)
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div class="powder-logo-wrap">
        <div class="powder-logo-badge">P</div>
        <div class="powder-logo-title">POWDER</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section-title">Library</div>', unsafe_allow_html=True)
    nav_selection = st.radio(
        "Navigation",
        ["📁 Sources", "✂️ Studio", "🎬 Highlights", "⚙️ Settings & GPU"],
        index=1 if st.session_state["video_path"] else 0,
        label_visibility="collapsed"
    )
    # Parse navigation
    if "Sources" in nav_selection:
        nav_clean = "Sources"
    elif "Studio" in nav_selection:
        nav_clean = "Studio"
    elif "Highlights" in nav_selection:
        nav_clean = "Highlights"
    else:
        nav_clean = "Settings"
    st.session_state["current_nav"] = nav_clean

    st.markdown('<div class="sidebar-section-title">System Status</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="background: #111420; border: 1px solid #1e2436; border-radius: 8px; padding: 10px; margin-bottom: 12px;">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
            <div style="width: 8px; height: 8px; border-radius: 50%; background: #22c55e;"></div>
            <span style="font-weight: 700; font-size: 12px; color: #f8fafc;">RTX 3050 NVENC</span>
        </div>
        <div style="font-size: 11px; color: #94a3b8;">GPU 60 FPS Acceleration Active</div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state["video_path"]:
        v_meta = st.session_state["video_meta"]
        st.markdown(f"""
        <div style="background: #111420; border: 1px solid #1e2436; border-radius: 8px; padding: 10px;">
            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">Active Project</div>
            <div style="font-size: 12px; font-weight: 600; color: #e2e8f0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                {os.path.basename(st.session_state['video_path'])}
            </div>
            <div style="font-size: 11px; color: #64748b; margin-top: 4px;">
                {v_meta.get('width', 1920)}x{v_meta.get('height', 1080)} • {v_meta.get('duration', 0):.0f}s
            </div>
        </div>
        """, unsafe_allow_html=True)

# -------------------------------------------------------------
# VIEW 1: SOURCES / INGESTION (REFERENCE IMAGE 2)
# -------------------------------------------------------------
if st.session_state["current_nav"] == "Sources":
    st.markdown('<div class="studio-header"><h2 class="video-title">📁 Import Sources</h2><div class="gpu-badge">● GPU Ready</div></div>', unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1, 4, 1])
    with col_center:
        st.markdown("""
        <div style="display: flex; gap: 12px; justify-content: center; margin-bottom: 24px;">
            <button style="background: #7c3aed; color: white; border: none; padding: 10px 20px; border-radius: 20px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 8px; cursor: pointer;">
                🟣 Connect Twitch
            </button>
            <button style="background: #ef4444; color: white; border: none; padding: 10px 20px; border-radius: 20px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 8px; cursor: pointer;">
                🔴 Connect YouTube
            </button>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="dropzone-box">
            <div style="font-size: 40px; margin-bottom: 12px;">📂</div>
            <h3 style="margin: 0 0 6px 0; color: #f8fafc; font-size: 18px;">Drag or click to browse your MP4 file</h3>
            <p style="color: #94a3b8; font-size: 13px; margin: 0 0 16px 0;">We'll quickly create exciting clips from your best gaming moments</p>
        </div>
        """, unsafe_allow_html=True)

        uploaded_file = st.file_uploader("Upload MP4 File", type=["mp4", "mov", "mkv", "webm"], label_visibility="collapsed")
        
        st.markdown('<div style="text-align: center; color: #64748b; margin: 16px 0; font-size: 13px; font-weight: 600;">― or Link Import ―</div>', unsafe_allow_html=True)

        yt_col, btn_col = st.columns([4, 1])
        with yt_col:
            yt_url = st.text_input("Paste YouTube / Stream Link", placeholder="https://www.youtube.com/watch?v=...", label_visibility="collapsed")
        with btn_col:
            import_btn = st.button("⚡ Ingest", type="primary", use_container_width=True)

        # Existing Local Videos Library
        upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        existing_files = [f for f in os.listdir(upload_dir) if f.lower().endswith((".mp4", ".mov", ".mkv", ".webm")) and not f.endswith(".part")]
        
        if existing_files:
            st.markdown('<div style="margin-top: 30px; font-size: 14px; font-weight: 700; color: #cbd5e1;">Available Local Recordings</div>', unsafe_allow_html=True)
            chosen_local = st.selectbox("Select existing recording:", existing_files, label_visibility="collapsed")
            if st.button("🎬 Open in Studio", use_container_width=True):
                target_path = os.path.join(upload_dir, chosen_local)
                with st.spinner("Loading video metadata & timeline..."):
                    st.session_state["video_path"] = target_path
                    meta = get_video_info(target_path)
                    st.session_state["video_meta"] = meta
                    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage", "cache")
                    v_base = os.path.splitext(chosen_local)[0]
                    p_frame = os.path.join(cache_dir, f"{v_base}_preview.jpg")
                    extract_preview_frame(target_path, p_frame, timestamp=10.0)
                    st.session_state["preview_frame"] = p_frame
                    st.session_state["timeline_thumbs"] = extract_timeline_thumbnails(target_path, cache_dir, meta["duration"], count=6)
                    st.session_state["current_nav"] = "Studio"
                    st.rerun()

        # Handle Action
        if import_btn or uploaded_file:
            target_path = None
            if uploaded_file:
                target_path = os.path.join(upload_dir, uploaded_file.name)
                with open(target_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            elif yt_url:
                with st.spinner("Downloading YouTube video in Full HD (1080p)..."):
                    try:
                        target_path = download_youtube_video(yt_url, upload_dir)
                    except Exception as e:
                        st.error(f"Download failed: {e}")

            if target_path and os.path.exists(target_path):
                with st.spinner("Extracting timeline keyframes & preview snapshot..."):
                    st.session_state["video_path"] = target_path
                    meta = get_video_info(target_path)
                    st.session_state["video_meta"] = meta
                    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage", "cache")
                    v_base = os.path.splitext(os.path.basename(target_path))[0]
                    p_frame = os.path.join(cache_dir, f"{v_base}_preview.jpg")
                    extract_preview_frame(target_path, p_frame, timestamp=10.0)
                    st.session_state["preview_frame"] = p_frame
                    st.session_state["timeline_thumbs"] = extract_timeline_thumbnails(target_path, cache_dir, meta["duration"], count=6)
                    st.session_state["discovered_clips"] = []
                    st.session_state["selected_clip_indices"] = []
                    st.success("Video Ingested! Switching to Studio...")
                    st.session_state["current_nav"] = "Studio"
                    st.rerun()

# -------------------------------------------------------------
# VIEW 2: STUDIO (POWDER.GG WORKSPACE - IMAGES 3 & 4)
# -------------------------------------------------------------
elif st.session_state["current_nav"] == "Studio":
    if not st.session_state["video_path"]:
        st.info("No video loaded yet! Please go to **📁 Sources** to upload or paste a video link.")
    else:
        v_path = st.session_state["video_path"]
        v_name = os.path.basename(v_path)
        v_meta = st.session_state["video_meta"]
        v_w = v_meta.get("width", 1920)
        v_h = v_meta.get("height", 1080)
        v_dur = v_meta.get("duration", 0.0)

        # Powder Top Studio Bar
        st.markdown(f"""
        <div class="studio-header">
            <div class="studio-title-box">
                <span style="color: #64748b; font-size: 18px; cursor: pointer;">←</span>
                <h3 class="video-title">{v_name}</h3>
                <span style="font-size: 13px; color: #94a3b8;">({v_w}x{v_h} • {v_dur:.0f}s)</span>
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
                <div class="gpu-badge">⚡ RTX 3050 NVENC Ready</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 2-Column Powder Workspace Layout
        left_studio, right_studio = st.columns([13, 8], gap="medium")

        # -----------------------------------------------------
        # LEFT COLUMN: PLAYER, CONTROLS & TIMELINE
        # -----------------------------------------------------
        with left_studio:
            # Powder Floating Action Bar over player
            btn_col1, btn_col2, btn_col3 = st.columns([1.2, 1.2, 2.6])
            with btn_col1:
                show_aspect = st.toggle("📱 9:16 Mode", value=True)
            with btn_col2:
                toggle_layout = st.button("🎛️ Edit layout", use_container_width=True)
                if toggle_layout:
                    st.session_state["show_layout_editor"] = not st.session_state["show_layout_editor"]
            with btn_col3:
                theme_choice = st.selectbox(
                    "Captions",
                    ["Hormozi Gold (Viral)", "MrBeast Hype", "Neon Cyberpunk", "Emerald Mint", "Clean Minimalist"],
                    label_visibility="collapsed"
                )

            # Main 16:9 Video Player
            st.video(v_path)

            # Filmstrip Timeline (Powder.gg Keyframe Slider)
            st.markdown('<div style="font-size: 12px; font-weight: 700; color: #94a3b8; margin-top: 8px;">TIMELINE FILMSTRIP</div>', unsafe_allow_html=True)
            thumbs = st.session_state.get("timeline_thumbs", [])
            if thumbs:
                t_cols = st.columns(len(thumbs))
                for idx, t in enumerate(thumbs):
                    with t_cols[idx]:
                        if os.path.exists(t["path"]):
                            st.image(t["path"], caption=f"{int(t['timestamp'])}s", use_container_width=True)
            else:
                st.caption("Keyframes extract automatically on video import.")

            # -------------------------------------------------
            # POWDER.GG EDIT LAYOUT DRAWER (CRUCIAL REQUEST)
            # -------------------------------------------------
            if st.session_state["show_layout_editor"]:
                st.markdown("""
                <div class="layout-drawer">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <h4 style="margin: 0; color: #ccff00; font-size: 16px;">🎛️ Powder.gg Interactive Layout Editor</h4>
                        <span style="font-size: 12px; color: #94a3b8;">Adjust Facecam & Gameplay Alignment Live</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                layout_choice = st.radio(
                    "Select Screen Mode:",
                    [
                        "🎮 Gaming Split (Facecam on Top + Gameplay on Bottom)",
                        "📱 Single Screen 9:16 (Full Vertical Crop)",
                        "🎬 Cinematic Blur Fit (Original 16:9 with Ambient Blur)"
                    ],
                    index=0
                )

                active_layout_mode = "crop"
                current_gaming_config = None
                current_single_config = None

                # 1. Gaming Split Controls
                if "Gaming Split" in layout_choice:
                    active_layout_mode = "gaming_split"
                    preset_col, fine_tune_col = st.columns([1, 2])
                    with preset_col:
                        streamer_preset = st.selectbox(
                            "Streamer Layout Preset:",
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
                    p_val = presets[streamer_preset]

                    with fine_tune_col:
                        f1, f2 = st.columns(2)
                        with f1:
                            st.markdown("<b style='color: #00ff78;'>📷 Facecam Box (Top 40%)</b>", unsafe_allow_html=True)
                            fc_x = st.slider("Facecam X (%)", 0, 100, p_val["fc_x"], key="s_fc_x")
                            fc_y = st.slider("Facecam Y (%)", 0, 100, p_val["fc_y"], key="s_fc_y")
                            fc_w = st.slider("Facecam Width (%)", 15, 70, p_val["fc_w"], key="s_fc_w")
                            fc_h = st.slider("Facecam Height (%)", 15, 70, p_val["fc_h"], key="s_fc_h")
                        with f2:
                            st.markdown("<b style='color: #00d2ff;'>🎯 Gameplay Box (Bottom 60%)</b>", unsafe_allow_html=True)
                            gp_x = st.slider("Gameplay X (%)", 0, 100, p_val["gp_x"], key="s_gp_x")
                            gp_y = st.slider("Gameplay Y (%)", 0, 100, p_val["gp_y"], key="s_gp_y")
                            gp_w = st.slider("Gameplay Width (%)", 30, 100, p_val["gp_w"], key="s_gp_w")
                            gp_h = st.slider("Gameplay Height (%)", 30, 100, p_val["gp_h"], key="s_gp_h")

                    # Calculate pixel coordinates
                    fc_px = int((fc_x / 100.0) * v_w)
                    fc_py = int((fc_y / 100.0) * v_h)
                    fc_pw = int((fc_w / 100.0) * v_w)
                    fc_ph = int((fc_h / 100.0) * v_h)

                    gp_px = int((gp_x / 100.0) * v_w)
                    gp_py = int((gp_y / 100.0) * v_h)
                    gp_pw = int((gp_w / 100.0) * v_w)
                    gp_ph = int((gp_h / 100.0) * v_h)

                    current_gaming_config = {
                        "facecam": {"x": fc_px, "y": fc_py, "w": fc_pw, "h": fc_ph},
                        "gameplay": {"x": gp_px, "y": gp_py, "w": gp_pw, "h": gp_ph},
                        "top_height": 760
                    }
                    st.session_state["active_gaming_config"] = current_gaming_config
                    st.session_state["active_layout"] = "gaming_split"

                    # DUAL LIVE VISUAL FEEDBACK: Raw Map + Mobile Result
                    st.markdown('<div style="font-size: 13px; font-weight: 700; color: #cbd5e1; margin: 12px 0 6px 0;">🔴 Live Dual Visual Alignment Feedback</div>', unsafe_allow_html=True)
                    vis1, vis2 = st.columns([3, 2])
                    
                    with vis1:
                        # Raw Video Frame with Bounding Boxes
                        if st.session_state["preview_frame"] and os.path.exists(st.session_state["preview_frame"]):
                            map_img = Image.open(st.session_state["preview_frame"]).convert("RGB")
                            d = ImageDraw.Draw(map_img)
                            # Cyan Gameplay
                            d.rectangle([gp_px, gp_py, gp_px + gp_pw, gp_py + gp_ph], outline=(0, 210, 255), width=6)
                            d.text((gp_px + 15, gp_py + 15), "TARGET GAMEPLAY (Bottom 60%)", fill=(0, 210, 255))
                            # Green Facecam
                            d.rectangle([fc_px, fc_py, fc_px + fc_pw, fc_py + fc_ph], outline=(0, 255, 120), width=6)
                            d.text((fc_px + 15, fc_py + 15), "FACECAM (Top 40%)", fill=(0, 255, 120))
                            st.image(map_img, caption="1. Selection Bounding Boxes on Raw Video", use_container_width=True)

                    with vis2:
                        # Simulated 9:16 Mobile Mockup
                        mob_img = generate_mobile_preview(st.session_state["preview_frame"], current_gaming_config)
                        if mob_img:
                            st.image(mob_img, caption="2. Exact 9:16 Short Preview Before Render", width=220)

                # 2. Single Screen Mode Controls
                elif "Single Screen" in layout_choice:
                    active_layout_mode = "crop"
                    st.session_state["active_layout"] = "crop"
                    sc_col1, sc_col2 = st.columns([1, 2])
                    with sc_col1:
                        single_pref = st.radio(
                            "Speaker Facecam Tracking:",
                            ["Auto-Track Speaker Face (AI)", "No Facecam (Custom / Center Gameplay Crop)"],
                            index=0
                        )

                    crop_w_t = int(v_h * 9 / 16)
                    if crop_w_t % 2 != 0: crop_w_t += 1

                    with sc_col2:
                        if "No Facecam" in single_pref:
                            h_pct = st.slider("Horizontal Screen Position (%)", 0, 100, 50)
                            max_x = v_w - crop_w_t
                            target_x = int((h_pct / 100.0) * max_x)
                            if target_x % 2 != 0: target_x += 1
                            current_single_config = {"mode": "custom", "crop_x": target_x}
                            st.session_state["active_single_config"] = current_single_config

                            if st.session_state["preview_frame"] and os.path.exists(st.session_state["preview_frame"]):
                                s_img = Image.open(st.session_state["preview_frame"]).convert("RGB")
                                d = ImageDraw.Draw(s_img)
                                d.rectangle([target_x, 0, target_x + crop_w_t, v_h], outline=(255, 230, 0), width=6)
                                d.text((target_x + 15, 25), "9:16 SHORT WINDOW", fill=(255, 230, 0))
                                st.image(s_img, caption="Live 9:16 Single Screen Alignment Map", use_container_width=True)
                        else:
                            st.session_state["active_single_config"] = {"mode": "auto_face"}
                            st.info("AI Face-Tracker will automatically center the camera on whoever is speaking.")

                # 3. Blur Fit
                else:
                    active_layout_mode = "blur_fit"
                    st.session_state["active_layout"] = "blur_fit"
                    st.info("Full 16:9 widescreen video centered with ambient blurred background on top and bottom.")

        # -----------------------------------------------------
        # RIGHT COLUMN: SUGGESTED CLIPS & POWDER CARDS (IMAGES 1, 3 & 4)
        # -----------------------------------------------------
        with right_studio:
            st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div style="font-weight: 700; font-size: 15px; color: #f8fafc;">Suggested Moments</div>
                <div style="font-size: 12px; color: var(--powder-neon); font-weight: 600;">⚡ AI Discovery</div>
            </div>
            """, unsafe_allow_html=True)

            # Filter pills (Powder.gg Image 1 style)
            st.markdown("""
            <div style="display: flex; gap: 6px; overflow-x: auto; margin-bottom: 12px;">
                <span class="event-tag event-tag-purple">Clip it (3)</span>
                <span class="event-tag event-tag-purple">Wow (2)</span>
                <span class="event-tag">💀 Kill</span>
                <span class="event-tag">👑 Victory</span>
                <span class="event-tag">😂 Laughter</span>
            </div>
            """, unsafe_allow_html=True)

            # If AI has not discovered clips yet:
            if not st.session_state.get("discovered_clips"):
                st.markdown("""
                <div class="powder-card">
                    <h4 style="margin: 0 0 8px 0; color: #f8fafc; font-size: 15px;">⚡ Auto-Detect Top Highlights</h4>
                    <p style="color: #94a3b8; font-size: 12px; margin-bottom: 14px;">
                        Let Ollama & Faster-Whisper analyze the transcript, speech excitement, and key gaming moments.
                    </p>
                </div>
                """, unsafe_allow_html=True)

                col_num, col_dur = st.columns(2)
                with col_num:
                    num_clips_input = st.slider("Moments Count", 1, 5, 3)
                with col_dur:
                    dur_range = st.slider("Duration (s)", 15, 90, (20, 50), step=5)

                if st.button("⚡ Scan & Discover Clips", type="primary", use_container_width=True):
                    with st.spinner("Transcribing audio & finding viral moments with AI..."):
                        try:
                            from pipeline import ShortsPipeline
                            from core.audio import extract_audio
                            from core.transcriber import AudioTranscriber
                            from core.highlight_detector import HighlightDetector

                            p = ShortsPipeline()
                            v_base = os.path.splitext(v_name)[0]
                            audio_file = os.path.join(p.audio_dir, f"{v_base}.wav")
                            if not os.path.exists(audio_file):
                                extract_audio(v_path, audio_file)

                            cache_file = os.path.join(p.cache_dir, f"{v_base}_transcript.json")
                            t_data = AudioTranscriber.load_cache(cache_file)
                            if not t_data:
                                p.transcriber = AudioTranscriber(model_size=p.whisper_model_name)
                                t_data = p.transcriber.transcribe(audio_file)
                                AudioTranscriber.save_cache(t_data, cache_file)

                            h_detector = HighlightDetector(model_name=p.ollama_model_name)
                            clips = h_detector.find_highlights(
                                t_data,
                                num_clips=num_clips_input,
                                min_duration=dur_range[0],
                                max_duration=dur_range[1]
                            )

                            st.session_state["discovered_clips"] = clips
                            st.session_state["selected_clip_indices"] = list(range(len(clips)))
                            st.success(f"Discovered {len(clips)} Viral Highlights!")
                            st.rerun()

                        except Exception as e:
                            st.error(f"Discovery error: {e}")

            # Once clips are discovered:
            if st.session_state.get("discovered_clips"):
                clips = st.session_state["discovered_clips"]
                selected_idxs = []

                for idx, c in enumerate(clips):
                    dur = int(c["end"] - c["start"])
                    v_score = c.get("virality_score", 92 - (idx * 5))
                    tags = c.get("tags", ["💀 Kill", "🔥 Highlight"])

                    tags_html = "".join([f'<span class="event-tag">{t}</span>' for t in tags])

                    st.markdown(f"""
                    <div class="powder-card">
                        <div class="clip-card-header">
                            <span class="virality-score">⚡ {v_score}</span>
                            <span style="font-size: 12px; color: #94a3b8; font-weight: 600;">{int(c['start'])}s - {int(c['end'])}s ({dur}s)</span>
                        </div>
                        <div style="font-weight: 700; color: #f8fafc; font-size: 14px; margin-bottom: 6px;">
                            {c.get('title', f'Moment #{idx+1}')}
                        </div>
                        <div style="margin-bottom: 8px;">{tags_html}</div>
                        <div style="font-size: 11px; color: #94a3b8; font-style: italic;">"{c.get('reason', '')}"</div>
                    </div>
                    """, unsafe_allow_html=True)

                    is_checked = st.checkbox(f"Include in batch render", value=(idx in st.session_state["selected_clip_indices"]), key=f"chk_clip_{idx}")
                    if is_checked:
                        selected_idxs.append(idx)

                st.session_state["selected_clip_indices"] = selected_idxs

                # BIG NEON BUTTON: CREATE X CLIPS (POWDER.GG DESIGN - IMAGE 3)
                num_to_create = len(selected_idxs)
                st.markdown("<br>", unsafe_allow_html=True)
                create_btn = st.button(
                    f"⚡ CREATE {num_to_create} CLIPS",
                    type="primary",
                    use_container_width=True,
                    disabled=(num_to_create == 0)
                )

                if create_btn:
                    progress_bar = st.progress(0)
                    status_box = st.empty()

                    def on_progress(title, pct, msg):
                        progress_bar.progress(int(pct))
                        status_box.markdown(f"**{title} ({pct:.0f}%):** {msg}")

                    try:
                        from pipeline import ShortsPipeline
                        pipeline = ShortsPipeline()

                        chosen_clips_data = [clips[i] for i in selected_idxs]
                        active_layout = st.session_state.get("active_layout", "gaming_split")
                        gaming_cfg = st.session_state.get("active_gaming_config")
                        single_cfg = st.session_state.get("active_single_config")

                        with st.spinner("Rendering shorts in Full HD with RTX 3050 NVENC..."):
                            results = pipeline.process(
                                video_source=v_path,
                                is_youtube=False,
                                num_clips=len(chosen_clips_data),
                                subtitle_theme=theme_choice,
                                enable_emojis=True,
                                layout_mode=active_layout,
                                gaming_config=gaming_cfg,
                                single_crop_config=single_cfg,
                                preselected_clips=chosen_clips_data,
                                progress_callback=on_progress
                            )

                        st.session_state["results"] = results
                        st.session_state["pipeline"] = pipeline
                        st.balloons()
                        st.success(f"Successfully Created {len(results)} Shorts!")
                        st.session_state["current_nav"] = "Highlights"
                        st.rerun()

                    except Exception as e:
                        st.error(f"Render Error: {e}")
                        st.exception(e)

# -------------------------------------------------------------
# VIEW 3: HIGHLIGHTS (RENDERED SHORTS GALLERY & DOWNLOADS)
# -------------------------------------------------------------
elif st.session_state["current_nav"] == "Highlights":
    st.markdown('<div class="studio-header"><h2 class="video-title">🎬 Rendered Shorts & Highlights</h2><div class="gpu-badge">● Complete</div></div>', unsafe_allow_html=True)

    outputs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "storage", "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    all_shorts = [f for f in os.listdir(outputs_dir) if f.lower().endswith(".mp4") and not f.startswith(".")]

    if not all_shorts and not st.session_state.get("results"):
        st.info("No generated shorts found yet. Head to **✂️ Studio** to create clips from your video!")
    else:
        results = st.session_state.get("results", [])
        
        # If results exist in session
        if results:
            cols = st.columns(len(results) if len(results) <= 3 else 3)
            for i, clip in enumerate(results):
                col_idx = i % 3
                with cols[col_idx]:
                    st.markdown(f"""
                    <div class="powder-card">
                        <div class="clip-card-header">
                            <span class="virality-score">⚡ Virality: {clip.get('virality_score', 92)}</span>
                            <span style="font-size: 12px; color: #94a3b8;">{clip.get('duration', 0)}s</span>
                        </div>
                        <div style="font-weight: 700; color: #f8fafc; font-size: 14px; margin-bottom: 8px;">
                            {clip.get('title', f'Short #{clip["clip_number"]}')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if os.path.exists(clip["video_path"]):
                        with open(clip["video_path"], "rb") as vf:
                            v_bytes = vf.read()
                            st.video(v_bytes)
                            st.download_button(
                                label=f"⬇️ Download Short #{clip['clip_number']}",
                                data=v_bytes,
                                file_name=clip["filename"],
                                mime="video/mp4",
                                key=f"dl_hl_{i}",
                                use_container_width=True
                            )
        else:
            # Fallback to listing stored MP4s
            cols = st.columns(min(3, len(all_shorts)))
            for i, fn in enumerate(all_shorts):
                col_idx = i % 3
                p = os.path.join(outputs_dir, fn)
                with cols[col_idx]:
                    st.markdown(f'<div class="powder-card"><div style="font-weight: 700; color: #f8fafc;">{fn}</div></div>', unsafe_allow_html=True)
                    with open(p, "rb") as vf:
                        v_bytes = vf.read()
                        st.video(v_bytes)
                        st.download_button(
                            label=f"⬇️ Download {fn}",
                            data=v_bytes,
                            file_name=fn,
                            mime="video/mp4",
                            key=f"dl_all_{i}",
                            use_container_width=True
                        )

# -------------------------------------------------------------
# VIEW 4: SETTINGS & GPU MONITOR
# -------------------------------------------------------------
elif st.session_state["current_nav"] == "Settings":
    st.markdown('<div class="studio-header"><h2 class="video-title">⚙️ Settings & Hardware</h2></div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="powder-card">
            <h4 style="margin: 0 0 10px 0; color: #ccff00;">🟢 NVIDIA GeForce RTX 3050</h4>
            <div style="font-size: 13px; color: #cbd5e1; line-height: 1.6;">
                • <b>VRAM:</b> 6GB GDDR6<br>
                • <b>NVENC Video Encoder:</b> Hardware Enabled (Preset P6, High Quality)<br>
                • <b>Render Speed:</b> ~15x faster than CPU realtime<br>
                • <b>Whisper Compute:</b> CUDA 12 (float16)<br>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="powder-card">
            <h4 style="margin: 0 0 10px 0; color: #38bdf8;">🧠 AI Models Configuration</h4>
            <div style="font-size: 13px; color: #cbd5e1; line-height: 1.6;">
                • <b>Speech-to-Text:</b> Faster-Whisper (Small / Multilingual)<br>
                • <b>Highlights Discovery:</b> Ollama (llama3.2:latest)<br>
                • <b>Subtitle Engine:</b> Windows Nirmala UI + Emoji Injection<br>
                • <b>API Cost:</b> $0.00 (100% Free & Local)<br>
            </div>
        </div>
        """, unsafe_allow_html=True)
