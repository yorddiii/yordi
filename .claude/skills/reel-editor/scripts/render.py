"""Render an edit.json into a finished 9:16 ad.

    python3 render.py EDIT.json [--preview] [--from T --to T] [--out FILE]

--preview renders at 540x960 with a fast encoder for quick review.

EDIT.json (paths relative to the file; all times in OUTPUT seconds unless noted):
{
  "canvas": {"w": 1080, "h": 1920, "fps": 30},
  "grade": {"contrast": 1.04, "saturation": 1.1, "brightness": 0.0, "gamma": 1.0},
  "aroll": [   # concatenated in order; the voice track comes only from here
    {"src": "raw/A.MOV", "in": 1.20, "out": 3.05, "zoom": 1.0, "focus": [0.5, 0.4],
     "join": "cut"},           # transition INTO this cut: cut | prism | flash | whip | spin
    {"gap": 4.3}               # voice-less stretch (music-only montage); cover it with inserts
  ],
  "inserts": [ # laid OVER the A-roll timeline; the voice keeps playing underneath
    {"start": 2.0, "end": 3.4, "src": "raw/B1.MOV", "in": 0.5, "zoom": 1.0, "focus": [0.5, 0.5],
     "speed": 1.0, "trans_in": "flash", "trans_out": "flash"},
    {"start": 2.0, "end": 3.4, "layout": "split",
     "top": {"src": "raw/B2.MOV", "in": 3.0}, "bottom": {"src": "raw/B3.MOV", "in": 0.0},
     "trans_in": "flash", "trans_out": "flash"},
    {"start": 13.0, "end": 14.1, "layout": "pip", "src": "raw/macro.MOV", "in": 0,
     "rect": [0.17, 0.30, 0.66, 0.27],        # x, y, w, h as fractions of the frame
     "fade_in": 0.0, "fade_out": 0.12, "opacity": 1.0}   # floats over whatever is below
  ],
  "fade_in": 0.1,              # from black at the start (seconds)
  "fade_out": 0.3,             # to black, ending where the tail starts
  "tail": 0.6,                 # black hold appended at the end
  "captions": "captions.json", # see Captions below
  "music": {"src": "music.mp3", "gain_db": -21, "in": 0},   # optional, ducked under voice
  "voice_lufs": -16,
  "output": "out/final.mp4"
}

captions.json:
{
  "style": {"preset": "bold" | "mixed", ...any preset key below to override...},
  "pages": [
    {"start": 0.1, "end": 2.0, "y": 0.525, "x": 0.5, "icon": "pin", "fade_out": 0.15,
     "lines": [
       {"color": "white", "words": [{"t": "ABILENE", "s": 0.12}, {"t": "RESIDENTS", "s": 0.42}]},
       {"color": "orange", "font": "expanded", "scale": 1.1, "dx": 0.0, "enter": "right",
        "words": [{"t": "IF", "s": 0.78}, {"t": "paint", "s": 0.9, "font": "extrabold-italic",
                   "scale": 2.0, "sweep": true}]}
     ]}
  ]
}
colors: white | orange (gradient) | "#RRGGBB"
fonts : expanded (Saira ExtraBold Expanded) | light-italic | regular | semibold-italic |
        bold | extrabold-italic (Open Sans)
enter : right | left | up | pop        sweep: teal->violet highlight travelling over the word
"""
import argparse
import math
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import FONTS, load_json, need  # noqa: E402

CREAM = np.array([246, 220, 171], np.float32)
WHITE_TXT = (250, 250, 250)
ORANGE_TOP, ORANGE_BOT = (255, 200, 85), (238, 108, 0)
SWEEP_A, SWEEP_B = np.array([70, 205, 235], np.float32), np.array([165, 115, 255], np.float32)

PRESETS = {
    # ref 01: Eurostile-like caps, white line + orange payoff line, hard page swaps
    "bold": {"font": "expanded", "size": 69, "y": 0.525, "shadow": 0.55, "enter": "right",
             "enter_dur": 0.13, "fade_out": 0.0, "line_gap": 0.98, "orange_scale": 1.1},
    # ref 02: mixed-weight humanist sans, small light-italic connectors + big bold keywords
    # measured sizes at 1080 wide: connectors light-italic x0.78 (~80px), keywords bold x1.2
    # (~125px), one hero word extrabold-italic x2.3 (~240px)
    "mixed": {"font": "regular", "size": 104, "y": 0.5, "shadow": 0.45, "enter": "left",
              "enter_dur": 0.15, "fade_out": 0.15, "line_gap": 0.86, "orange_scale": 1.0},
}


# ----------------------------------------------------------------------------- timeline
def build_timeline(edit, fps):
    """Return (video pieces, transition boundaries, aroll cuts, pips, content frames, total frames)."""
    cuts, f = [], 0
    aroll = list(edit["aroll"])
    for c in aroll:
        if "gap" in c:
            n = max(1, round(c["gap"] * fps))
        else:
            n = max(1, round((c["out"] - c["in"]) * fps))
        cuts.append(dict(c, f0=f, f1=f + n))
        f += n
    content = f
    tail = round(edit.get("tail", 0) * fps)
    if tail:
        cuts.append({"gap": tail / fps, "f0": f, "f1": f + tail, "tail": True})
        f += tail
    total = f
    inserts, pips = [], []
    for ins in edit.get("inserts", []):
        f0, f1 = round(ins["start"] * fps), min(content, round(ins["end"] * fps))
        if f1 <= f0:
            continue
        (pips if ins.get("layout") == "pip" else inserts).append(dict(ins, f0=f0, f1=f1))
    marks = sorted({0, total, *[c["f0"] for c in cuts], *[i["f0"] for i in inserts],
                    *[i["f1"] for i in inserts]})
    pieces = []
    for a, b in zip(marks, marks[1:]):
        if b <= a:
            continue
        top = next((i for i in reversed(inserts) if i["f0"] <= a < i["f1"]), None)
        if top is not None:
            src = dict(top, t=top.get("in", 0) + (a - top["f0"]) / fps * top.get("speed", 1.0))
            if top.get("layout") == "split":
                for k in ("top", "bottom"):
                    part = top[k]
                    src[k] = dict(part, t=part.get("in", 0) + (a - top["f0"]) / fps *
                                  part.get("speed", top.get("speed", 1.0)))
            pieces.append({"f0": a, "f1": b, "kind": "insert", "spec": src})
        else:
            c = next(c for c in cuts if c["f0"] <= a < c["f1"])
            if "gap" in c:
                pieces.append({"f0": a, "f1": b, "kind": "black", "spec": {}})
            else:
                pieces.append({"f0": a, "f1": b, "kind": "aroll",
                               "spec": dict(c, t=c["in"] + (a - c["f0"]) / fps)})
    # merge neighbouring pieces that are one continuous source (split by an unrelated mark)
    merged = []
    for p in pieces:
        q = merged[-1] if merged else None
        if q and q["kind"] == p["kind"] and q["spec"].get("src") == p["spec"].get("src") and \
                q["spec"].get("f0") == p["spec"].get("f0") and q["spec"].get("in") == p["spec"].get("in"):
            q["f1"] = p["f1"]
        else:
            merged.append(p)
    bounds = []
    for c in cuts[1:]:
        covered = any(i["f0"] < c["f0"] < i["f1"] for i in inserts)
        if c.get("join", "cut") != "cut" and not covered:
            bounds.append((c["f0"], c["join"]))
    for i in inserts:
        if i.get("trans_in", "cut") != "cut":
            bounds.append((i["f0"], i["trans_in"]))
        if i.get("trans_out", "cut") != "cut" and i["f1"] < content:
            bounds.append((i["f1"], i["trans_out"]))
    return merged, sorted(bounds), cuts, pips, content, total


# ----------------------------------------------------------------------------- video in
def vf_chain(spec, W, H, fps, grade):
    z = float(spec.get("zoom", 1.0))
    fx, fy = spec.get("focus", [0.5, 0.5])
    speed = float(spec.get("speed", 1.0))
    f = [f"setpts=(PTS-STARTPTS)/{speed}" if speed != 1 else "setpts=PTS-STARTPTS",
         f"fps={fps}",
         f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos",
         f"crop={W}:{H}:(iw-{W})*{fx}:(ih-{H})*{fy}"]
    if z != 1.0:
        f += [f"crop=iw/{z}:ih/{z}:(iw-iw/{z})*{fx}:(ih-ih/{z})*{fy}",
              f"scale={W}:{H}:flags=lanczos"]
    if grade:
        f.append("eq=contrast={c}:saturation={s}:brightness={b}:gamma={g}".format(
            c=grade.get("contrast", 1), s=grade.get("saturation", 1),
            b=grade.get("brightness", 0), g=grade.get("gamma", 1)))
    f.append("setsar=1,format=rgb24")
    return ",".join(f)


class Reader:
    """Streams exactly n RGB frames of one source spec (repeats the last frame if it runs out)."""

    def __init__(self, spec, base, W, H, fps, grade, n):
        self.W, self.H, self.n = W, H, n
        self.last = None
        self.proc = None
        if not spec:
            return
        dur = n / fps + 0.5
        cmd = ["ffmpeg", "-loglevel", "error", "-nostdin"]
        if spec.get("layout") == "split":
            hh = (H - 12) // 2
            for k in ("top", "bottom"):
                part = spec[k]
                cmd += ["-ss", f"{part['t']:.3f}", "-t", f"{dur * part.get('speed', 1):.3f}",
                        "-i", os.path.join(base, part["src"])]
            a = vf_chain(spec["top"], W, hh, fps, grade)
            b = vf_chain(spec["bottom"], W, hh, fps, grade)
            fc = (f"[0:v]{a}[a];[1:v]{b}[b];color=c=white:s={W}x12:r={fps}[d];"
                  f"[a][d][b]vstack=3,crop={W}:{H}:0:0,format=rgb24[v]")
            cmd += ["-filter_complex", fc, "-map", "[v]"]
        else:
            cmd += ["-ss", f"{spec['t']:.3f}", "-t", f"{dur * spec.get('speed', 1):.3f}",
                    "-i", os.path.join(base, spec["src"]), "-vf", vf_chain(spec, W, H, fps, grade)]
        cmd += ["-an", "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)

    def read(self):
        if self.proc is not None:
            buf = self.proc.stdout.read(self.W * self.H * 3)
            if len(buf) == self.W * self.H * 3:
                self.last = np.frombuffer(buf, np.uint8).reshape(self.H, self.W, 3)
        if self.last is None:
            self.last = np.zeros((self.H, self.W, 3), np.uint8)
        return self.last

    def close(self):
        if self.proc is not None:
            self.proc.stdout.close()
            self.proc.wait()


def shifted_spec(spec, skip):
    spec = dict(spec)
    if not skip or not spec:
        return spec
    if spec.get("layout") == "split":
        for k in ("top", "bottom"):
            spec[k] = dict(spec[k], t=spec[k]["t"] + skip * spec[k].get("speed", 1))
    else:
        spec["t"] += skip * spec.get("speed", 1)
    return spec


# ----------------------------------------------------------------------------- transitions
def _gradient(W, H, stops, angle_deg, shift):
    """Diagonal multi-stop gradient image, positions shifted by `shift`."""
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    a = math.radians(angle_deg)
    u = (xs / W) * math.cos(a) + (ys / H) * math.sin(a)
    u = (u - u.min()) / (u.max() - u.min()) + shift
    pos = np.array([s[0] for s in stops], np.float32)
    out = np.zeros((H, W, 3), np.float32)
    for ch in range(3):
        out[..., ch] = np.interp(u, pos, np.array([s[1][ch] for s in stops], np.float32))
    return out


class Transitions:
    """Frame-level effects around a boundary, measured from the reference ads."""

    def __init__(self, W, H, fps):
        self.W, self.H, self.fps = W, H, fps
        sw, sh = W // 4, H // 4  # gradients are smooth: build small, upscale once
        self._leak = self._up(_gradient(sw, sh, [(0, (255, 120, 40)), (0.45, (255, 170, 90)),
                                                 (1.0, (255, 110, 175))], 60, 0))
        self._prism = [self._up(_gradient(sw, sh, [(-1, (255, 150, 60)), (-0.3, (255, 150, 60)),
                                                   (0.2, (200, 140, 255)), (0.6, (255, 160, 150)),
                                                   (1.2, (255, 190, 120)), (2, (255, 190, 120))],
                                          35, s)) for s in np.linspace(-0.6, 0.6, 7)]

    def _up(self, g):
        return np.asarray(Image.fromarray(g.clip(0, 255).astype(np.uint8)).resize(
            (self.W, self.H), Image.BILINEAR)).astype(np.float32)

    @staticmethod
    def _screen(img, col, a):
        return img + (255 - img) * (col / 255.0) * a

    def apply(self, img, kind, rel):
        """img float32 HxWx3; rel = seconds from the boundary (negative = before)."""
        if kind == "flash":
            if not -0.14 <= rel <= 0.30:
                return img
            leak = np.interp(rel, [-0.14, -0.02, 0.06, 0.30], [0, 0.75, 0.6, 0])
            flash = np.interp(rel, [-0.07, -0.015, 0.03, 0.09], [0, 1, 1, 0])
            expo = np.interp(rel, [-0.14, -0.03, 0.0], [1, 1.18, 1.18]) if rel < 0 else 1
            img = np.clip(img * expo, 0, 255)
            img = self._screen(img, self._leak, leak)
            return img * (1 - flash) + CREAM * flash
        if kind == "prism":
            if not -0.06 <= rel <= 0.17:
                return img
            a = np.interp(rel, [-0.06, 0.0, 0.08, 0.17], [0, 0.8, 0.8, 0])
            k = int(np.clip(np.interp(rel, [-0.06, 0.17], [0, 6.99]), 0, 6))
            g = self._prism[k]
            return img * (1 - a * 0.5) + g * (a * 0.5) + (255 - img) * (g / 255) * a * 0.25
        if kind == "whip":
            if not -0.07 <= rel <= 0.13:
                return img
            s = np.interp(rel, [-0.07, -0.01, 0.0, 0.05, 0.13], [0, 0.10, 0.28, 0.10, 0])
            shift = np.interp(rel, [0, 0.13], [-0.12, 0]) if rel >= 0 else \
                np.interp(rel, [-0.07, 0], [0, 0.10])
            return self._vblur(img, int(s * self.H), int(shift * self.H))
        if kind == "spin":
            if not -0.07 <= rel <= 0.17:
                return img
            ang = np.interp(rel, [-0.07, 0.0], [0, -14]) if rel < 0 else \
                np.interp(rel, [0, 0.17], [24, 0]) * (1 - rel / 0.17) ** 0.5
            return self._spin(img, float(ang))
        return img

    def _spin(self, img, ang):
        """Rotate + zoom with a rotational smear (3 taps), corners kept covered by zoom."""
        if abs(ang) < 0.3:
            return img
        src = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
        z = 1.0 + abs(ang) / 24 * 0.5
        cx, cy = self.W / 2, self.H / 2
        acc = np.zeros_like(img)
        taps = (ang - abs(ang) * 0.35, ang, ang + abs(ang) * 0.35)
        for a in taps:
            r = math.radians(a)
            ca, sa = math.cos(r) / z, math.sin(r) / z
            data = (ca, sa, cx - ca * cx - sa * cy, -sa, ca, cy + sa * cx - ca * cy)
            acc += np.asarray(src.transform((self.W, self.H), Image.AFFINE, data, Image.BILINEAR),
                              np.float32)
        return acc / len(taps)

    @staticmethod
    def _vblur(img, length, shift):
        if shift:  # slide with edge clamp (no wrap-around)
            idx = np.clip(np.arange(img.shape[0]) - shift, 0, img.shape[0] - 1)
            img = img[idx]
        if length < 2:
            return img
        pad = np.pad(img, ((length, length), (0, 0), (0, 0)), mode="edge")
        c = np.cumsum(pad, axis=0, dtype=np.float64)
        h = img.shape[0]
        half = length // 2
        lo = np.arange(h) + length - half
        hi = lo + length
        return ((c[hi] - c[lo]) / length).astype(np.float32)


# ----------------------------------------------------------------------------- captions
def _hblur(s, blur):
    pad = np.pad(s, ((0, 0), (blur, blur), (0, 0)))
    c = np.cumsum(pad, axis=1, dtype=np.float64)
    return ((c[:, blur * 2:] - c[:, :-blur * 2]) / (2 * blur)).astype(np.float32)[:, :s.shape[1]]


def _vblur_s(s, blur):
    pad = np.pad(s, ((blur, blur), (0, 0), (0, 0)))
    c = np.cumsum(pad, axis=0, dtype=np.float64)
    return ((c[blur * 2:] - c[:-blur * 2]) / (2 * blur)).astype(np.float32)[:s.shape[0]]


class Word:
    def __init__(self, page, appear, x, y, rgba, mask=None, shadow=None, shadow_rgb=None,
                 enter="right", sweep=False):
        self.start, self.end = page["start"], page["end"]
        self.fade_out = page["_fade_out"]
        self.appear, self.x, self.y, self.rgba = appear, x, y, rgba
        self.mask, self.shadow, self.shadow_rgb = mask, shadow, shadow_rgb
        self.enter, self.sweep = enter, sweep


class Captions:
    """Word-by-word captions. Every word sits at its final layout position from the start of
    its page and enters (slide + motion blur + fade) on its own spoken time."""

    def __init__(self, data, W, H, scale):
        self.W, self.H, self.s = W, H, scale
        st = dict(PRESETS[data.get("style", {}).get("preset", "bold")])
        st.update(data.get("style", {}))
        self.st = st
        self.items = []
        self._fonts = {}
        for page in data.get("pages", []):
            self._layout(page)

    def _font(self, key, px):
        k = (key, int(px))
        if k not in self._fonts:
            self._fonts[k] = ImageFont.truetype(FONTS[key], max(8, int(px)))
        return self._fonts[k]

    def _sprite(self, text, font, color):
        asc, desc = font.getmetrics()
        pad = int(16 * self.s) + int(font.size * 0.12)
        w = int(font.getlength(text)) + 2 * pad
        h = asc + desc + 2 * pad
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).text((pad, pad), text, font=font, fill=255)
        shadow_a = self.st["shadow"]
        if color == "orange":
            top, bot = ORANGE_TOP, ORANGE_BOT
            y0, y1 = pad + int(asc * 0.25), pad + asc
            t = np.clip((np.arange(h) - y0) / max(1, y1 - y0), 0, 1)[:, None]
            fill = np.stack([np.repeat(top[i] + (bot[i] - top[i]) * t, w, axis=1)
                             for i in range(3)], -1)
            shadow_rgb, shadow_a = np.array((70, 25, 0), np.float32), max(shadow_a, 0.75)
        else:
            rgb = WHITE_TXT if color in (None, "white") else tuple(
                int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
            fill = np.broadcast_to(np.array(rgb, np.float32), (h, w, 3))
            shadow_rgb = np.zeros(3, np.float32)
        m = np.asarray(mask, np.float32) / 255
        sh = mask.filter(ImageFilter.GaussianBlur(max(2, font.size * 0.07)))
        off = max(1, int(font.size * 0.045))
        sh = np.roll(np.asarray(sh, np.float32) / 255, off, axis=0) * shadow_a
        return self._compose(fill, m, sh, shadow_rgb), pad, m, sh, shadow_rgb

    @staticmethod
    def _compose(fill, m, sh, shadow_rgb):
        a = m + sh * (1 - m)
        rgb = fill * m[..., None] + shadow_rgb * (sh * (1 - m))[..., None]
        rgb = rgb / np.maximum(a, 1e-4)[..., None]
        return np.dstack([rgb, a * 255]).astype(np.float32)

    def _pin(self, px):
        s = int(px)
        img = Image.new("RGBA", (s, int(s * 1.35)), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        r = s // 2 - 1
        d.ellipse((1, 1, 1 + 2 * r, 1 + 2 * r), fill=(225, 30, 40, 255))
        d.polygon([(s * 0.14, s * 0.62), (s * 0.86, s * 0.62), (s / 2, s * 1.33)], fill=(225, 30, 40, 255))
        q = s * 0.2
        d.ellipse((s / 2 - q, r + 1 - q, s / 2 + q, r + 1 + q), fill=(120, 0, 10, 255))
        return np.asarray(img, np.float32)

    def _word_px(self, ln, w, color):
        base = self.st["size"] * (self.st["orange_scale"] if color == "orange" else 1.0)
        px = w.get("size", ln.get("size", base * ln.get("scale", 1.0) * w.get("scale", 1.0)))
        return px * self.s

    def _layout(self, page):
        page["_fade_out"] = page.get("fade_out", self.st["fade_out"])
        y_c = page.get("y", self.st["y"]) * self.H
        x_c = page.get("x", 0.5) * self.W
        lines = []
        for ln in page["lines"]:
            color = ln.get("color", "white")
            words = []
            for w in ln["words"]:
                fk = w.get("font", ln.get("font", self.st["font"]))
                px = self._word_px(ln, w, w.get("color", color))
                words.append([w, fk, px])
            for _ in range(2):  # shrink to fit
                fonts = [self._font(fk, px) for _, fk, px in words]
                spaces = [f.getlength(" ") for f in fonts]
                widths = [f.getlength(w["t"]) for (w, _, _), f in zip(words, fonts)]
                total = sum(widths) + sum(spaces[:-1])
                if total <= self.W * 0.9:
                    break
                for wd in words:
                    wd[2] *= self.W * 0.9 / total
            lh = max(px for _, _, px in words) * self.st["line_gap"]
            lines.append((ln, color, words, fonts, widths, spaces, total, lh))
        y = y_c - sum(ln[-1] for ln in lines) / 2
        for ln, color, words, fonts, widths, spaces, total, lh in lines:
            align = ln.get("align", "center")
            dx = ln.get("dx", 0) * self.W
            x = {"left": x_c - self.W * 0.42, "right": x_c + self.W * 0.42 - total}.get(
                align, x_c - total / 2) + dx
            base_y = y + lh * 0.78  # shared baseline for mixed sizes
            for (w, fk, px), font, ww, sp in zip(words, fonts, widths, spaces):
                col = w.get("color", color)
                rgba, pad, m, sh, srgb = self._sprite(w["t"], font, col)
                asc, _ = font.getmetrics()
                top = base_y - asc - pad
                self.items.append(Word(page, w.get("s", page["start"]), x - pad, top, rgba, m, sh, srgb,
                                       w.get("enter", ln.get("enter", self.st["enter"])),
                                       w.get("sweep", False)))
                x += ww + sp
            y += lh
        if page.get("icon") == "pin":
            ln, color, words, fonts, widths, spaces, total, lh = lines[0]
            pin = self._pin(lh * 0.95)
            x = x_c - total / 2 - pin.shape[1] - lh * 0.15
            self.items.append(Word(page, page["start"], x, y_c - sum(l[-1] for l in lines) / 2 - lh * 0.1,
                                   pin, enter="pop"))

    def _sweep(self, it, t):
        q = float(np.clip((t - it.appear) / 0.6, 0, 1))
        c = -0.2 + q * 1.05  # band centre travels across and settles on the last letters
        h, w = it.mask.shape
        u = np.arange(w, dtype=np.float32) / w
        k = np.clip(1 - np.abs(u - c) / 0.35, 0, 1)[None, :, None]
        g = (SWEEP_A + (SWEEP_B - SWEEP_A) * np.clip((u - c + 0.35) / 0.7, 0, 1)[:, None])[None]
        fill = np.array(WHITE_TXT, np.float32) * (1 - k) + g * k
        return self._compose(np.broadcast_to(fill, (h, w, 3)), it.mask, it.shadow, it.shadow_rgb)

    def draw(self, img, t):
        dur = self.st["enter_dur"]
        for it in self.items:
            if not (it.start <= t < it.end) or t < it.appear:
                continue
            e = 1 - (1 - min(1.0, (t - it.appear) / dur)) ** 3
            alpha = e
            if it.fade_out:
                alpha *= min(1.0, (it.end - t) / it.fade_out)
            s = self._sweep(it, t) if it.sweep else it.rgba
            x, y = it.x, it.y
            blur = int((1 - e) * 36 * self.s)
            if it.enter in ("right", "left"):
                x += (1 - e) * 0.045 * self.W * (1 if it.enter == "right" else -1)
                if blur > 1:
                    s = _hblur(s, blur)
            elif it.enter == "up":
                y += (1 - e) * 0.025 * self.H
                if blur > 1:
                    s = _vblur_s(s, blur)
            elif it.enter == "pop" and e < 1:
                k = 1 + (1 - e) * 0.35
                h0, w0 = s.shape[:2]
                big = np.asarray(Image.fromarray(s.astype(np.uint8), "RGBA").resize(
                    (int(w0 * k), int(h0 * k)), Image.BILINEAR), np.float32)
                x -= (big.shape[1] - w0) / 2
                y -= (big.shape[0] - h0) / 2
                s = _hblur(big, blur) if blur > 1 else big
            self._blit(img, s, x, y, alpha)

    @staticmethod
    def _blit(img, spr, x, y, alpha):
        H, W = img.shape[:2]
        x, y = int(round(x)), int(round(y))
        h, w = spr.shape[:2]
        x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        s = spr[y0 - y:y1 - y, x0 - x:x1 - x]
        a = s[..., 3:4] / 255 * alpha
        region = img[y0:y1, x0:x1]
        img[y0:y1, x0:x1] = region * (1 - a) + s[..., :3] * a


# ----------------------------------------------------------------------------- audio
def build_audio(edit, base, cuts, fps, tmp, f_from, f_to):
    parts, labels, srcs = [], [], []
    for c in cuts:
        if c["f1"] <= f_from or c["f0"] >= f_to:
            continue
        k = len(labels)
        if "gap" in c:
            d = (min(f_to, c["f1"]) - max(f_from, c["f0"])) / fps
            srcs += ["-f", "lavfi", "-t", f"{d:.4f}", "-i", "anullsrc=r=48000:cl=stereo"]
            parts.append(f"[{k}:a]atrim=0:{d:.4f},asetpts=PTS-STARTPTS[a{k}]")
        else:
            a0 = c["in"] + max(0, f_from - c["f0"]) / fps
            a1 = c["in"] + (min(f_to, c["f1"]) - c["f0"]) / fps
            d = a1 - a0
            srcs += ["-ss", f"{a0:.3f}", "-t", f"{d:.3f}", "-i", os.path.join(base, c["src"])]
            parts.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,"
                         f"atrim=0:{d:.4f},asetpts=PTS-STARTPTS,"
                         f"afade=t=in:d=0.012,afade=t=out:st={max(0, d - 0.015):.4f}:d=0.015[a{k}]")
        labels.append(f"[a{k}]")
    dur = (f_to - f_from) / fps
    lufs = edit.get("voice_lufs", -16)
    fc = ";".join(parts) + f";{''.join(labels)}concat=n={len(labels)}:v=0:a=1," \
        f"highpass=f=70,acompressor=threshold=0.12:ratio=3:attack=5:release=80:makeup=1.5," \
        f"loudnorm=I={lufs}:TP=-1.5:LRA=9,aresample=48000,apad,atrim=0:{dur:.4f}[voice]"
    out = "[voice]"
    m = edit.get("music")
    if m:
        k = len(labels)
        srcs += ["-stream_loop", "-1", "-ss", str(m.get("in", 0)), "-i", os.path.join(base, m["src"])]
        g = m.get("gain_db", -21)
        fc += (f";[{k}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{dur:.4f},"
               f"volume={g}dB,afade=t=out:st={max(0, dur - 1.0):.3f}:d=1.0[mus];"
               f"[voice]asplit[v1][v2];[mus][v2]sidechaincompress=threshold=0.04:ratio="
               f"{m.get('duck_ratio', 5)}:attack=20:release=300[duck];"
               f"[v1][duck]amix=inputs=2:normalize=0:duration=first[mix]")
        out = "[mix]"
    wav = os.path.join(tmp, "audio.wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-nostdin", "-y", *srcs, "-filter_complex", fc,
                    "-map", out, "-c:a", "pcm_s16le", wav], check=True)
    return wav


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--from", dest="t_from", type=float, default=0)
    ap.add_argument("--to", dest="t_to", type=float)
    ap.add_argument("--out")
    a = ap.parse_args()
    need("ffmpeg")
    base = os.path.dirname(os.path.abspath(a.edit))
    edit = load_json(a.edit)
    cv = edit.get("canvas", {})
    W, H, fps = cv.get("w", 1080), cv.get("h", 1920), cv.get("fps", 30)
    if a.preview:
        W, H = W // 2, H // 2
    scale = W / 1080
    pieces, bounds, cuts, pips, content, total = build_timeline(edit, fps)
    f_from = round(a.t_from * fps)
    f_to = min(total, round(a.t_to * fps)) if a.t_to else total
    cap = edit.get("captions")
    caps = Captions(load_json(os.path.join(base, cap)) if isinstance(cap, str) else (cap or {}),
                    W, H, scale)
    trans = Transitions(W, H, fps)
    grade = edit.get("grade", {"contrast": 1.04, "saturation": 1.08})
    fade_in = round(edit.get("fade_in", 0) * fps)
    fade_out = round(edit.get("fade_out", 0) * fps)
    out = a.out or os.path.join(base, edit.get("output", "out/final.mp4"))
    if a.preview and not a.out:
        out = os.path.splitext(out)[0] + "_preview.mp4"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    pip_readers = {}
    with tempfile.TemporaryDirectory() as tmp:
        wav = build_audio(edit, base, cuts, fps, tmp, f_from, f_to)
        enc = ["ffmpeg", "-loglevel", "error", "-nostdin", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-i", wav, "-map", "0:v", "-map", "1:a",
               "-c:v", "libx264", "-preset", "veryfast" if a.preview else "medium",
               "-crf", "23" if a.preview else "17", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
        writer = subprocess.Popen(enc, stdin=subprocess.PIPE)
        done = 0
        for p in pieces:
            if p["f1"] <= f_from or p["f0"] >= f_to:
                continue
            lo, hi = max(p["f0"], f_from), min(p["f1"], f_to)
            spec = shifted_spec(p["spec"], (lo - p["f0"]) / fps) if p["kind"] != "black" else {}
            reader = Reader(spec, base, W, H, fps, grade, hi - lo)
            for fi in range(lo, hi):
                img = reader.read().astype(np.float32)
                for bf, kind in bounds:
                    rel = (fi - bf) / fps
                    if -0.35 < rel < 0.35:
                        img = trans.apply(img, kind, rel)
                for k, pip in enumerate(pips):
                    if not pip["f0"] <= fi < pip["f1"]:
                        if k in pip_readers and fi >= pip["f1"]:
                            pip_readers.pop(k).close()
                        continue
                    x, y, w, h = pip["rect"]
                    pw, ph = int(w * W) // 2 * 2, int(h * H) // 2 * 2
                    if k not in pip_readers:
                        t0 = pip.get("in", 0) + (fi - pip["f0"]) / fps * pip.get("speed", 1)
                        pip_readers[k] = Reader(dict(pip, t=t0), base, pw, ph, fps, grade, pip["f1"] - fi)
                    frame = pip_readers[k].read().astype(np.float32)
                    al = pip.get("opacity", 1.0)
                    if pip.get("fade_in"):
                        al *= min(1, (fi - pip["f0"] + 1) / (pip["fade_in"] * fps))
                    if pip.get("fade_out"):
                        al *= min(1, (pip["f1"] - fi) / (pip["fade_out"] * fps))
                    x0, y0 = int(x * W), int(y * H)
                    reg = img[y0:y0 + ph, x0:x0 + pw]
                    img[y0:y0 + ph, x0:x0 + pw] = reg * (1 - al) + frame[:reg.shape[0], :reg.shape[1]] * al
                if fi < content:
                    caps.draw(img, fi / fps)
                if fade_in and fi < fade_in:
                    img *= fi / fade_in
                if fade_out and content - fade_out <= fi:
                    img *= max(0.0, (content - fi) / fade_out)
                writer.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes())
                done += 1
            reader.close()
            print(f"\rrendered {done}/{f_to - f_from} frames", end="", file=sys.stderr)
        for r in pip_readers.values():
            r.close()
        writer.stdin.close()
        writer.wait()
    print(f"\n-> {out} ({(f_to - f_from) / fps:.2f}s)")


if __name__ == "__main__":
    main()
