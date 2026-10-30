import os
import sys
import json
import logging
import socket
import asyncio
import base64
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
import streamlit.components.v1 as components
from core.audio import extract_preview_frame, extract_timeline_thumbnails, get_video_info, download_youtube_video, trim_video

# -------------------------------------------------------------
# STREAMLIT PAGE CONFIGURATION
# -------------------------------------------------------------
st.set_page_config(
    page_title="POWDER Studio AI - Interactive Gaming Shorts Suite",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# HIGH-FIDELITY GAMING SAAS CSS
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

    .sidebar-heading {
        color: var(--text-secondary);
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        margin: 14px 0 6px 0;
    }

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
    st.session_state["current_nav"] = "Studio" if "video_path" in st.session_state and st.session_state["video_path"] else "Dashboard"
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

# Default Alignment Presets
if "fc_x" not in st.session_state: st.session_state["fc_x"] = 65
if "fc_y" not in st.session_state: st.session_state["fc_y"] = 5
if "fc_w" not in st.session_state: st.session_state["fc_w"] = 32
if "fc_h" not in st.session_state: st.session_state["fc_h"] = 40
if "gp_x" not in st.session_state: st.session_state["gp_x"] = 15
if "gp_y" not in st.session_state: st.session_state["gp_y"] = 0
if "gp_w" not in st.session_state: st.session_state["gp_w"] = 70
if "gp_h" not in st.session_state: st.session_state["gp_h"] = 100
if "snapshot_ts" not in st.session_state: st.session_state["snapshot_ts"] = 45.0

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

# Paths
base_dir = os.path.dirname(os.path.abspath(__file__))
upload_dir = os.path.join(base_dir, "storage", "uploads")
outputs_dir = os.path.join(base_dir, "storage", "outputs")
cache_dir = os.path.join(base_dir, "storage", "cache")
os.makedirs(upload_dir, exist_ok=True)
os.makedirs(outputs_dir, exist_ok=True)
os.makedirs(cache_dir, exist_ok=True)

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

def get_base64_encoded_image(image_path: str) -> str:
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""

# -------------------------------------------------------------
# LEFT SIDEBAR NAVIGATION
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
    if "Dashboard" in selected_nav: st.session_state["current_nav"] = "Dashboard"
    elif "Capture" in selected_nav: st.session_state["current_nav"] = "Capture"
    elif "Studio" in selected_nav: st.session_state["current_nav"] = "Studio"
    elif "Layout" in selected_nav: st.session_state["current_nav"] = "Layout"
    elif "Captions" in selected_nav: st.session_state["current_nav"] = "Captions"
    elif "Library" in selected_nav: st.session_state["current_nav"] = "Library"
    elif "Settings" in selected_nav: st.session_state["current_nav"] = "Settings"

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


# =============================================================
# SCREEN 2.1: DASHBOARD
# =============================================================
if st.session_state["current_nav"] == "Dashboard":
    st.markdown('<div class="top-header"><h2 class="top-title">🏠 Studio Dashboard</h2><div class="badge-gpu">⚡ NVIDIA RTX 3050 Online</div></div>', unsafe_allow_html=True)

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

    q_col1, q_col2 = st.columns([2, 1])
    with q_col1:
        st.markdown("""
        <div class="powder-card">
            <h3 style="margin: 0 0 8px 0; color: #f8fafc; font-size: 18px;">⚡ Turn Gaming Moments into Viral 9:16 Shorts</h3>
            <p style="color: #94a3b8; font-size: 13px; margin: 0 0 16px 0;">
                Connect YouTube / Twitch, scrub to the gameplay scene, align your facecam & gameplay with mouse drag, and render high-retention shorts in seconds.
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
                ✓ Mouse Drag-and-Drop Crop Boxes<br>
                ✓ Gameplay Scene Timestamp Scrubber<br>
                ✓ Timeline In/Out Custom Trimmer<br>
                ✓ 60 FPS NVIDIA NVENC Encoding
            </div>
        </div>
        """, unsafe_allow_html=True)

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
                        # Default snapshot to 45s (gameplay) or 20%
                        snap_s = min(45.0, meta["duration"] * 0.2)
                        st.session_state["snapshot_ts"] = snap_s
                        p_frame = os.path.join(cache_dir, f"{v_base}_preview.jpg")
                        extract_preview_frame(full_vid_p, p_frame, timestamp=snap_s)
                        st.session_state["preview_frame"] = p_frame
                        st.session_state["timeline_thumbs"] = extract_timeline_thumbnails(full_vid_p, cache_dir, meta["duration"], count=6)
                        st.session_state["current_nav"] = "Studio"
                        st.rerun()


# =============================================================
# SCREEN 2.2: CAPTURE & INGEST
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
                    snap_s = min(45.0, meta["duration"] * 0.2)
                    st.session_state["snapshot_ts"] = snap_s
                    p_frame = os.path.join(cache_dir, f"{v_base}_preview.jpg")
                    extract_preview_frame(target_p, p_frame, timestamp=snap_s)
                    st.session_state["preview_frame"] = p_frame
                    st.session_state["timeline_thumbs"] = extract_timeline_thumbnails(target_p, cache_dir, meta["duration"], count=6)
                    st.session_state["current_nav"] = "Studio"
                    st.rerun()

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
                    snap_s = min(45.0, meta["duration"] * 0.2)
                    st.session_state["snapshot_ts"] = snap_s
                    p_frame = os.path.join(cache_dir, f"{v_base}_preview.jpg")
                    extract_preview_frame(chosen_target, p_frame, timestamp=snap_s)
                    st.session_state["preview_frame"] = p_frame
                    st.session_state["timeline_thumbs"] = extract_timeline_thumbnails(chosen_target, cache_dir, meta["duration"], count=6)
                    st.session_state["discovered_clips"] = []
                    st.session_state["selected_clip_indices"] = []
                    st.success("Video Ingested! Switching to Studio...")
                    st.session_state["current_nav"] = "Studio"
                    st.rerun()


# =============================================================
# SCREEN 2.4 & 2.5: STUDIO, CLIPS & INTERACTIVE IN/OUT CUTTER
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

        col_player, col_moments = st.columns([13, 8], gap="medium")

        # LEFT COLUMN: PLAYER, TIMELINE & CUSTOM CUTTER
        with col_player:
            t1, t2, t3 = st.columns([1.2, 1.4, 2.4])
            with t1:
                st.markdown('<div class="virality-badge">📱 9:16 Active</div>', unsafe_allow_html=True)
            with t2:
                if st.button("🎛️ Drag & Drop Layout", use_container_width=True):
                    st.session_state["current_nav"] = "Layout"
                    st.rerun()
            with t3:
                if st.button("🎨 Customize Subtitles", use_container_width=True):
                    st.session_state["current_nav"] = "Captions"
                    st.rerun()

            # Main Video Player
            st.video(v_path)

            # Filmstrip Timeline Bar
            st.markdown('<div style="font-size: 12px; font-weight: 700; color: #94a3b8; margin-top: 8px;">TIMELINE FILMSTRIP</div>', unsafe_allow_html=True)
            thumbs = st.session_state.get("timeline_thumbs", [])
            if thumbs:
                t_cols = st.columns(len(thumbs))
                for idx, t in enumerate(thumbs):
                    with t_cols[idx]:
                        if os.path.exists(t["path"]):
                            st.image(t["path"], caption=f"{int(t['timestamp'])}s", use_container_width=True)

            # -------------------------------------------------
            # 🎬 NLE PROFESSIONAL TIMELINE & SPLIT / CUT TOOLS
            # -------------------------------------------------
            st.markdown("""
            <div class="powder-card" style="margin-top: 14px; border-color: #283147;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 16px;">🎬</span>
                        <h4 style="margin: 0; color: #f8fafc; font-size: 15px;">Timeline Editor & Split Tools</h4>
                    </div>
                    <span style="font-size: 11px; background: rgba(204, 255, 0, 0.15); color: #ccff00; padding: 3px 8px; border-radius: 4px; font-weight: 700;">CapCut / Premiere Style</span>
                </div>
                <p style="color: #94a3b8; font-size: 12px; margin: 0 0 12px 0;">
                    Scrub the playhead needle to any frame, split at playhead, or 1-click ripple delete the intro before current time.
                </p>
            </div>
            """, unsafe_allow_html=True)

            # Interactive Playhead Scrubber
            cur_playhead = float(st.session_state.get("playhead_ts", 91.0))
            cur_playhead = min(float(v_dur), max(0.0, cur_playhead))
            
            p_head_col, t_code_col = st.columns([3, 1])
            with p_head_col:
                new_playhead = st.slider(
                    "Playhead Position (seconds):",
                    0.0, float(v_dur),
                    value=cur_playhead,
                    step=1.0,
                    key="editor_playhead_slider"
                )
                st.session_state["playhead_ts"] = new_playhead

            with t_code_col:
                ph_m = int(new_playhead // 60)
                ph_s = int(new_playhead % 60)
                dur_m = int(v_dur // 60)
                dur_s = int(v_dur % 60)
                st.markdown(f"""
                <div style="background: #090a10; border: 1px solid #283147; border-radius: 8px; padding: 10px; text-align: center; margin-top: 6px;">
                    <div style="font-size: 10px; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Playhead Timecode</div>
                    <div style="font-family: monospace; font-size: 18px; font-weight: 800; color: #ccff00; margin-top: 2px;">
                        {ph_m:02d}:{ph_s:02d} <span style="font-size: 12px; color: #64748b;">/ {dur_m:02d}:{dur_s:02d}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Quick Scrubber Steppers
            st.markdown("<div style='font-size: 11px; font-weight: 700; color: #94a3b8; margin: 4px 0 6px 0;'>QUICK SEEK CONTROLS:</div>", unsafe_allow_html=True)
            k1, k2, k3, k4, k5 = st.columns(5)
            with k1:
                if st.button("⏪ -10s", use_container_width=True):
                    st.session_state["playhead_ts"] = max(0.0, new_playhead - 10.0)
                    st.rerun()
            with k2:
                if st.button("⏪ -2s", use_container_width=True):
                    st.session_state["playhead_ts"] = max(0.0, new_playhead - 2.0)
                    st.rerun()
            with k3:
                if st.button("📍 Seek Game (01:31)", use_container_width=True):
                    st.session_state["playhead_ts"] = 91.0
                    st.session_state["snapshot_ts"] = 91.0
                    v_base = os.path.splitext(v_name)[0]
                    p_frame = os.path.join(cache_dir, f"{v_base}_preview.jpg")
                    extract_preview_frame(v_path, p_frame, timestamp=91.0)
                    st.session_state["preview_frame"] = p_frame
                    st.rerun()
            with k4:
                if st.button("⏩ +2s", use_container_width=True):
                    st.session_state["playhead_ts"] = min(float(v_dur), new_playhead + 2.0)
                    st.rerun()
            with k5:
                if st.button("⏩ +10s", use_container_width=True):
                    st.session_state["playhead_ts"] = min(float(v_dur), new_playhead + 10.0)
                    st.rerun()

            # Editor Action Buttons: Ripple Delete & Split Tools
            st.markdown("<div style='font-size: 11px; font-weight: 700; color: #cbd5e1; margin: 12px 0 6px 0;'>TIMELINE EDIT ACTIONS:</div>", unsafe_allow_html=True)
            act_col1, act_col2 = st.columns(2)

            with act_col1:
                # 1-CLICK RIPPLE DELETE INTRO (Cut Left of Playhead)
                if st.button(f"🗑️ Ripple Delete Intro (Cut Left of {ph_m:02d}:{ph_s:02d})", type="primary", use_container_width=True):
                    if new_playhead <= 1.0:
                        st.warning("Playhead is at the start! Scrub forward to where gameplay begins to delete the intro.")
                    else:
                        with st.spinner(f"Ripple deleting intro before {ph_m:02d}:{ph_s:02d} in 0.1s..."):
                            v_base = os.path.splitext(v_name)[0]
                            trimmed_filename = f"{v_base}_cut_{int(new_playhead)}s.mp4"
                            trimmed_path = os.path.join(upload_dir, trimmed_filename)
                            trim_video(v_path, trimmed_path, float(new_playhead), v_dur)

                            if os.path.exists(trimmed_path):
                                st.session_state["video_path"] = trimmed_path
                                meta = get_video_info(trimmed_path)
                                st.session_state["video_meta"] = meta
                                st.session_state["playhead_ts"] = 0.0
                                st.session_state["snapshot_ts"] = 5.0
                                p_frame = os.path.join(cache_dir, f"{os.path.splitext(trimmed_filename)[0]}_preview.jpg")
                                extract_preview_frame(trimmed_path, p_frame, timestamp=5.0)
                                st.session_state["preview_frame"] = p_frame
                                st.session_state["timeline_thumbs"] = extract_timeline_thumbnails(trimmed_path, cache_dir, meta["duration"], count=6)
                                st.session_state["discovered_clips"] = []
                                st.session_state["selected_clip_indices"] = []
                                st.success(f"Intro successfully deleted! Video now starts directly from {ph_m:02d}:{ph_s:02d}.")
                                st.rerun()

            with act_col2:
                # 1-CLICK RIPPLE DELETE OUTRO (Cut Right of Playhead)
                if st.button(f"🗑️ Ripple Delete Outro (Cut Right of {ph_m:02d}:{ph_s:02d})", use_container_width=True):
                    if new_playhead >= v_dur - 2.0:
                        st.warning("Playhead is at the end of the video!")
                    else:
                        with st.spinner(f"Trimming outro after {ph_m:02d}:{ph_s:02d}..."):
                            v_base = os.path.splitext(v_name)[0]
                            trimmed_filename = f"{v_base}_end_{int(new_playhead)}s.mp4"
                            trimmed_path = os.path.join(upload_dir, trimmed_filename)
                            trim_video(v_path, trimmed_path, 0.0, float(new_playhead))

                            if os.path.exists(trimmed_path):
                                st.session_state["video_path"] = trimmed_path
                                meta = get_video_info(trimmed_path)
                                st.session_state["video_meta"] = meta
                                st.session_state["playhead_ts"] = 0.0
                                st.session_state["snapshot_ts"] = 5.0
                                p_frame = os.path.join(cache_dir, f"{os.path.splitext(trimmed_filename)[0]}_preview.jpg")
                                extract_preview_frame(trimmed_path, p_frame, timestamp=5.0)
                                st.session_state["preview_frame"] = p_frame
                                st.session_state["timeline_thumbs"] = extract_timeline_thumbnails(trimmed_path, cache_dir, meta["duration"], count=6)
                                st.session_state["discovered_clips"] = []
                                st.session_state["selected_clip_indices"] = []
                                st.success("Outro trimmed! Project updated.")
                                st.rerun()

            # In/Out Selection Range for Direct Short Export
            st.markdown("<div style='font-size: 11px; font-weight: 700; color: #cbd5e1; margin: 12px 0 6px 0;'>CUSTOM SHORT EXPORT WINDOW:</div>", unsafe_allow_html=True)
            default_cut_s = int(new_playhead)
            default_cut_e = int(min(v_dur, default_cut_s + 35))
            
            c_range = st.slider(
                "Select In / Out Range to Export:",
                0, int(v_dur),
                value=(default_cut_s, default_cut_e),
                step=1
            )
            cut_in, cut_out = c_range
            cut_duration = cut_out - cut_in

            c_info1, c_info2 = st.columns([2, 1])
            with c_info1:
                in_fmt = f"{int(cut_in//60):02d}:{int(cut_in%60):02d}"
                out_fmt = f"{int(cut_out//60):02d}:{int(cut_out%60):02d}"
                st.markdown(f"**Marked Short:** `{in_fmt}` ──▶ `{out_fmt}` (Duration: **{cut_duration}s**)")
            with c_info2:
                if st.button("📸 Grab Frame at Cut Start", use_container_width=True):
                    st.session_state["snapshot_ts"] = float(cut_in)
                    v_base = os.path.splitext(v_name)[0]
                    p_frame = os.path.join(cache_dir, f"{v_base}_preview.jpg")
                    extract_preview_frame(v_path, p_frame, timestamp=float(cut_in))
                    st.session_state["preview_frame"] = p_frame
                    st.success(f"Snapshot updated to {in_fmt}!")
                    st.rerun()

            cut_layout = st.selectbox(
                "Layout for this custom cut:",
                ["🎮 Powder.gg Gaming Split (Facecam Top + Gameplay Bottom)", "📱 Single Screen (Fullscreen Talking/Intro)", "🎬 Ambient Blur Fit"],
                index=0
            )

            if st.button(f"⚡ RENDER THIS {cut_duration}s SELECTION AS 9:16 SHORT (NVENC 60 FPS)", type="primary", use_container_width=True):
                if cut_duration <= 5:
                    st.error("Cut duration must be at least 5 seconds!")
                else:
                    prog_bar = st.progress(0)
                    status_lbl = st.empty()

                    def on_progress(title, pct, msg):
                        prog_bar.progress(int(pct))
                        status_lbl.markdown(f"**{title} ({pct:.0f}%):** {msg}")

                    try:
                        from pipeline import ShortsPipeline
                        pipeline = ShortsPipeline()

                        chosen_clip = [{
                            "start": float(cut_in),
                            "end": float(cut_out),
                            "title": f"Custom Cut ({in_fmt}-{out_fmt})",
                            "hook_score": 9.5,
                            "virality_score": 95,
                            "tags": ["✂️ Custom Cut", "⚡ Clip it"],
                            "reason": "Direct timeline user selection"
                        }]

                        act_layout = "gaming_split" if "Gaming Split" in cut_layout else ("crop" if "Single Screen" in cut_layout else "blur_fit")
                        act_gaming = st.session_state.get("active_gaming_config")
                        act_single = st.session_state.get("active_single_config")
                        theme_sel = st.session_state.get("subtitle_theme", "Hormozi Gold (Viral)")

                        with st.spinner("Rendering custom cut with RTX 3050 NVENC..."):
                            results = pipeline.process(
                                video_source=v_path,
                                is_youtube=False,
                                num_clips=1,
                                subtitle_theme=theme_sel,
                                enable_emojis=True,
                                layout_mode=act_layout,
                                gaming_config=act_gaming,
                                single_crop_config=act_single,
                                preselected_clips=chosen_clip,
                                progress_callback=on_progress
                            )

                        st.session_state["results"] = results
                        st.balloons()
                        st.success(f"Custom Cut Rendered Successfully!")
                        st.session_state["current_nav"] = "Library"
                        st.rerun()
                    except Exception as err:
                        st.error(f"Render Error: {err}")

        # RIGHT COLUMN: AI SUGGESTED MOMENTS
        with col_moments:
            st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div style="font-weight: 700; font-size: 15px; color: #f8fafc;">AI Suggested Moments</div>
                <div style="font-size: 12px; color: var(--powder-neon); font-weight: 700;">⚡ AI Discovery</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("""
            <div style="display: flex; gap: 6px; overflow-x: auto; margin-bottom: 12px;">
                <span class="event-tag event-tag-purple">Clip it (3)</span>
                <span class="event-tag event-tag-purple">Wow (2)</span>
                <span class="event-tag">💀 Kill</span>
                <span class="event-tag">👑 Victory</span>
                <span class="event-tag">😂 Laughter</span>
            </div>
            """, unsafe_allow_html=True)

            if not st.session_state.get("discovered_clips"):
                st.markdown("""
                <div class="powder-card">
                    <h4 style="margin: 0 0 8px 0; color: #f8fafc; font-size: 14px;">⚡ AI Highlight Scanner</h4>
                    <p style="color: #94a3b8; font-size: 12px; margin-bottom: 12px;">
                        Scans audio with Faster-Whisper on GPU & uses Ollama to find viral hooks, clutch gameplay, and laughter.
                    </p>
                </div>
                """, unsafe_allow_html=True)

                col_n, col_d = st.columns(2)
                with col_n:
                    clips_num = st.slider("Moments Count", 1, 5, 3)
                with col_d:
                    dur_bounds = st.slider("Target Duration", 15, 90, (20, 50), step=5)

                skip_intro = st.checkbox("✂️ Ignore Pre-Roll Intro in AI Scan", value=True)
                scan_start_sec = 0.0
                if skip_intro:
                    def_skip = int(st.session_state.get("snapshot_ts", 91.0))
                    scan_start_sec = st.number_input("Scan speech only after (seconds):", min_value=0, max_value=max(0, int(v_dur) - 10), value=min(int(v_dur) - 10, def_skip), step=5)
                    st.caption(f"AI will ignore 00:00 to {int(scan_start_sec//60):02d}:{int(scan_start_sec%60):02d} and only look for gameplay highlights.")

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
                                max_duration=dur_bounds[1],
                                scan_start=float(scan_start_sec)
                            )

                            st.session_state["discovered_clips"] = clips
                            st.session_state["selected_clip_indices"] = list(range(len(clips)))
                            st.success(f"Discovered {len(clips)} Highlights!")
                            st.rerun()

                        except Exception as ex:
                            st.error(f"Discovery error: {ex}")

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


# =============================================================
# SCREEN 2.7: LAYOUT & TEMPLATES (INTERACTIVE MOUSE DRAG CANVAS)
# =============================================================
elif st.session_state["current_nav"] == "Layout":
    st.markdown('<div class="top-header"><h2 class="top-title">🎛️ Visual Layout Alignment & Interactive Mouse Canvas</h2><div class="badge-gpu">Live Sync</div></div>', unsafe_allow_html=True)

    if not st.session_state["video_path"]:
        st.info("Please load a video in **📥 Capture & Ingest** first.")
    else:
        v_path = st.session_state["video_path"]
        v_name = os.path.basename(v_path)
        v_meta = st.session_state["video_meta"]
        v_w = v_meta.get("width", 1920)
        v_h = v_meta.get("height", 1080)
        v_dur = v_meta.get("duration", 0.0)

        # -----------------------------------------------------
        # 1. SCENE SCRUBBER (SOLVES INTRO WEBCAM VS GAMEPLAY SCENE!)
        # -----------------------------------------------------
        st.markdown("""
        <div class="powder-card">
            <h4 style="margin: 0 0 6px 0; color: #ccff00; font-size: 15px;">⏱️ Step 1: Scrub to Actual Gameplay Scene</h4>
            <p style="color: #94a3b8; font-size: 12px; margin: 0 0 10px 0;">
                If your video starts with a fullscreen webcam intro, scrub the slider to <b>45s or 120s</b> where the actual game + facecam is playing on screen!
            </p>
        </div>
        """, unsafe_allow_html=True)

        sc_col1, sc_col2 = st.columns([3, 1])
        with sc_col1:
            scrub_target = st.slider(
                "Gameplay Scene Timestamp (seconds):",
                0, int(v_dur),
                value=int(st.session_state.get("snapshot_ts", 45.0)),
                step=1
            )
        with sc_col2:
            if st.button("📸 Grab Frame at this Second", type="primary", use_container_width=True):
                st.session_state["snapshot_ts"] = float(scrub_target)
                v_base = os.path.splitext(v_name)[0]
                p_frame = os.path.join(cache_dir, f"{v_base}_preview.jpg")
                extract_preview_frame(v_path, p_frame, timestamp=float(scrub_target))
                st.session_state["preview_frame"] = p_frame
                st.success(f"Frame updated to {scrub_target}s!")
                st.rerun()

        # Quick Jump Buttons
        st.markdown("<div style='font-size: 12px; font-weight: 700; color: #cbd5e1; margin-bottom: 6px;'>Quick Scene Shortcuts:</div>", unsafe_allow_html=True)
        q1, q2, q3, q4, q5 = st.columns(5)
        with q1:
            if st.button("⏱️ Intro (5s)"):
                st.session_state["snapshot_ts"] = 5.0
                v_base = os.path.splitext(v_name)[0]
                p_frame = os.path.join(cache_dir, f"{v_base}_preview.jpg")
                extract_preview_frame(v_path, p_frame, timestamp=5.0)
                st.session_state["preview_frame"] = p_frame
                st.rerun()
        with q2:
            if st.button("🎮 Gameplay (45s)"):
                st.session_state["snapshot_ts"] = 45.0
                v_base = os.path.splitext(v_name)[0]
                p_frame = os.path.join(cache_dir, f"{v_base}_preview.jpg")
                extract_preview_frame(v_path, p_frame, timestamp=45.0)
                st.session_state["preview_frame"] = p_frame
                st.rerun()
        with q3:
            if st.button("🎮 Mid-Game (120s)"):
                st.session_state["snapshot_ts"] = 120.0
                v_base = os.path.splitext(v_name)[0]
                p_frame = os.path.join(cache_dir, f"{v_base}_preview.jpg")
                extract_preview_frame(v_path, p_frame, timestamp=120.0)
                st.session_state["preview_frame"] = p_frame
                st.rerun()
        with q4:
            if st.button("🎮 Clutch (250s)"):
                st.session_state["snapshot_ts"] = min(v_dur - 10, 250.0)
                v_base = os.path.splitext(v_name)[0]
                p_frame = os.path.join(cache_dir, f"{v_base}_preview.jpg")
                extract_preview_frame(v_path, p_frame, timestamp=st.session_state["snapshot_ts"])
                st.session_state["preview_frame"] = p_frame
                st.rerun()
        with q5:
            if st.button("🎮 Late-Match (400s)"):
                st.session_state["snapshot_ts"] = min(v_dur - 10, 400.0)
                v_base = os.path.splitext(v_name)[0]
                p_frame = os.path.join(cache_dir, f"{v_base}_preview.jpg")
                extract_preview_frame(v_path, p_frame, timestamp=st.session_state["snapshot_ts"])
                st.session_state["preview_frame"] = p_frame
                st.rerun()

        st.markdown("---")

        # -----------------------------------------------------
        # 2. SCREEN MODE SELECTION
        # -----------------------------------------------------
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

            st.markdown("""
            <div class="powder-card">
                <h4 style="margin: 0 0 6px 0; color: #ccff00; font-size: 15px;">🖱️ Step 2: 1-Click Streamer Presets & Mouse Drag Placement</h4>
                <p style="color: #94a3b8; font-size: 12px; margin: 0;">
                    Click a preset below or drag the boxes with your mouse on the video canvas to perfectly frame your facecam and gameplay crosshairs!
                </p>
            </div>
            """, unsafe_allow_html=True)

            # 1-Click Preset Buttons
            p_col1, p_col2, p_col3, p_col4, p_col5 = st.columns(5)
            with p_col1:
                if st.button("📌 Top-Right (Scout)", use_container_width=True):
                    st.session_state["fc_x"], st.session_state["fc_y"], st.session_state["fc_w"], st.session_state["fc_h"] = 65, 5, 32, 40
                    st.session_state["gp_x"], st.session_state["gp_y"], st.session_state["gp_w"], st.session_state["gp_h"] = 15, 0, 70, 100
                    st.rerun()
            with p_col2:
                if st.button("📌 Top-Left Facecam", use_container_width=True):
                    st.session_state["fc_x"], st.session_state["fc_y"], st.session_state["fc_w"], st.session_state["fc_h"] = 5, 5, 32, 40
                    st.session_state["gp_x"], st.session_state["gp_y"], st.session_state["gp_w"], st.session_state["gp_h"] = 15, 0, 70, 100
                    st.rerun()
            with p_col3:
                if st.button("📌 Center-Top (Spyki)", use_container_width=True):
                    st.session_state["fc_x"], st.session_state["fc_y"], st.session_state["fc_w"], st.session_state["fc_h"] = 28, 15, 44, 45
                    st.session_state["gp_x"], st.session_state["gp_y"], st.session_state["gp_w"], st.session_state["gp_h"] = 15, 0, 70, 100
                    st.rerun()
            with p_col4:
                if st.button("📌 Bottom-Right", use_container_width=True):
                    st.session_state["fc_x"], st.session_state["fc_y"], st.session_state["fc_w"], st.session_state["fc_h"] = 65, 55, 32, 40
                    st.session_state["gp_x"], st.session_state["gp_y"], st.session_state["gp_w"], st.session_state["gp_h"] = 15, 0, 70, 100
                    st.rerun()
            with p_col5:
                if st.button("📌 Bottom-Left", use_container_width=True):
                    st.session_state["fc_x"], st.session_state["fc_y"], st.session_state["fc_w"], st.session_state["fc_h"] = 5, 55, 32, 40
                    st.session_state["gp_x"], st.session_state["gp_y"], st.session_state["gp_w"], st.session_state["gp_h"] = 15, 0, 70, 100
                    st.rerun()

            # Numeric sliders for fine-tuning
            with st.expander("⚙️ Fine-Tune Sliders (Optional Sub-Pixel Adjustment)"):
                col_sl1, col_sl2 = st.columns(2)
                with col_sl1:
                    st.markdown("<b style='color: #00ff78;'>📷 Facecam Box (Top 40%)</b>", unsafe_allow_html=True)
                    st.session_state["fc_x"] = st.slider("Facecam X (%)", 0, 100, int(st.session_state["fc_x"]), key="f_sl_x")
                    st.session_state["fc_y"] = st.slider("Facecam Y (%)", 0, 100, int(st.session_state["fc_y"]), key="f_sl_y")
                    st.session_state["fc_w"] = st.slider("Facecam Width (%)", 15, 70, int(st.session_state["fc_w"]), key="f_sl_w")
                    st.session_state["fc_h"] = st.slider("Facecam Height (%)", 15, 70, int(st.session_state["fc_h"]), key="f_sl_h")
                with col_sl2:
                    st.markdown("<b style='color: #00d2ff;'>🎯 Gameplay Box (Bottom 60%)</b>", unsafe_allow_html=True)
                    st.session_state["gp_x"] = st.slider("Gameplay X (%)", 0, 100, int(st.session_state["gp_x"]), key="g_sl_x")
                    st.session_state["gp_y"] = st.slider("Gameplay Y (%)", 0, 100, int(st.session_state["gp_y"]), key="g_sl_y")
                    st.session_state["gp_w"] = st.slider("Gameplay Width (%)", 30, 100, int(st.session_state["gp_w"]), key="g_sl_w")
                    st.session_state["gp_h"] = st.slider("Gameplay Height (%)", 30, 100, int(st.session_state["gp_h"]), key="g_sl_h")

            # Calculate pixel bounds
            fc_px = int((st.session_state["fc_x"] / 100.0) * v_w)
            fc_py = int((st.session_state["fc_y"] / 100.0) * v_h)
            fc_pw = int((st.session_state["fc_w"] / 100.0) * v_w)
            fc_ph = int((st.session_state["fc_h"] / 100.0) * v_h)

            gp_px = int((st.session_state["gp_x"] / 100.0) * v_w)
            gp_py = int((st.session_state["gp_y"] / 100.0) * v_h)
            gp_pw = int((st.session_state["gp_w"] / 100.0) * v_w)
            gp_ph = int((st.session_state["gp_h"] / 100.0) * v_h)

            g_cfg = {
                "facecam": {"x": fc_px, "y": fc_py, "w": fc_pw, "h": fc_ph},
                "gameplay": {"x": gp_px, "y": gp_py, "w": gp_pw, "h": gp_ph},
                "top_height": 760
            }
            st.session_state["active_gaming_config"] = g_cfg

            # -------------------------------------------------
            # 3. INTERACTIVE MOUSE CANVAS & LIVE 9:16 SIMULATION
            # -------------------------------------------------
            st.markdown('<div style="font-size: 13px; font-weight: 700; color: #cbd5e1; margin: 16px 0 8px 0;">🔴 Live Visual Alignment Canvas & 9:16 Mockup</div>', unsafe_allow_html=True)
            vis_c1, vis_c2 = st.columns([14, 8])

            with vis_c1:
                b64_frame = get_base64_encoded_image(st.session_state["preview_frame"])
                if b64_frame:
                    fc_l_px = int(st.session_state["fc_x"] * 640 / 100)
                    fc_t_px = int(st.session_state["fc_y"] * 360 / 100)
                    fc_w_px = int(st.session_state["fc_w"] * 640 / 100)
                    fc_h_px = int(st.session_state["fc_h"] * 360 / 100)

                    gp_l_px = int(st.session_state["gp_x"] * 640 / 100)
                    gp_t_px = int(st.session_state["gp_y"] * 360 / 100)
                    gp_w_px = int(st.session_state["gp_w"] * 640 / 100)
                    gp_h_px = int(st.session_state["gp_h"] * 360 / 100)

                    html_canvas = f"""
                    <div style="font-family: sans-serif; user-select: none;">
                        <div id="c-wrap" style="position: relative; width: 640px; height: 360px; background: #000; border-radius: 8px; overflow: hidden; border: 2px solid #283147; box-shadow: 0 4px 16px rgba(0,0,0,0.5);">
                            <img src="data:image/jpeg;base64,{b64_frame}" style="width: 100%; height: 100%; object-fit: contain; pointer-events: none;" />
                            
                            <!-- Facecam Box (Green) -->
                            <div id="fc-box" style="position: absolute; border: 3px solid #00ff78; background: rgba(0, 255, 120, 0.22); cursor: move; box-sizing: border-box; left: {fc_l_px}px; top: {fc_t_px}px; width: {fc_w_px}px; height: {fc_h_px}px;">
                                <div style="position: absolute; top: 4px; left: 4px; background: rgba(0,0,0,0.85); color: #00ff78; font-size: 10px; font-weight: 800; padding: 2px 5px; border-radius: 3px; pointer-events: none;">
                                    📷 FACECAM (Top 40%)
                                </div>
                                <div id="fc-h" style="position: absolute; right: -5px; bottom: -5px; width: 12px; height: 12px; background: #00ff78; cursor: nwse-resize; border-radius: 2px;"></div>
                            </div>

                            <!-- Gameplay Box (Cyan) -->
                            <div id="gp-box" style="position: absolute; border: 3px solid #00d2ff; background: rgba(0, 210, 255, 0.16); cursor: move; box-sizing: border-box; left: {gp_l_px}px; top: {gp_t_px}px; width: {gp_w_px}px; height: {gp_h_px}px;">
                                <div style="position: absolute; top: 4px; left: 4px; background: rgba(0,0,0,0.85); color: #00d2ff; font-size: 10px; font-weight: 800; padding: 2px 5px; border-radius: 3px; pointer-events: none;">
                                    🎯 GAMEPLAY (Bottom 60%)
                                </div>
                                <div id="gp-h" style="position: absolute; right: -5px; bottom: -5px; width: 12px; height: 12px; background: #00d2ff; cursor: nwse-resize; border-radius: 2px;"></div>
                            </div>
                        </div>
                        <div style="font-size: 11px; color: #94a3b8; margin-top: 6px;">
                            💡 <b>Mouse Drag Enabled:</b> Click inside any box to move it freely; drag the corner handle to resize!
                        </div>
                    </div>

                    <script>
                    function attachDrag(boxId, handleId) {{
                        const box = document.getElementById(boxId);
                        const handle = document.getElementById(handleId);
                        const wrap = document.getElementById('c-wrap');
                        let isDragging = false, isResizing = false;
                        let startX, startY, startL, startT, startW, startH;

                        box.addEventListener('mousedown', function(e) {{
                            if (e.target === handle) return;
                            isDragging = true;
                            startX = e.clientX; startY = e.clientY;
                            startL = box.offsetLeft; startT = box.offsetTop;
                            e.preventDefault();
                        }});

                        handle.addEventListener('mousedown', function(e) {{
                            isResizing = true;
                            startX = e.clientX; startY = e.clientY;
                            startW = box.offsetWidth; startH = box.offsetHeight;
                            e.stopPropagation();
                            e.preventDefault();
                        }});

                        window.addEventListener('mousemove', function(e) {{
                            if (isDragging) {{
                                const dx = e.clientX - startX;
                                const dy = e.clientY - startY;
                                let nl = Math.max(0, Math.min(wrap.offsetWidth - box.offsetWidth, startL + dx));
                                let nt = Math.max(0, Math.min(wrap.offsetHeight - box.offsetHeight, startT + dy));
                                box.style.left = nl + 'px';
                                box.style.top = nt + 'px';
                            }} else if (isResizing) {{
                                const dx = e.clientX - startX;
                                const dy = e.clientY - startY;
                                let nw = Math.max(40, Math.min(wrap.offsetWidth - box.offsetLeft, startW + dx));
                                let nh = Math.max(40, Math.min(wrap.offsetHeight - box.offsetTop, startH + dy));
                                box.style.width = nw + 'px';
                                box.style.height = nh + 'px';
                            }}
                        }});

                        window.addEventListener('mouseup', function() {{
                            isDragging = false;
                            isResizing = false;
                        }});
                    }}
                    attachDrag('fc-box', 'fc-h');
                    attachDrag('gp-box', 'gp-h');
                    </script>
                    """
                    components.html(html_canvas, height=395)

            with vis_c2:
                mob_img = generate_mobile_preview(st.session_state["preview_frame"], g_cfg)
                if mob_img:
                    st.image(mob_img, caption="Live 9:16 Mobile Mockup", width=220)

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
                    st.info("AI Face-Tracker will automatically center the camera on whoever is talking.")

        else:
            st.session_state["active_layout"] = "blur_fit"
            st.info("Full 16:9 widescreen video stays crisp in center with ambient blurred background.")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✓ Save Layout & Return to Studio", type="primary", use_container_width=True):
            st.session_state["current_nav"] = "Studio"
            st.rerun()


# =============================================================
# SCREEN 2.8: CAPTIONS & STYLING
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
# SCREEN 2.3 & 2.11: CLIPS LIBRARY & EXPORT HUB
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
# SCREEN 3.1 & 3.6: SETTINGS, HARDWARE & SHORTCUTS
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
            <h4 style="margin: 0 0 10px 0; color: #38bdf8;">⌨️ Keyboard Shortcuts</h4>
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
