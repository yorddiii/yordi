"""Render an edit.json into a finished 9:16 ad in the "local-service talking-head" style.

    python3 render.py EDIT.json [--preview] [--from T --to T]

--preview renders at 540x960 with a fast encoder for quick review.

EDIT.json (paths relative to the file):
{
  "canvas": {"w": 1080, "h": 1920, "fps": 30},
  "grade": {"contrast": 1.04, "saturation": 1.1, "brightness": 0.0, "gamma": 1.0},
  "aroll": [   # talking head, concatenated in order; the voice track comes from here
    {"src": "raw/A.MOV", "in": 1.20, "out": 3.05, "zoom": 1.0, "focus": [0.5, 0.4],
     "join": "cut"}            # transition INTO this cut: cut | prism | flash | whip
  ],
  "inserts": [ # B-roll laid OVER the A-roll (voice keeps playing); times are output seconds
    {"start": 2.0, "end": 3.4, "src": "raw/B1.MOV", "in": 0.5, "zoom": 1.0, "focus": [0.5, 0.5],
     "speed": 1.0, "trans_in": "flash", "trans_out": "flash"},
    {"start": 2.0, "end": 3.4, "layout": "split",
     "top": {"src": "raw/B2.MOV", "in": 3.0}, "bottom": {"src": "raw/B3.MOV", "in": 0.0},
     "trans_in": "flash", "trans_out": "flash"}
  ],
  "captions": "captions.json",
  "music": {"src": "music.mp3", "gain_db": -21, "in": 0},   # optional, ducked under voice
  "voice_lufs": -16,
  "output": "out/final.mp4"
}
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
from common import FONT, load_json, need  # noqa: E402

CREAM = np.array([246, 220, 171], np.float32)
WHITE_TXT = (250, 250, 250)
ORANGE_TOP, ORANGE_BOT = (255, 200, 85), (238, 108, 0)


# ----------------------------------------------------------------------------- timeline
def build_timeline(edit, fps):
    """Return (video pieces, transition boundaries, aroll cuts with output frames, total frames)."""
    cuts, f = [], 0
    for c in edit["aroll"]:
        n = max(1, round((c["out"] - c["in"]) * fps))
        cuts.append(dict(c, f0=f, f1=f + n))
        f += n
    total = f
    inserts = []
    for ins in edit.get("inserts", []):
        f0, f1 = round(ins["start"] * fps), min(total, round(ins["end"] * fps))
        if f1 > f0:
            inserts.append(dict(ins, f0=f0, f1=f1))
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
        if i.get("trans_out", "cut") != "cut" and i["f1"] < total:
            bounds.append((i["f1"], i["trans_out"]))
    return merged, sorted(bounds), cuts, total


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


def open_piece(piece, base, W, H, fps, grade):
    n = piece["f1"] - piece["f0"]
    spec = piece["spec"]
    dur = n / fps + 0.5
    cmd = ["ffmpeg", "-loglevel", "error", "-nostdin"]
    if spec.get("layout") == "split":
        hh = (H - 12) // 2
        for k in ("top", "bottom"):
            part = spec[k]
            cmd += ["-ss", f"{part['t']:.3f}", "-t", f"{dur * part.get('speed', 1):.3f}",
                    "-i", os.path.join(base, part["src"])]
        a = vf_chain(dict(spec["top"], speed=spec["top"].get("speed", 1)), W, hh, fps, grade)
        b = vf_chain(dict(spec["bottom"], speed=spec["bottom"].get("speed", 1)), W, hh, fps, grade)
        fc = (f"[0:v]{a}[a];[1:v]{b}[b];color=c=white:s={W}x12:r={fps}[d];"
              f"[a][d][b]vstack=3,crop={W}:{H}:0:0,format=rgb24[v]")
        cmd += ["-filter_complex", fc, "-map", "[v]"]
    else:
        cmd += ["-ss", f"{spec['t']:.3f}", "-t", f"{dur * spec.get('speed', 1):.3f}",
                "-i", os.path.join(base, spec["src"]), "-vf", vf_chain(spec, W, H, fps, grade)]
    cmd += ["-an", "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE), n


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
    """Frame-level light-leak / flash / whip effects measured from the reference ad."""

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
        return img

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
class Captions:
    """Word-by-word reveal captions: white line + orange gradient emphasis line,
    each word slides/blur-fades in from the right in ~0.13s and stays until the page ends."""

    ENTER = 0.13

    def __init__(self, data, W, H, scale):
        self.W, self.H, self.s = W, H, scale
        st = data.get("style", {})
        self.size = st.get("size", 69)
        self.y = st.get("y", 0.525)
        self.items = []  # (start, end, appear, x, y, sprite RGBA float32)
        for page in data.get("pages", []):
            self._layout(page, st)

    def _font(self, px):
        return ImageFont.truetype(FONT, max(8, int(px)))

    def _sprite(self, text, font, color):
        asc, desc = font.getmetrics()
        pad = int(14 * self.s)
        w = int(font.getlength(text)) + 2 * pad
        h = asc + desc + 2 * pad
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).text((pad, pad), text, font=font, fill=255)
        if color == "orange":
            top, bot = ORANGE_TOP, ORANGE_BOT
            y0, y1 = pad + int(asc * 0.25), pad + asc
            t = np.clip((np.arange(h) - y0) / max(1, y1 - y0), 0, 1)[:, None]
            fill = np.stack([np.repeat(top[i] + (bot[i] - top[i]) * t, w, axis=1)
                             for i in range(3)], -1)
            shadow_rgb, shadow_a = (70, 25, 0), 0.75
        else:
            fill = np.broadcast_to(np.array(WHITE_TXT, np.float32), (h, w, 3))
            shadow_rgb, shadow_a = (0, 0, 0), 0.55
        m = np.asarray(mask, np.float32) / 255
        sh = mask.filter(ImageFilter.GaussianBlur(4 * self.s))
        off = int(3 * self.s)
        sh = np.roll(np.asarray(sh, np.float32) / 255, off, axis=0) * shadow_a
        a = m + sh * (1 - m)
        rgb = (fill * m[..., None] + np.array(shadow_rgb, np.float32) * (sh * (1 - m))[..., None])
        rgb = rgb / np.maximum(a, 1e-4)[..., None]
        return np.dstack([rgb, a * 255]).astype(np.float32), pad

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

    def _layout(self, page, st):
        start, end = page["start"], page["end"]
        y_c = page.get("y", self.y) * self.H
        lines = []
        for ln in page["lines"]:
            color = ln.get("color", "white")
            px = ln.get("size", self.size * (1.1 if color == "orange" else 1.0)) * self.s
            font = self._font(px)
            space = font.getlength(" ")
            widths = [font.getlength(w["t"]) for w in ln["words"]]
            total = sum(widths) + space * (len(widths) - 1)
            max_w = self.W * 0.88
            if total > max_w:  # shrink to fit
                px *= max_w / total
                font = self._font(px)
                space = font.getlength(" ")
                widths = [font.getlength(w["t"]) for w in ln["words"]]
                total = sum(widths) + space * (len(widths) - 1)
            lines.append((ln, color, font, px, widths, total, space))
        heights = [px * 0.98 for _, _, _, px, _, _, _ in lines]
        y = y_c - sum(heights) / 2
        for (ln, color, font, px, widths, total, space), lh in zip(lines, heights):
            x = (self.W - total) / 2
            asc, _ = font.getmetrics()
            for w, ww in zip(ln["words"], widths):
                spr, pad = self._sprite(w["t"], font, color)
                top = y + lh * 0.5 - (asc * 0.62) - pad  # optical centre on cap height
                self.items.append((start, end, w.get("s", start), x - pad, top, spr))
                x += ww + space
            y += lh
        if page.get("icon") == "pin":
            ln, color, font, px, widths, total, space = lines[0]
            pin = self._pin(px * 0.95)
            x = (self.W - total) / 2 - pin.shape[1] - px * 0.15
            self.items.append((start, end, start, x, y_c - sum(heights) / 2 - px * 0.15, pin))

    def draw(self, img, t):
        for start, end, appear, x, y, spr in self.items:
            if not (start <= t < end) or t < appear:
                continue
            p = min(1.0, (t - appear) / self.ENTER)
            e = 1 - (1 - p) ** 3
            alpha = e
            dx = (1 - e) * 0.045 * self.W
            s = spr
            blur = int((1 - e) * 36 * self.s)
            if blur > 1:
                pad = np.pad(s, ((0, 0), (blur, blur), (0, 0)))
                c = np.cumsum(pad, axis=1, dtype=np.float64)
                s = ((c[:, blur * 2:] - c[:, :-blur * 2]) / (2 * blur)).astype(np.float32)
                s = s[:, :spr.shape[1]] if s.shape[1] >= spr.shape[1] else spr
            self._blit(img, s, x + dx, y, alpha)

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
def build_audio(edit, base, cuts, fps, total, tmp, f_from, f_to):
    parts, labels = [], []
    srcs = []
    for c in cuts:
        if c["f1"] <= f_from or c["f0"] >= f_to:
            continue
        a0 = c["in"] + max(0, f_from - c["f0"]) / fps
        a1 = c["in"] + (min(f_to, c["f1"]) - c["f0"]) / fps
        srcs += ["-ss", f"{a0:.3f}", "-t", f"{a1 - a0:.3f}", "-i", os.path.join(base, c["src"])]
        k = len(labels)
        d = a1 - a0
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
               f"[voice]asplit[v1][v2];[mus][v2]sidechaincompress=threshold=0.04:ratio=5:"
               f"attack=20:release=300[duck];[v1][duck]amix=inputs=2:normalize=0:duration=first[mix]")
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
    pieces, bounds, cuts, total = build_timeline(edit, fps)
    f_from = round(a.t_from * fps)
    f_to = min(total, round(a.t_to * fps)) if a.t_to else total
    cap = edit.get("captions")
    caps = Captions(load_json(os.path.join(base, cap)) if isinstance(cap, str) else (cap or {}),
                    W, H, scale)
    trans = Transitions(W, H, fps)
    grade = edit.get("grade", {"contrast": 1.04, "saturation": 1.08})
    out = a.out or os.path.join(base, edit.get("output", "out/final.mp4"))
    if a.preview and not a.out:
        out = os.path.splitext(out)[0] + "_preview.mp4"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        wav = build_audio(edit, base, cuts, fps, total, tmp, f_from, f_to)
        enc = ["ffmpeg", "-loglevel", "error", "-nostdin", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-i", wav, "-map", "0:v", "-map", "1:a",
               "-c:v", "libx264", "-preset", "veryfast" if a.preview else "medium",
               "-crf", "23" if a.preview else "17", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
        writer = subprocess.Popen(enc, stdin=subprocess.PIPE)
        frame_bytes = W * H * 3
        done = 0
        for p in pieces:
            if p["f1"] <= f_from or p["f0"] >= f_to:
                continue
            lo, hi = max(p["f0"], f_from), min(p["f1"], f_to)
            p = dict(p, spec=dict(p["spec"]))
            skip = (lo - p["f0"]) / fps
            if skip:
                if p["spec"].get("layout") == "split":
                    for k in ("top", "bottom"):
                        p["spec"][k] = dict(p["spec"][k], t=p["spec"][k]["t"] + skip *
                                            p["spec"][k].get("speed", 1))
                else:
                    p["spec"]["t"] += skip * p["spec"].get("speed", 1)
            p["f0"], p["f1"] = lo, hi
            proc, n = open_piece(p, base, W, H, fps, grade)
            last = None
            for i in range(n):
                buf = proc.stdout.read(frame_bytes)
                if len(buf) == frame_bytes:
                    last = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
                elif last is None:
                    last = np.zeros((H, W, 3), np.uint8)
                fi = p["f0"] + i
                img = last.astype(np.float32)
                for bf, kind in bounds:
                    rel = (fi - bf) / fps
                    if -0.35 < rel < 0.35:
                        img = trans.apply(img, kind, rel)
                caps.draw(img, fi / fps)
                writer.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes())
                done += 1
            proc.stdout.close()
            proc.wait()
            print(f"\rrendered {done}/{f_to - f_from} frames", end="", file=sys.stderr)
        writer.stdin.close()
        writer.wait()
    print(f"\n-> {out} ({(f_to - f_from) / fps:.2f}s)")


if __name__ == "__main__":
    main()
