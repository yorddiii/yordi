"""Catalogue a folder of raw clips before editing.

    python3 ingest.py RAW_DIR --work WORK_DIR [--no-transcribe]

For every video in RAW_DIR writes
  WORK/sheets/<clip>.png        timestamped contact sheet (1 frame/sec, tiled)
  WORK/words/<clip>.json        word timestamps (clips with speech)
  WORK/ingest.md                one section per clip: specs + indexed transcript
Open each sheet with the image viewer to learn what every B-roll clip shows and
where the talking-head takes are; read ingest.md to pick the clean takes.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import need, probe, run  # noqa: E402

EXTS = (".mov", ".mp4", ".m4v", ".mkv", ".avi", ".webm", ".mts")


def sheet(path, out, dur):
    per = max(1.0, dur / 48)  # at most ~48 tiles
    n = int(dur / per) + 1
    cols = 8
    rows = (n + cols - 1) // cols
    run(["ffmpeg", "-loglevel", "error", "-y", "-i", path, "-vf",
         f"fps=1/{per:.3f},scale=180:-2,drawtext=text='%{{pts\\:hms}}':x=3:y=3:fontsize=14:"
         f"fontcolor=yellow:box=1:boxcolor=black@0.7,tile={cols}x{rows}", "-frames:v", "1", out])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw")
    ap.add_argument("--work", required=True)
    ap.add_argument("--no-transcribe", action="store_true")
    a = ap.parse_args()
    need("ffmpeg")
    os.makedirs(os.path.join(a.work, "sheets"), exist_ok=True)
    os.makedirs(os.path.join(a.work, "words"), exist_ok=True)
    clips = sorted(f for f in os.listdir(a.raw) if f.lower().endswith(EXTS))
    md = ["# Raw clip catalogue", ""]
    for name in clips:
        path = os.path.join(a.raw, name)
        info = probe(path)
        stem = os.path.splitext(name)[0]
        sheet(path, os.path.join(a.work, "sheets", stem + ".png"), info["duration"])
        md += [f"## {name}", "",
               f"- {info.get('width')}x{info.get('height')} @ {info.get('fps')} fps, "
               f"{info['duration']:.2f}s, audio: {info['has_audio']}",
               f"- sheet: sheets/{stem}.png"]
        if info["has_audio"] and not a.no_transcribe:
            from transcribe import transcribe
            words = transcribe(path)
            json.dump(words, open(os.path.join(a.work, "words", stem + ".json"), "w"))
            md.append(f"- {len(words)} words (words/{stem}.json)")
            if words:
                md += ["", "```"]
                line = []
                for i, w in enumerate(words):
                    if i and w["s"] - words[i - 1]["e"] > 0.35:
                        md.append(" ".join(line))
                        md.append(f"   ~ pause {w['s'] - words[i - 1]['e']:.2f}s")
                        line = []
                    line.append(f"[{i}]{w['w']}@{w['s']:.2f}")
                md += [" ".join(line), "```"]
        md.append("")
        print(f"ingested {name}", file=sys.stderr)
    with open(os.path.join(a.work, "ingest.md"), "w") as f:
        f.write("\n".join(md))
    print(os.path.join(a.work, "ingest.md"))


if __name__ == "__main__":
    main()
