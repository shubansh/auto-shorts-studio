import os
import sys
import json
import logging
import socket
import asyncio
from PIL import Image, ImageDraw

# Windows Python 3.13 AsyncIO Fix: Prevent WinError 10054 ConnectionResetError
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass
    try:
        from asyncio.proactor_events import _ProactorBasePipeTransport
        _orig_call_conn_lost = _ProactorBasePipeTransport._call_connection_lost
        def _safe_call_connection_lost(self, exc=None):
            try:
                _orig_call_conn_lost(self, exc)
            except (ConnectionResetError, OSError):
                pass
        _ProactorBasePipeTransport._call_connection_lost = _safe_call_connection_lost
    except Exception:
        pass

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
# STREAMLIT PAGE CONFIGURATION
# -------------------------------------------------------------
st.set_page_config(
    page_title="POWDER Studio AI - Full UI/UX Suite",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# HIGH-FIDELITY POWDER.GG GAMING SAAS CSS
# -------------------------------------------------------------
st.markdown("""
<style>
    :root {
        --bg-main: #0c0d12;
        --bg-sidebar: #08090d;
        --bg-card: #121520;
        --bg-card-hover: #181d2c;
        --border-color: #1e2436;
        --powder-neon: #ccff00;
        --powder-neon-glow: rgba(204, 255, 0, 0.25);
        --accent-purple: #8b5cf6;
        --accent-red: #ef4444;
        --accent-cyan: #00d2ff;
        --text-primary: #f8fafc;
        --text-secondary: #94a3b8;
    }

    .stApp {
        background-color: var(--bg-main) !important;
        color: var(--text-primary) !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    [data-testid="stSidebar"] {
        background-color: var(--bg-sidebar) !important;
        border-right: 1px solid var(--border-color) !important;
    }

    /* Logo Styling */
    .powder-brand {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 6px 0 18px 0;
        border-bottom: 1px solid var(--border-color);
        margin-bottom: 18px;
    }
    .powder-icon {
        background: var(--powder-neon);
        color: #000;
        font-weight: 900;
        font-size: 20px;
        width: 38px;
        height: 38px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        box-shadow: 0 0 12px var(--powder-neon-glow);
    }
    .powder-title {
        font-size: 22px;
        font-weight: 800;
        letter-spacing: 2px;
        color: #ffffff;
        margin: 0;
    }

    /* Section Subheaders */
    .sidebar-heading {
        color: var(--text-secondary);
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        margin: 14px 0 6px 0;
    }

    /* Glass Cards */
    .powder-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 14px;
        transition: transform 0.15s, border-color 0.15s;
    }
    .powder-card:hover {
        border-color: #2a334d;
        background: var(--bg-card-hover);
    }

    /* Metric Stat Badges */
    .stat-box {
        background: #111422;
        border: 1px solid var(--border-color);
        border-radius: 10px;
        padding: 12px 16px;
        text-align: center;
    }
    .stat-number {
        font-size: 24px;
        font-weight: 800;
        color: var(--powder-neon);
        margin: 0;
    }
    .stat-label {
        font-size: 12px;
        color: var(--text-secondary);
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }

    /* Virality & Tag Pills */
    .virality-badge {
        background: rgba(204, 255, 0, 0.15);
        color: var(--powder-neon);
        font-weight: 800;
        font-size: 12px;
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid rgba(204, 255, 0, 0.35);
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }
    .event-tag {
        background: #181d2e;
        color: #cbd5e1;
        font-size: 11px;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 12px;
        display: inline-block;
        margin-right: 4px;
        margin-bottom: 4px;
        border: 1px solid #283147;
    }
    .event-tag-purple {
        background: rgba(139, 92, 246, 0.15);
        color: #c4b5fd;
        border: 1px solid rgba(139, 92, 246, 0.4);
    }

    /* Neon Buttons */
    .stButton>button[kind="primary"] {
        background-color: var(--powder-neon) !important;
        color: #000000 !important;
        font-weight: 800 !important;
        font-size: 14px !important;
        border-radius: 24px !important;
        border: none !important;
        padding: 10px 22px !important;
        box-shadow: 0 4px 14px var(--powder-neon-glow) !important;
        transition: transform 0.15s !important;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: #b3e600 !important;
        transform: translateY(-1px) !important;
    }

    /* Dashed Upload Box */
    .upload-zone {
        background: #111420;
        border: 2px dashed #2a334a;
        border-radius: 16px;
        padding: 36px 20px;
        text-align: center;
        margin-bottom: 20px;
        transition: border-color 0.3s;
    }
    .upload-zone:hover {
        border-color: var(--powder-neon);
    }

    /* Header Bar */
    .top-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 0 16px 0;
        border-bottom: 1px solid var(--border-color);
        margin-bottom: 18px;
    }
    .top-title {
        font-size: 20px;
        font-weight: 700;
        color: #ffffff;
        margin: 0;
    }
    .badge-gpu {
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.35);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -------------------------------------------------------------
if "current_nav" not in st.session_state:
    st.session_state["current_nav"] = "Dashboard"
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
if "active_layout" not in st.session_state:
    st.session_state["active_layout"] = "gaming_split"
if "active_gaming_config" not in st.session_state:
    st.session_state["active_gaming_config"] = None
if "active_single_config" not in st.session_state:
    st.session_state["active_single_config"] = None
if "subtitle_theme" not in st.session_state:
    st.session_state["subtitle_theme"] = "Hormozi Gold (Viral)"
if "enable_emojis" not in st.session_state:
    st.session_state["enable_emojis"] = True
if "results" not in st.session_state:
    st.session_state["results"] = []

# -------------------------------------------------------------
# HELPER: DUAL PREVIEW MOCKUP GENERATOR
# -------------------------------------------------------------
def generate_mobile_preview(frame_path: str, gaming_config: dict, target_w: int = 320, target_h: int = 568) -> Image.Image:
    if not frame_path or not os.path.exists(frame_path):
        return None
    try:
        raw_img = Image.open(frame_path).convert("RGB")
        w_orig, h_orig = raw_img.size

        fc = gaming_config.get("facecam", {"x": 0, "y": 0, "w": w_orig, "h": int(h_orig * 0.4)})
        gp = gaming_config.get("gameplay", {"x": 0, "y": 0, "w": w_orig, "h": h_orig})

        fx = max(0, min(w_orig - 20, int(fc["x"])))
        fy = max(0, min(h_orig - 20, int(fc["y"])))
        fw = max(20, min(w_orig - fx, int(fc["w"])))
        fh = max(20, min(h_orig - fy, int(fc["h"])))
        fc_crop = raw_img.crop((fx, fy, fx + fw, fy + fh))

        gx = max(0, min(w_orig - 20, int(gp["x"])))
        gy = max(0, min(h_orig - 20, int(gp["y"])))
        gw = max(20, min(w_orig - gx, int(gp["w"])))
        gh = max(20, min(h_orig - gy, int(gp["h"])))
        gp_crop = raw_img.crop((gx, gy, gx + gw, gy + gh))

        top_h = int(target_h * 0.40)
        bot_h = target_h - top_h

        fc_scaled = fc_crop.resize((target_w, top_h), Image.Resampling.LANCZOS)
        gp_scaled = gp_crop.resize((target_w, bot_h), Image.Resampling.LANCZOS)

        canvas = Image.new("RGB", (target_w, target_h), (12, 13, 18))
        canvas.paste(fc_scaled, (0, 0))
        canvas.paste(gp_scaled, (0, top_h))

        draw = ImageDraw.Draw(canvas)
        draw.line([(0, top_h), (target_w, top_h)], fill=(204, 255, 0), width=3)
        sub_y = target_h - 100
        draw.rectangle([target_w // 2 - 95, sub_y, target_w // 2 + 95, sub_y + 32], fill=(0, 0, 0), outline=(204, 255, 0), width=2)
        draw.text((target_w // 2 - 70, sub_y + 8), "VIRAL KARAOKE 🔥", fill=(255, 255, 0))

        return canvas
    except Exception as e:
        logging.error(f"Failed to generate mobile preview: {e}")
        return None

# -------------------------------------------------------------
# LEFT SIDEBAR NAVIGATION (MATCHING BLUEPRINT FLOW)
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div class="powder-brand">
        <div class="powder-icon">P</div>
        <div class="powder-title">POWDER</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sidebar-heading">Main Product Flow</div>', unsafe_allow_html=True)
    nav_options = [
        "🏠 Dashboard",
        "📥 Capture & Ingest",
        "✂️ Studio & Clips",
        "🎛️ Layout & Templates",
        "🎨 Captions & Styling",
        "📂 Clips Library",
        "⚙️ Settings & GPU"
    ]

    curr_idx = 0
    for i, opt in enumerate(nav_options):
        if st.session_state["current_nav"] in opt:
            curr_idx = i
            break

    selected_nav = st.radio("Navigation", nav_options, index=curr_idx, label_visibility="collapsed")
    
    # Clean nav name
    clean_key = selected_nav.split(" ")[-1]
    if "Dashboard" in selected_nav: st.session_state["current_nav"] = "Dashboard"
    elif "Capture" in selected_nav: st.session_state["current_nav"] = "Capture"
    elif "Studio" in selected_nav: st.session_state["current_nav"] = "Studio"
    elif "Layout" in selected_nav: st.session_state["current_nav"] = "Layout"
    elif "Captions" in selected_nav: st.session_state["current_nav"] = "Captions"
    elif "Library" in selected_nav: st.session_state["current_nav"] = "Library"
    elif "Settings" in selected_nav: st.session_state["current_nav"] = "Settings"

    # Real-time System Status Pill
    st.markdown('<div class="sidebar-heading">Hardware Status</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="background: #111420; border: 1px solid #1e2436; border-radius: 8px; padding: 10px; margin-bottom: 12px;">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
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
            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">Active Session</div>
            <div style="font-size: 12px; font-weight: 600; color: #e2e8f0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                {os.path.basename(st.session_state['video_path'])}
            </div>
            <div style="font-size: 11px; color: #64748b; margin-top: 4px;">
                {v_meta.get('width', 1920)}x{v_meta.get('height', 1080)} • {v_meta.get('duration', 0):.0f}s
            </div>
        </div>
        """, unsafe_allow_html=True)

# Directory Paths
base_dir = os.path.dirname(os.path.abspath(__file__))
upload_dir = os.path.join(base_dir, "storage", "uploads")
outputs_dir = os.path.join(base_dir, "storage", "outputs")
cache_dir = os.path.join(base_dir, "storage", "cache")
os.makedirs(upload_dir, exist_ok=True)
os.makedirs(outputs_dir, exist_ok=True)
os.makedirs(cache_dir, exist_ok=True)


# =============================================================
# SCREEN 2.1: DASHBOARD (HOME SCREEN)
# =============================================================
if st.session_state["current_nav"] == "Dashboard":
    st.markdown('<div class="top-header"><h2 class="top-title">🏠 Studio Dashboard</h2><div class="badge-gpu">⚡ NVIDIA RTX 3050 Online</div></div>', unsafe_allow_html=True)

    # 4 Top Stats Cards (from Blueprint 2.1)
    s1, s2, s3, s4 = st.columns(4)
    rendered_shorts = [f for f in os.listdir(outputs_dir) if f.lower().endswith(".mp4") and not f.startswith(".")]
    uploaded_vids = [f for f in os.listdir(upload_dir) if f.lower().endswith((".mp4", ".mov", ".mkv", ".webm")) and not f.endswith(".part")]

    with s1:
        st.markdown(f'<div class="stat-box"><div class="stat-number">{len(rendered_shorts)}</div><div class="stat-label">Clips Generated</div></div>', unsafe_allow_html=True)
    with s2:
        st.markdown('<div class="stat-box"><div class="stat-number">15x</div><div class="stat-label">GPU Render Speed</div></div>', unsafe_allow_html=True)
    with s3:
        st.markdown(f'<div class="stat-box"><div class="stat-number">{len(uploaded_vids)}</div><div class="stat-label">Source Sessions</div></div>', unsafe_allow_html=True)
    with s4:
        st.markdown('<div class="stat-box"><div class="stat-number">$0.00</div><div class="stat-label">100% Free & Local</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Quick Start Action Banner
    q_col1, q_col2 = st.columns([2, 1])
    with q_col1:
        st.markdown("""
        <div class="powder-card">
            <h3 style="margin: 0 0 8px 0; color: #f8fafc; font-size: 18px;">⚡ Turn Gaming Moments into Viral 9:16 Shorts</h3>
            <p style="color: #94a3b8; font-size: 13px; margin: 0 0 16px 0;">
                Connect YouTube / Twitch, align your facecam & gameplay boxes live, and let Faster-Whisper + Ollama find your best kills and clutch moments.
            </p>
        </div>
        """, unsafe_allow_html=True)
        btn1, btn2 = st.columns(2)
        with btn1:
            if st.button("📥 Import New Video / URL", type="primary", use_container_width=True):
                st.session_state["current_nav"] = "Capture"
                st.rerun()
        with btn2:
            if st.session_state["video_path"]:
                if st.button("✂️ Open Active Video in Studio", use_container_width=True):
                    st.session_state["current_nav"] = "Studio"
                    st.rerun()

    with q_col2:
        st.markdown("""
        <div class="powder-card">
            <h4 style="margin: 0 0 8px 0; color: #ccff00; font-size: 15px;">🎮 Supported Formats & Layouts</h4>
            <div style="font-size: 12px; color: #cbd5e1; line-height: 1.8;">
                ✓ Powder.gg Split (Facecam Top + Gameplay Bottom)<br>
                ✓ Single Screen Portrait (AI Face Tracking)<br>
                ✓ Gameplay-Only (Center / Custom 9:16 Crop)<br>
                ✓ Cinematic Ambient Blurred Background
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Recent Sessions Grid
    st.markdown('<h4 style="color: #cbd5e1; margin: 24px 0 12px 0;">Recent Video Sessions</h4>', unsafe_allow_html=True)
    if uploaded_vids:
        v_cols = st.columns(min(4, len(uploaded_vids)))
        for idx, vid_file in enumerate(uploaded_vids[:4]):
            col_target = v_cols[idx % 4]
            full_vid_p = os.path.join(upload_dir, vid_file)
            with col_target:
                st.markdown(f"""
                <div class="powder-card">
                    <div style="font-size: 13px; font-weight: 700; color: #f8fafc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 6px;">
                        {vid_file}
                    </div>
                    <div style="font-size: 11px; color: #94a3b8;">Full HD Recording</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Open #{idx+1}", key=f"open_dash_{idx}", use_container_width=True):
                    with st.spinner("Loading video session..."):
                        st.session_state["video_path"] = full_vid_p
                        meta = get_video_info(full_vid_p)
                        st.session_state["video_meta"] = meta
                        v_base = os.path.splitext(vid_file)[0]
                        p_frame = os.path.join(cache_dir, f"{v_base}_preview.jpg")
                        extract_preview_frame(full_vid_p, p_frame, timestamp=10.0)
                        st.session_state["preview_frame"] = p_frame
                        st.session_state["timeline_thumbs"] = extract_timeline_thumbnails(full_vid_p, cache_dir, meta["duration"], count=6)
                        st.session_state["current_nav"] = "Studio"
                        st.rerun()


# =============================================================
# SCREEN 2.2: CAPTURE & INGEST (IMPORT MODAL - BLUEPRINT 2.2)
# =============================================================
elif st.session_state["current_nav"] == "Capture":
    st.markdown('<div class="top-header"><h2 class="top-title">📥 Ingest & Game Capture</h2><div class="badge-gpu">Ready</div></div>', unsafe_allow_html=True)

    c_left, c_mid, c_right = st.columns([1, 4, 1])
    with c_mid:
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
        <div class="upload-zone">
            <div style="font-size: 40px; margin-bottom: 12px;">📂</div>
            <h3 style="margin: 0 0 6px 0; color: #f8fafc; font-size: 18px;">Drag or click to browse your MP4 file</h3>
            <p style="color: #94a3b8; font-size: 13px; margin: 0 0 16px 0;">We'll quickly create exciting clips from your best gaming moments</p>
        </div>
        """, unsafe_allow_html=True)

        uploaded_file = st.file_uploader("Upload Video File", type=["mp4", "mov", "mkv", "webm"], label_visibility="collapsed")

        st.markdown('<div style="text-align: center; color: #64748b; margin: 18px 0; font-size: 13px; font-weight: 600;">― or Link Import ―</div>', unsafe_allow_html=True)

        col_url, col_btn = st.columns([4, 1])
        with col_url:
            yt_link = st.text_input("Enter YouTube Video Link", placeholder="https://www.youtube.com/watch?v=...", label_visibility="collapsed")
        with col_btn:
            run_import = st.button("⚡ Ingest", type="primary", use_container_width=True)

        # Existing Recordings Dropdown
        existing_vids = [f for f in os.listdir(upload_dir) if f.lower().endswith((".mp4", ".mov", ".mkv", ".webm")) and not f.endswith(".part")]
        if existing_vids:
            st.markdown('<div style="margin-top: 26px; font-size: 13px; font-weight: 700; color: #cbd5e1;">Or Pick Existing Source:</div>', unsafe_allow_html=True)
            chosen_local = st.selectbox("Existing files:", existing_vids, label_visibility="collapsed")
            if st.button("🎬 Load into Studio", use_container_width=True):
                target_p = os.path.join(upload_dir, chosen_local)
                with st.spinner("Loading video metadata & timeline..."):
                    st.session_state["video_path"] = target_p
                    meta = get_video_info(target_p)
                    st.session_state["video_meta"] = meta
                    v_base = os.path.splitext(chosen_local)[0]
                    p_frame = os.path.join(cache_dir, f"{v_base}_preview.jpg")
                    extract_preview_frame(target_p, p_frame, timestamp=10.0)
                    st.session_state["preview_frame"] = p_frame
                    st.session_state["timeline_thumbs"] = extract_timeline_thumbnails(target_p, cache_dir, meta["duration"], count=6)
                    st.session_state["current_nav"] = "Studio"
                    st.rerun()

        # Execute Import
        if run_import or uploaded_file:
            chosen_target = None
            if uploaded_file:
                chosen_target = os.path.join(upload_dir, uploaded_file.name)
                with open(chosen_target, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            elif yt_link:
                with st.spinner("Downloading YouTube video at 1080p Full HD..."):
                    try:
                        chosen_target = download_youtube_video(yt_link, upload_dir)
                    except Exception as ex:
                        st.error(f"Download failed: {ex}")

            if chosen_target and os.path.exists(chosen_target):
                with st.spinner("Extracting timeline keyframes & preview snapshot..."):
                    st.session_state["video_path"] = chosen_target
                    meta = get_video_info(chosen_target)
                    st.session_state["video_meta"] = meta
                    v_base = os.path.splitext(os.path.basename(chosen_target))[0]
                    p_frame = os.path.join(cache_dir, f"{v_base}_preview.jpg")
                    extract_preview_frame(chosen_target, p_frame, timestamp=10.0)
                    st.session_state["preview_frame"] = p_frame
                    st.session_state["timeline_thumbs"] = extract_timeline_thumbnails(chosen_target, cache_dir, meta["duration"], count=6)
                    st.session_state["discovered_clips"] = []
                    st.session_state["selected_clip_indices"] = []
                    st.success("Video Ingested! Switching to Studio...")
                    st.session_state["current_nav"] = "Studio"
                    st.rerun()


# =============================================================
# SCREEN 2.4 & 2.5: STUDIO & CLIPS (CORE POWDER.GG WORKSPACE)
# =============================================================
elif st.session_state["current_nav"] == "Studio":
    if not st.session_state["video_path"]:
        st.info("No video loaded! Please go to **📥 Capture & Ingest** first.")
    else:
        v_path = st.session_state["video_path"]
        v_name = os.path.basename(v_path)
        v_meta = st.session_state["video_meta"]
        v_w = v_meta.get("width", 1920)
        v_h = v_meta.get("height", 1080)
        v_dur = v_meta.get("duration", 0.0)

        # Header Bar
        st.markdown(f"""
        <div class="top-header">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="color: #64748b; font-size: 18px; cursor: pointer;">←</span>
                <h3 class="top-title">{v_name}</h3>
                <span style="font-size: 12px; color: #94a3b8;">({v_w}x{v_h} • {v_dur:.0f}s)</span>
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
                <div class="badge-gpu">⚡ RTX 3050 NVENC Ready</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 2-Column Powder Layout
        col_player, col_moments = st.columns([13, 8], gap="medium")

        # -----------------------------------------------------
        # LEFT: 16:9 VIDEO PLAYER & FILMSTRIP TIMELINE
        # -----------------------------------------------------
        with col_player:
            # Action Toolbar above player
            t1, t2, t3 = st.columns([1.2, 1.4, 2.4])
            with t1:
                st.markdown('<div class="virality-badge">📱 9:16 Active</div>', unsafe_allow_html=True)
            with t2:
                if st.button("🎛️ Edit Layout Live", use_container_width=True):
                    st.session_state["current_nav"] = "Layout"
                    st.rerun()
            with t3:
                if st.button("🎨 Customize Subtitles", use_container_width=True):
                    st.session_state["current_nav"] = "Captions"
                    st.rerun()

            # Main Video Player
            st.video(v_path)

            # Filmstrip Timeline Bar (Blueprint 2.5)
            st.markdown('<div style="font-size: 12px; font-weight: 700; color: #94a3b8; margin-top: 8px;">TIMELINE FILMSTRIP</div>', unsafe_allow_html=True)
            thumbs = st.session_state.get("timeline_thumbs", [])
            if thumbs:
                t_cols = st.columns(len(thumbs))
                for idx, t in enumerate(thumbs):
                    with t_cols[idx]:
                        if os.path.exists(t["path"]):
                            st.image(t["path"], caption=f"{int(t['timestamp'])}s", use_container_width=True)

        # -----------------------------------------------------
        # RIGHT: VIRAL MOMENTS & CLIPS (BLUEPRINT 2.4)
        # -----------------------------------------------------
        with col_moments:
            st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div style="font-weight: 700; font-size: 15px; color: #f8fafc;">Suggested Moments</div>
                <div style="font-size: 12px; color: var(--powder-neon); font-weight: 700;">⚡ AI Discovery</div>
            </div>
            """, unsafe_allow_html=True)

            # Event Filter Pills
            st.markdown("""
            <div style="display: flex; gap: 6px; overflow-x: auto; margin-bottom: 12px;">
                <span class="event-tag event-tag-purple">Clip it (3)</span>
                <span class="event-tag event-tag-purple">Wow (2)</span>
                <span class="event-tag">💀 Kill</span>
                <span class="event-tag">👑 Victory</span>
                <span class="event-tag">😂 Laughter</span>
            </div>
            """, unsafe_allow_html=True)

            # Discovery Trigger if not yet run
            if not st.session_state.get("discovered_clips"):
                st.markdown("""
                <div class="powder-card">
                    <h4 style="margin: 0 0 8px 0; color: #f8fafc; font-size: 14px;">⚡ AI Highlight Scanner</h4>
                    <p style="color: #94a3b8; font-size: 12px; margin-bottom: 12px;">
                        Scans transcript audio with Faster-Whisper on GPU & uses Ollama to find viral hooks, clutch gameplay, and laughter.
                    </p>
                </div>
                """, unsafe_allow_html=True)

                col_n, col_d = st.columns(2)
                with col_n:
                    clips_num = st.slider("Moments Count", 1, 5, 3)
                with col_d:
                    dur_bounds = st.slider("Target Duration", 15, 90, (20, 50), step=5)

                if st.button("⚡ Scan & Discover Highlights", type="primary", use_container_width=True):
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
                                num_clips=clips_num,
                                min_duration=dur_bounds[0],
                                max_duration=dur_bounds[1]
                            )

                            st.session_state["discovered_clips"] = clips
                            st.session_state["selected_clip_indices"] = list(range(len(clips)))
                            st.success(f"Discovered {len(clips)} Highlights!")
                            st.rerun()

                        except Exception as ex:
                            st.error(f"Discovery error: {ex}")

            # Display Discovered Clip Cards
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
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <span class="virality-badge">⚡ {v_score}</span>
                            <span style="font-size: 12px; color: #94a3b8; font-weight: 600;">{int(c['start'])}s - {int(c['end'])}s ({dur}s)</span>
                        </div>
                        <div style="font-weight: 700; color: #f8fafc; font-size: 14px; margin-bottom: 6px;">
                            {c.get('title', f'Moment #{idx+1}')}
                        </div>
                        <div style="margin-bottom: 6px;">{tags_html}</div>
                        <div style="font-size: 11px; color: #94a3b8; font-style: italic;">"{c.get('reason', '')}"</div>
                    </div>
                    """, unsafe_allow_html=True)

                    is_inc = st.checkbox("Include in Batch Export", value=(idx in st.session_state["selected_clip_indices"]), key=f"sel_m_{idx}")
                    if is_inc:
                        selected_idxs.append(idx)

                st.session_state["selected_clip_indices"] = selected_idxs

                # BIG NEON BUTTON: CREATE X CLIPS (BLUEPRINT 2.6 & 2.10)
                num_to_export = len(selected_idxs)
                st.markdown("<br>", unsafe_allow_html=True)
                create_btn = st.button(
                    f"⚡ CREATE {num_to_export} CLIPS (NVENC 60 FPS)",
                    type="primary",
                    use_container_width=True,
                    disabled=(num_to_export == 0)
                )

                if create_btn:
                    prog_bar = st.progress(0)
                    status_lbl = st.empty()

                    def on_progress(title, pct, msg):
                        prog_bar.progress(int(pct))
                        status_lbl.markdown(f"**{title} ({pct:.0f}%):** {msg}")

                    try:
                        from pipeline import ShortsPipeline
                        pipeline = ShortsPipeline()

                        chosen_clips_data = [clips[i] for i in selected_idxs]
                        act_layout = st.session_state.get("active_layout", "gaming_split")
                        act_gaming = st.session_state.get("active_gaming_config")
                        act_single = st.session_state.get("active_single_config")
                        theme_sel = st.session_state.get("subtitle_theme", "Hormozi Gold (Viral)")
                        emojis_sel = st.session_state.get("enable_emojis", True)

                        with st.spinner("Rendering shorts in Full HD with RTX 3050 NVENC..."):
                            results = pipeline.process(
                                video_source=v_path,
                                is_youtube=False,
                                num_clips=len(chosen_clips_data),
                                subtitle_theme=theme_sel,
                                enable_emojis=emojis_sel,
                                layout_mode=act_layout,
                                gaming_config=act_gaming,
                                single_crop_config=act_single,
                                preselected_clips=chosen_clips_data,
                                progress_callback=on_progress
                            )

                        st.session_state["results"] = results
                        st.balloons()
                        st.success(f"Successfully Created {len(results)} Shorts!")
                        st.session_state["current_nav"] = "Library"
                        st.rerun()

                    except Exception as err:
                        st.error(f"Render Error: {err}")
                        st.exception(err)


# =============================================================
# SCREEN 2.7: LAYOUT & TEMPLATES (INTERACTIVE ALIGNMENT)
# =============================================================
elif st.session_state["current_nav"] == "Layout":
    st.markdown('<div class="top-header"><h2 class="top-title">🎛️ Visual Layout & Crop Alignment</h2><div class="badge-gpu">Live Sync</div></div>', unsafe_allow_html=True)

    if not st.session_state["video_path"]:
        st.info("Please load a video in **📥 Capture & Ingest** first.")
    else:
        v_meta = st.session_state["video_meta"]
        v_w = v_meta.get("width", 1920)
        v_h = v_meta.get("height", 1080)

        st.markdown("""
        <div class="powder-card">
            <h4 style="margin: 0 0 6px 0; color: #ccff00;">Powder.gg Dual Visual Alignment</h4>
            <p style="color: #94a3b8; font-size: 13px; margin: 0;">
                Inspect your actual video frame on the left and see the exact 9:16 mobile mockup on the right in real time.
            </p>
        </div>
        """, unsafe_allow_html=True)

        mode_sel = st.radio(
            "Screen Mode:",
            [
                "🎮 Gaming Split (Facecam on Top + Gameplay on Bottom)",
                "📱 Single Screen 9:16 (Full Portrait Crop)",
                "🎬 Cinematic Blur Fit (Original 16:9 with Ambient Blur)"
            ],
            index=0 if st.session_state.get("active_layout") == "gaming_split" else (1 if st.session_state.get("active_layout") == "crop" else 2)
        )

        if "Gaming Split" in mode_sel:
            st.session_state["active_layout"] = "gaming_split"

            col_p, col_tune = st.columns([1, 2])
            with col_p:
                preset_name = st.selectbox(
                    "Streamer Preset:",
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

            presets_dict = {
                "Center-Top Facecam (Like Spyki Plays)": {"fc_x": 28, "fc_y": 15, "fc_w": 44, "fc_h": 45, "gp_x": 15, "gp_y": 0, "gp_w": 70, "gp_h": 100},
                "Top-Right Facecam (Scout, Mortal, Dynamo)": {"fc_x": 65, "fc_y": 5, "fc_w": 32, "fc_h": 40, "gp_x": 15, "gp_y": 0, "gp_w": 70, "gp_h": 100},
                "Top-Left Facecam": {"fc_x": 5, "fc_y": 5, "fc_w": 32, "fc_h": 40, "gp_x": 15, "gp_y": 0, "gp_w": 70, "gp_h": 100},
                "Bottom-Right Facecam": {"fc_x": 65, "fc_y": 55, "fc_w": 32, "fc_h": 40, "gp_x": 15, "gp_y": 0, "gp_w": 70, "gp_h": 100},
                "Bottom-Left Facecam": {"fc_x": 5, "fc_y": 55, "fc_w": 32, "fc_h": 40, "gp_x": 15, "gp_y": 0, "gp_w": 70, "gp_h": 100},
                "Custom Manual Sliders": {"fc_x": 30, "fc_y": 10, "fc_w": 40, "fc_h": 40, "gp_x": 15, "gp_y": 0, "gp_w": 70, "gp_h": 100}
            }
            vals = presets_dict[preset_name]

            with col_tune:
                tune1, tune2 = st.columns(2)
                with tune1:
                    st.markdown("<b style='color: #00ff78;'>📷 Facecam Box (Top 40%)</b>", unsafe_allow_html=True)
                    fc_x = st.slider("Facecam X (%)", 0, 100, vals["fc_x"], key="l_fc_x")
                    fc_y = st.slider("Facecam Y (%)", 0, 100, vals["fc_y"], key="l_fc_y")
                    fc_w = st.slider("Facecam Width (%)", 15, 70, vals["fc_w"], key="l_fc_w")
                    fc_h = st.slider("Facecam Height (%)", 15, 70, vals["fc_h"], key="l_fc_h")
                with tune2:
                    st.markdown("<b style='color: #00d2ff;'>🎯 Gameplay Box (Bottom 60%)</b>", unsafe_allow_html=True)
                    gp_x = st.slider("Gameplay X (%)", 0, 100, vals["gp_x"], key="l_gp_x")
                    gp_y = st.slider("Gameplay Y (%)", 0, 100, vals["gp_y"], key="l_gp_y")
                    gp_w = st.slider("Gameplay Width (%)", 30, 100, vals["gp_w"], key="l_gp_w")
                    gp_h = st.slider("Gameplay Height (%)", 30, 100, vals["gp_h"], key="l_gp_h")

            fc_px = int((fc_x / 100.0) * v_w)
            fc_py = int((fc_y / 100.0) * v_h)
            fc_pw = int((fc_w / 100.0) * v_w)
            fc_ph = int((fc_h / 100.0) * v_h)

            gp_px = int((gp_x / 100.0) * v_w)
            gp_py = int((gp_y / 100.0) * v_h)
            gp_pw = int((gp_w / 100.0) * v_w)
            gp_ph = int((gp_h / 100.0) * v_h)

            g_cfg = {
                "facecam": {"x": fc_px, "y": fc_py, "w": fc_pw, "h": fc_ph},
                "gameplay": {"x": gp_px, "y": gp_py, "w": gp_pw, "h": gp_ph},
                "top_height": 760
            }
            st.session_state["active_gaming_config"] = g_cfg

            # Dual Visual Feedback
            st.markdown('<div style="font-size: 13px; font-weight: 700; color: #cbd5e1; margin: 14px 0 8px 0;">🔴 Live Dual Visual Alignment Feedback</div>', unsafe_allow_html=True)
            v1, v2 = st.columns([3, 2])
            with v1:
                if st.session_state["preview_frame"] and os.path.exists(st.session_state["preview_frame"]):
                    img_map = Image.open(st.session_state["preview_frame"]).convert("RGB")
                    d = ImageDraw.Draw(img_map)
                    d.rectangle([gp_px, gp_py, gp_px + gp_pw, gp_py + gp_ph], outline=(0, 210, 255), width=6)
                    d.text((gp_px + 15, gp_py + 15), "TARGET GAMEPLAY (Bottom 60%)", fill=(0, 210, 255))
                    d.rectangle([fc_px, fc_py, fc_px + fc_pw, fc_py + fc_ph], outline=(0, 255, 120), width=6)
                    d.text((fc_px + 15, fc_py + 15), "FACECAM (Top 40%)", fill=(0, 255, 120))
                    st.image(img_map, caption="1. Selection Bounding Boxes on 16:9 Raw Video", use_container_width=True)
            with v2:
                mob_img = generate_mobile_preview(st.session_state["preview_frame"], g_cfg)
                if mob_img:
                    st.image(mob_img, caption="2. Exact 9:16 Short Preview Before Render", width=220)

        elif "Single Screen" in mode_sel:
            st.session_state["active_layout"] = "crop"
            sc1, sc2 = st.columns([1, 2])
            with sc1:
                single_choice = st.radio(
                    "Face Tracking Mode:",
                    ["Auto-Track Speaker Face (AI)", "No Facecam (Custom / Center Gameplay Crop)"],
                    index=0
                )

            crop_w_t = int(v_h * 9 / 16)
            if crop_w_t % 2 != 0: crop_w_t += 1

            with sc2:
                if "No Facecam" in single_choice:
                    hp = st.slider("Horizontal Screen Position (%)", 0, 100, 50)
                    max_x = v_w - crop_w_t
                    tx = int((hp / 100.0) * max_x)
                    if tx % 2 != 0: tx += 1
                    st.session_state["active_single_config"] = {"mode": "custom", "crop_x": tx}

                    if st.session_state["preview_frame"] and os.path.exists(st.session_state["preview_frame"]):
                        img_s = Image.open(st.session_state["preview_frame"]).convert("RGB")
                        d = ImageDraw.Draw(img_s)
                        d.rectangle([tx, 0, tx + crop_w_t, v_h], outline=(255, 230, 0), width=6)
                        d.text((tx + 15, 25), "9:16 SHORT WINDOW", fill=(255, 230, 0))
                        st.image(img_s, caption="Live 9:16 Horizontal Position Map", use_container_width=True)
                else:
                    st.session_state["active_single_config"] = {"mode": "auto_face"}
                    st.info("AI Face-Tracker will automatically track and center on the active speaker.")

        else:
            st.session_state["active_layout"] = "blur_fit"
            st.info("Full 16:9 widescreen video stays crisp in center with ambient blurred background.")

        if st.button("✓ Save Layout & Return to Studio", type="primary"):
            st.session_state["current_nav"] = "Studio"
            st.rerun()


# =============================================================
# SCREEN 2.8: CAPTIONS & STYLING (BLUEPRINT 2.8)
# =============================================================
elif st.session_state["current_nav"] == "Captions":
    st.markdown('<div class="top-header"><h2 class="top-title">🎨 Caption Engine & Effects</h2><div class="badge-gpu">ASS Karaoke</div></div>', unsafe_allow_html=True)

    c_col1, c_col2 = st.columns(2)
    with c_col1:
        st.markdown("""
        <div class="powder-card">
            <h4 style="margin: 0 0 10px 0; color: #ccff00;">Viral Subtitle Presets</h4>
            <div style="font-size: 13px; color: #94a3b8; margin-bottom: 14px;">
                Choose high-retention caption styles with word-by-word karaoke highlight.
            </div>
        </div>
        """, unsafe_allow_html=True)

        selected_theme = st.selectbox(
            "Caption Theme",
            ["Hormozi Gold (Viral)", "MrBeast Hype", "Neon Cyberpunk", "Emerald Mint", "Clean Minimalist"],
            index=["Hormozi Gold (Viral)", "MrBeast Hype", "Neon Cyberpunk", "Emerald Mint", "Clean Minimalist"].index(st.session_state["subtitle_theme"])
        )
        st.session_state["subtitle_theme"] = selected_theme

        st.session_state["enable_emojis"] = st.checkbox("✨ Auto-Emojis (💰 🔥 🏆 🎯 🚀 🐶)", value=st.session_state["enable_emojis"])

    with c_col2:
        st.markdown("""
        <div class="powder-card">
            <h4 style="margin: 0 0 10px 0; color: #38bdf8;">Live Theme Preview</h4>
        </div>
        """, unsafe_allow_html=True)

        theme_previews = {
            "Hormozi Gold (Viral)": "THIS IS <span style='color: #ffff00; font-weight: 900;'>VIRAL</span> 💰",
            "MrBeast Hype": "WIN A <span style='color: #ff3333; font-weight: 900;'>LAMBORGHINI</span> 🔥",
            "Neon Cyberpunk": "ELECTRIC <span style='color: #ff00ff; font-weight: 900;'>SPEED</span> ⚡",
            "Emerald Mint": "CHAMPION <span style='color: #00ff66; font-weight: 900;'>VICTORY</span> 🏆",
            "Clean Minimalist": "SIMPLE <span style='color: #ffffff; font-weight: 900;'>AESTHETIC</span> ✨"
        }
        st.markdown(f"""
        <div style="background: #000; border: 2px solid #2a334d; border-radius: 12px; padding: 30px; text-align: center; font-size: 24px; font-weight: 800; letter-spacing: 1px;">
            {theme_previews.get(selected_theme, "")}
        </div>
        """, unsafe_allow_html=True)

    if st.button("✓ Apply Caption Theme & Return to Studio", type="primary"):
        st.session_state["current_nav"] = "Studio"
        st.rerun()


# =============================================================
# SCREEN 2.3 & 2.11: CLIPS LIBRARY & EXPORT HUB (BLUEPRINT 2.3)
# =============================================================
elif st.session_state["current_nav"] == "Library":
    st.markdown('<div class="top-header"><h2 class="top-title">📂 Exported Shorts & Clips Library</h2><div class="badge-gpu">Completed</div></div>', unsafe_allow_html=True)

    all_exported = [f for f in os.listdir(outputs_dir) if f.lower().endswith(".mp4") and not f.startswith(".")]

    if not all_exported and not st.session_state.get("results"):
        st.info("No rendered clips yet! Head over to **✂️ Studio & Clips** to create clips.")
    else:
        res = st.session_state.get("results", [])
        if res:
            cols = st.columns(len(res) if len(res) <= 3 else 3)
            for i, clip in enumerate(res):
                c_idx = i % 3
                with cols[c_idx]:
                    st.markdown(f"""
                    <div class="powder-card">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <span class="virality-badge">⚡ {clip.get('virality_score', 92)}</span>
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
                                key=f"dl_lib_{i}",
                                use_container_width=True
                            )
        else:
            cols = st.columns(min(3, len(all_exported)))
            for i, fn in enumerate(all_exported):
                c_idx = i % 3
                target_p = os.path.join(outputs_dir, fn)
                with cols[c_idx]:
                    st.markdown(f'<div class="powder-card"><div style="font-weight: 700; color: #f8fafc;">{fn}</div></div>', unsafe_allow_html=True)
                    with open(target_p, "rb") as vf:
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


# =============================================================
# SCREEN 3.1 & 3.6: SETTINGS, HARDWARE & SHORTCUTS (BLUEPRINT 3.1)
# =============================================================
elif st.session_state["current_nav"] == "Settings":
    st.markdown('<div class="top-header"><h2 class="top-title">⚙️ System Settings & Hardware</h2></div>', unsafe_allow_html=True)

    col_h, col_s = st.columns(2)
    with col_h:
        st.markdown("""
        <div class="powder-card">
            <h4 style="margin: 0 0 10px 0; color: #ccff00;">🟢 NVIDIA GeForce RTX 3050 NVENC</h4>
            <div style="font-size: 13px; color: #cbd5e1; line-height: 1.8;">
                • <b>VRAM:</b> 6GB GDDR6 Dedicated<br>
                • <b>Hardware Video Encoder:</b> h264_nvenc (Preset P6, High Quality)<br>
                • <b>Whisper STT Acceleration:</b> CUDA 12 (float16)<br>
                • <b>Encode Bitrate:</b> 14 Mbps (Full HD 1080x1920 @ 60 FPS)
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="powder-card">
            <h4 style="margin: 0 0 10px 0; color: #38bdf8;">⌨️ Keyboard Shortcuts (Blueprint 3.6)</h4>
            <div style="font-size: 13px; color: #cbd5e1; line-height: 1.8;">
                • <b>Space:</b> Play / Pause Video<br>
                • <b>F:</b> Toggle Fullscreen Player<br>
                • <b>M:</b> Mute / Unmute Audio<br>
                • <b>Ctrl + R:</b> Rerun Streamlit Session<br>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_s:
        st.markdown("""
        <div class="powder-card">
            <h4 style="margin: 0 0 10px 0; color: #a78bfa;">🧠 AI Models & Local Pipeline</h4>
            <div style="font-size: 13px; color: #cbd5e1; line-height: 1.8;">
                • <b>LLM:</b> Ollama (<code>llama3.2:latest</code>)<br>
                • <b>Speech Recognition:</b> Faster-Whisper (<code>small</code> / Multilingual)<br>
                • <b>Subtitle Font:</b> Windows Nirmala UI (Sharp Hindi & English Support)<br>
                • <b>Cost:</b> 100% Free & Unlimited Local Exports
            </div>
        </div>
        """, unsafe_allow_html=True)
