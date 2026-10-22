"""Shared helpers for the reel-editor scripts (ffmpeg/ffprobe wrappers, paths)."""
import json
import os
import shutil
import subprocess
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(SKILL_DIR, "assets")
FONT = os.path.join(ASSETS, "fonts", "Saira-ExtraBold-Expanded.ttf")
CACHE = os.path.expanduser(os.environ.get("REEL_CACHE", "~/.cache/reel-editor"))


def need(binary):
    if not shutil.which(binary):
        sys.exit(f"error: '{binary}' not found on PATH")


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        sys.exit(f"command failed: {' '.join(cmd)}\n{r.stderr[-2000:]}")
    return r.stdout


def probe(path):
    """Return duration, display size (rotation applied), fps and whether it has audio."""
    out = json.loads(run(["ffprobe", "-v", "error", "-print_format", "json",
                          "-show_format", "-show_streams", path]))
    v = next((s for s in out["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in out["streams"] if s["codec_type"] == "audio"), None)
    info = {"path": path, "duration": float(out["format"].get("duration", 0)),
            "has_audio": a is not None}
    if v:
        w, h = v["width"], v["height"]
        rot = 0
        for sd in v.get("side_data_list", []):
            if "rotation" in sd:
                rot = int(sd["rotation"])
        rot = int(v.get("tags", {}).get("rotate", rot))
        if abs(rot) % 180 == 90:
            w, h = h, w
        num, den = v.get("avg_frame_rate", "0/1").split("/")
        info.update(width=w, height=h, fps=round(float(num) / float(den or 1), 3))
    return info


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(obj, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)
