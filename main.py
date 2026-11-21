import copy
import math
import re
import threading
import time
import flet as ft


CLIP_COLORS = {
    "None": "#333338",
    "Orange": "#E67E22",
    "Teal": "#1ABC9C",
    "Purple": "#9B59B6",
    "Lime": "#2ECC71",
    "Blue": "#3498DB",
    "Pink": "#E84393",
}

COLOR_LOOKS = {
    "Default": {"lift": 0.0, "gamma": 1.0, "gain": 1.0, "sat": 1.0, "tint": "#1A2332"},
    "Anime Pop": {"lift": 0.04, "gamma": 1.15, "gain": 1.2, "sat": 1.55, "tint": "#3B185F"},
    "Cyberpunk": {"lift": -0.02, "gamma": 1.2, "gain": 1.15, "sat": 1.45, "tint": "#0D3B66"},
    "Teal & Orange": {"lift": 0.01, "gamma": 1.1, "gain": 1.12, "sat": 1.3, "tint": "#134E5E"},
    "Warm": {"lift": 0.03, "gamma": 1.05, "gain": 1.08, "sat": 1.2, "tint": "#4A2511"},
    "Dramatic": {"lift": -0.06, "gamma": 1.3, "gain": 1.1, "sat": 0.85, "tint": "#1C1C24"},
    "B&W": {"lift": 0.0, "gamma": 1.25, "gain": 1.1, "sat": 0.0, "tint": "#222225"},
}

FUSION_NODE_CATALOG = [
    {"type": "4K UltraSmooth AI", "category": "Custom AI", "color": "#D32F2F", "param_name": "4K Sharpness & Smooth", "default_val": 90, "desc": "Upscales to 3840x2160 4K + 60fps Optical Flow smoothing"},
    {"type": "PuppetPin3D", "category": "3D Mesh", "color": "#AD1457", "param_name": "Mesh Bend Stiffness", "default_val": 75, "desc": "3D mesh warp pins to bend & keyframe limbs/objects in X/Y/Z"},
    {"type": "Camera3D", "category": "3D", "color": "#00838F", "param_name": "Camera Field of View", "default_val": 50, "desc": "3D virtual camera with FOV, Z-depth & perspective control"},
    {"type": "ImagePlane3D", "category": "3D", "color": "#00695C", "param_name": "3D Plane Depth Scale", "default_val": 100, "desc": "Places 2D video clip into full 3D X/Y/Z space"},
    {"type": "Shape3D", "category": "3D", "color": "#0277BD", "param_name": "3D Subdivisions", "default_val": 64, "desc": "3D cube, sphere, cylinder & plane geometry generator"},
    {"type": "Merge3D", "category": "3D", "color": "#00897B", "param_name": "3D Scene Blend", "default_val": 100, "desc": "Combines multiple 3D cameras, lights & objects into one scene"},
    {"type": "PointLight3D", "category": "3D", "color": "#F57F17", "param_name": "Light Intensity", "default_val": 85, "desc": "3D scene lighting with shadow & intensity control"},
    {"type": "Renderer3D", "category": "3D", "color": "#283593", "param_name": "Supersampling AA", "default_val": 80, "desc": "Renders 3D scene camera view back into 2D 4K output"},
    {"type": "Transform", "category": "2D", "color": "#2980B9", "param_name": "2D Zoom Scale", "default_val": 100, "desc": "2D Position, Zoom, Rotation, Anchor & Flip"},
    {"type": "ColorCorrector", "category": "Color", "color": "#8E44AD", "param_name": "Node Gain Boost", "default_val": 60, "desc": "Node-based Hue, Saturation, Contrast & Gain"},
    {"type": "OpticalFlow", "category": "Retime", "color": "#16A085", "param_name": "Motion Vector Smooth", "default_val": 95, "desc": "Motion-estimated frame interpolation for silky smooth motion"},
    {"type": "Merge", "category": "Composite", "color": "#D35400", "param_name": "Foreground Opacity", "default_val": 100, "desc": "Combines Foreground over Background with blend modes"},
    {"type": "Blur / Glow", "category": "Filter", "color": "#2C3E50", "param_name": "Glow Bloom Intensity", "default_val": 45, "desc": "Gaussian blur and cinematic highlight bloom"},
    {"type": "DeltaKeyer", "category": "Matte", "color": "#27AE60", "param_name": "Key Matte Clean", "default_val": 80, "desc": "Clean green/blue screen chroma key extraction"},
    {"type": "Text+", "category": "Generator", "color": "#C0392B", "param_name": "3D Extrusion Depth", "default_val": 40, "desc": "3D extruded vector title & anime caption typography"},
    {"type": "Tracker", "category": "Tracking", "color": "#546E7A", "param_name": "Track Confidence", "default_val": 90, "desc": "Point & planar motion tracking for callouts"},
]

DEFAULT_STATE = {
    "media_pool": [],
    "active_clip": None,
    "cursor_tool": "select",
    "selected_item": "3D Mesh Plane",
    "playhead_sec": 0.0,
    "is_playing": False,
    "trim_start": 0.0,
    "trim_end": 15.0,
    "bpm": 128,
    "speed_pct": 100.0,
    "markers": [],
    "timeline_cuts": [],
    "keyframes": [],
    "fusion_nodes": [
        {"id": 1, "type": "MediaIn1", "category": "I/O", "color": "#3A3A40", "enabled": True, "param_name": "Input Gain", "param_val": 100, "desc": "Source Timeline Clip Input"},
        {"id": 2, "type": "ImagePlane3D", "category": "3D", "color": "#00695C", "enabled": True, "param_name": "3D Plane Depth Scale", "param_val": 100, "desc": "Maps clip onto 3D X/Y/Z plane"},
        {"id": 3, "type": "PuppetPin3D", "category": "3D Mesh", "color": "#AD1457", "enabled": True, "param_name": "Mesh Bend Stiffness", "param_val": 75, "desc": "3D Mesh Puppet Pin Deformation"},
        {"id": 4, "type": "Blur / Glow", "category": "Filter", "color": "#2C3E50", "enabled": True, "param_name": "Glow Bloom Intensity", "param_val": 45, "desc": "Cinematic highlight bloom & glow"},
        {"id": 5, "type": "Renderer3D", "category": "3D", "color": "#283593", "enabled": True, "param_name": "Supersampling AA", "param_val": 80, "desc": "Renders 3D space through Camera3D"},
        {"id": 6, "type": "4K UltraSmooth AI", "category": "Custom AI", "color": "#D32F2F", "enabled": True, "param_name": "4K Sharpness & Smooth", "param_val": 90, "desc": "3840x2160 4K Upscale + 60fps Optical Flow Smooth"},
        {"id": 7, "type": "MediaOut1", "category": "I/O", "color": "#3A3A40", "enabled": True, "param_name": "Output Bitrate %", "param_val": 100, "desc": "Final Timeline Output"},
    ],
    "selected_node_id": 6,
    "ultra_4k_enabled": True,
    "smooth_60fps_enabled": True,
    "puppet_pins": [
        {"id": 1, "name": "Pin 1 (Head)", "x": 0.0, "y": -20.0, "z": 15.0},
        {"id": 2, "name": "Pin 2 (Core)", "x": 0.0, "y": 15.0, "z": 0.0},
    ],
    "selected_pin_id": 1,
    "pos_x": 0.0,
    "pos_y": 0.0,
    "pos_z": 0.0,
    "rot_x": 0.0,
    "rot_y": 0.0,
    "rot_z": 0.0,
    "active_look": "Anime Pop",
    "lift": 0.04,
    "gamma": 1.15,
    "gain": 1.2,
    "sat": 1.55,
    "volume": 100,
    "voice_isolation": True,
    "dialogue_leveler": False,
    "normalize_audio": True,
    "export_res": "3840x2160 (4K UltraSmooth 60fps)",
    "export_codec": "H.265 (HEVC 10-bit)",
    "render_history": [],
}


def main(page: ft.Page):
    page.title = "Resolve Studio 3D Pro"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#121214"
    page.padding = 0
    page.spacing = 0

    state = copy.deepcopy(DEFAULT_STATE)
    try:
        saved = page.client_storage.get("resolve_pro_v5")
        if isinstance(saved, dict):
            for k, v in saved.items():
                if k in state:
                    state[k] = v
            state["is_playing"] = False
    except Exception:
        pass

    def persist_state():
        try:
            page.client_storage.set("resolve_pro_v5", state)
        except Exception:
            pass

    def safe_float(val, default=0.0):
        try:
            return max(0.0, float(val))
        except (ValueError, TypeError):
            return default

    def safe_int(val, default=128):
        try:
            return max(40, min(260, int(float(val))))
        except (ValueError, TypeError):
            return default

    def format_tc(seconds: float) -> str:
        total_frames = int(round(seconds * 60))
        ff = total_frames % 60
        total_sec = total_frames // 60
        ss = total_sec % 60
        mm = (total_sec // 60) % 60
        hh = total_sec // 3600
        return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"

    def notify(msg: str, color: str = "#2E7D32"):
        snack = ft.SnackBar(ft.Text(msg, color="#FFFFFF", size=12), bgcolor=color, duration=1800)
        page.overlay.append(snack)
        snack.open = True
        page.update()

    # --- KEYFRAME INTERPOLATION ENGINE ---
    def apply_keyframes_at_time(t: float):
        kfs = sorted(state["keyframes"], key=lambda k: k["time"])
        if not kfs:
            return
        if t <= kfs["time"]:
            chosen = kfs
        elif t >= kfs[-1]["time"]:
            chosen = kfs[-1]
        else:
            chosen = kfs
            for i in range(len(kfs) - 1):
                k1, k2 = kfs[i], kfs[i + 1]
                if k1["time"] <= t <= k2["time"]:
                    span = max(0.001, k2["time"] - k1["time"])
                    alpha = (t - k1["time"]) / span
                    smooth_a = alpha * alpha * (3 - 2 * alpha)
                    chosen = {
                        "pos_z": round(k1["pos_z"] + (k2["pos_z"] - k1["pos_z"]) * smooth_a, 1),
                        "rot_y": round(k1["rot_y"] + (k2["rot_y"] - k1["rot_y"]) * smooth_a, 1),
                        "pin_x": round(k1["pin_x"] + (k2["pin_x"] - k1["pin_x"]) * smooth_a, 1),
                        "pin_y": round(k1["pin_y"] + (k2["pin_y"] - k1["pin_y"]) * smooth_a, 1),
                    }
                    break
        state["pos_z"] = chosen["pos_z"]
        state["rot_y"] = chosen["rot_y"]
        active_pin = next((p for p in state["puppet_pins"] if p["id"] == state["selected_pin_id"]), None)
        if active_pin:
            active_pin["x"] = chosen["pin_x"]
            active_pin["y"] = chosen["pin_y"]

    def add_keyframe_at_playhead():
        t = round(state["playhead_sec"], 1)
        active_pin = next((p for p in state["puppet_pins"] if p["id"] == state["selected_pin_id"]), {"x": 0.0, "y": 0.0})
        state["keyframes"] = [k for k in state["keyframes"] if abs(k["time"] - t) > 0.05]
        state["keyframes"].append({
            "time": t,
            "pos_z": state["pos_z"],
            "rot_y": state["rot_y"],
            "pin_x": active_pin["x"],
            "pin_y": active_pin["y"],
        })
        persist_state()
        refresh_current_page()
        notify(f"Added 3D Keyframe ◆ at {t}s!", "#F57F17")

