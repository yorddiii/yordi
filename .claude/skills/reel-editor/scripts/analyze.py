"""Break a video down so its edit can be studied (new reference ads) or reviewed (our renders).

    python3 analyze.py VIDEO --out DIR [--fps 2] [--transcribe]

Writes into DIR:
  sheet_NN.png      timestamped contact sheets (6x3 tiles, default 2 frames/sec)
  report.md         cut list, flash/leak transitions, pacing stats, loudness, transcript
  words.json        (with --transcribe)
Read the sheets with the image viewer, then zoom into anything interesting with
  python3 analyze.py VIDEO --out DIR --strip START DUR   (every frame, 7x2 tiles)
"""
import argparse
import os
import re
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import need, probe, run  # noqa: E402

CREAM = np.array([246, 220, 171], float)


def sheets(video, out, fps):
    tiles = 18
    run(["ffmpeg", "-loglevel", "error", "-y", "-i", video, "-vf",
         f"fps={fps},scale=240:-2,drawtext=text='%{{pts\\:hms}}':x=4:y=4:fontsize=16:"
         f"fontcolor=yellow:box=1:boxcolor=black@0.7,tile=6x3", "-frames:v",
         str(int(probe(video)["duration"] * fps / tiles) + 1), os.path.join(out, "sheet_%02d.png")])


def strip(video, out, start, dur):
    path = os.path.join(out, f"strip_{start:.2f}.png")
    run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(start), "-t", str(dur), "-i", video,
         "-vf", "scale=160:-2,drawtext=text='%{pts\\:flt}':x=2:y=2:fontsize=14:fontcolor=yellow:"
         "box=1:boxcolor=black,tile=7x2", "-frames:v", "1", path])
    print(path)


def frames_small(video):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", video, "-vf", "scale=48:86",
                          "-pix_fmt", "rgb24", "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 86, 48, 3).astype(float)


def analyze_cuts(video, fps):
    a = frames_small(video)
    d = np.abs(np.diff(a, axis=0)).mean(axis=(1, 2, 3))
    med = np.median(d)
    events, i = [], 0
    while i < len(d):
        if d[i] > max(12, 4 * med):
            j = i
            while j + 1 < len(d) and d[j + 1] > max(10, 3 * med):
                j += 1
            seg = a[i:j + 2]
            mean = seg.mean(axis=(1, 2))
            std = seg.std(axis=(1, 2, 3))
            flash = any(np.abs(m - CREAM).max() < 30 and s < 40 for m, s in zip(mean, std))
            purple = any(m[2] > m[1] + 30 and m[0] > 190 for m in mean)
            kind = "flash/leak" if flash else "prism-leak" if purple else (
                "hard cut" if j == i else f"{j - i + 1}-frame transition (whip/blur/zoom?)")
            events.append((i + 1, (i + 1) / fps, kind))
            i = j + 1
        i += 1
    return events, len(a)


def loudness(video):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", video, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    rms = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", video, "-af",
                          "asetnsamples=4410,astats=metadata=1:reset=1,ametadata=print:"
                          "key=lavfi.astats.Overall.RMS_level:file=-", "-f", "null", "-"],
                         capture_output=True, text=True).stdout
    v = sorted(float(x) for x in re.findall(r"RMS_level=(-?[\d.]+)", rms))
    return (m[-1] if m else "?"), (v[len(v) // 20] if v else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=float, default=2)
    ap.add_argument("--transcribe", action="store_true")
    ap.add_argument("--strip", nargs=2, type=float, metavar=("START", "DUR"))
    a = ap.parse_args()
    need("ffmpeg")
    os.makedirs(a.out, exist_ok=True)
    if a.strip:
        return strip(a.video, a.out, *a.strip)
    info = probe(a.video)
    sheets(a.video, a.out, a.fps)
    events, n = analyze_cuts(a.video, info.get("fps") or 30)
    lufs, floor = loudness(a.video)
    shots = [0] + [t for _, t, _ in events] + [info["duration"]]
    lens = np.diff(shots)
    rep = [f"# Analysis of {os.path.basename(a.video)}", "",
           f"- {info.get('width')}x{info.get('height')} @ {info.get('fps')} fps, "
           f"{info['duration']:.2f}s, {n} frames",
           f"- {len(events)} cuts/transitions; avg shot {lens.mean():.2f}s, "
           f"median {np.median(lens):.2f}s, shortest {lens.min():.2f}s",
           f"- integrated loudness {lufs} LUFS; 5th-percentile RMS {floor:.0f} dB "
           "(above about -40 dB between words means a music bed is under the voice)", "",
           "## Cut list", "", "| frame | time | kind |", "|---|---|---|"]
    rep += [f"| {f} | {t:.2f} | {k} |" for f, t, k in events]
    if a.transcribe:
        from transcribe import transcribe
        import json
        words = transcribe(a.video)
        json.dump(words, open(os.path.join(a.out, "words.json"), "w"))
        rep += ["", "## Transcript (auto, proof-read it)", "",
                " ".join(f"{w['w']}@{w['s']:.1f}" for w in words)]
    with open(os.path.join(a.out, "report.md"), "w") as f:
        f.write("\n".join(rep) + "\n")
    print("\n".join(rep))
    print(f"\nsheets + report in {a.out}")


if __name__ == "__main__":
    main()
