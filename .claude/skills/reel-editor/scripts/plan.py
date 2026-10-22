"""Turn chosen talking-head takes into a tight A-roll timeline plus a caption draft.

    python3 plan.py PLAN.json

PLAN.json:
{
  "raw_dir": "raw",                     # relative to the plan file
  "work": "work",
  "edit": "edit.json",                  # written (aroll + empty inserts) unless it exists; see --force
  "captions": "captions.json",          # written with --captions (or when missing)
  "takes": [                            # in story order; word indices from ingest.md
    {"clip": "IMG_0001.MOV", "from": 0, "to": 14},
    {"clip": "IMG_0003.MOV", "from": 2, "to": 40, "drop": [17, 18]}   # drop = flubbed word indices
  ],
  "max_pause": 0.22,                    # longer silences inside a take are cut out (jump cut)
  "zooms": [1.0, 1.15]                  # alternated at every jump cut, like the reference
}

Prints every word with its OUTPUT time, so B-roll inserts can be placed on the exact
words they illustrate. Re-running regenerates aroll in edit.json while keeping its
inserts/music/etc.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_json, save_json  # noqa: E402

PAD_IN, PAD_OUT = 0.07, 0.09


def build_aroll(plan, base):
    words_dir = os.path.join(base, plan.get("work", "work"), "words")
    max_pause = plan.get("max_pause", 0.22)
    zooms = plan.get("zooms", [1.0, 1.15])
    cuts, tl_words, t_out, zi = [], [], 0.0, 0
    for take in plan["takes"]:
        stem = os.path.splitext(take["clip"])[0]
        words = load_json(os.path.join(words_dir, stem + ".json"))
        drop = set(take.get("drop", []))
        idx = [i for i in range(take["from"], take["to"] + 1) if i not in drop]
        # split into runs of words with no long pause / dropped word between them
        runs, cur = [], [idx[0]]
        for i in idx[1:]:
            prev = cur[-1]
            if i != prev + 1 or words[i]["s"] - words[prev]["e"] > max_pause:
                runs.append(cur)
                cur = [i]
            else:
                cur.append(i)
        runs.append(cur)
        for r_i, run_ in enumerate(runs):
            t_in = max(0.0, words[run_[0]]["s"] - PAD_IN)
            t_end = words[run_[-1]]["e"] + PAD_OUT
            cut = {"src": os.path.join(plan.get("raw_dir", "raw"), take["clip"]),
                   "in": round(t_in, 3), "out": round(t_end, 3),
                   "zoom": zooms[zi % len(zooms)], "focus": take.get("focus", [0.5, 0.4]),
                   "join": "cut"}
            zi += 1
            cuts.append(cut)
            for i in run_:
                w = words[i]
                tl_words.append({"w": w["w"], "s": round(t_out + w["s"] - t_in, 3),
                                 "e": round(t_out + w["e"] - t_in, 3),
                                 "phrase_end": i == run_[-1]})
            t_out += t_end - t_in
    return cuts, tl_words, t_out


def draft_captions(words, total):
    """Greedy pages: line 1 white, line 2 orange, broken at phrase ends, like the reference."""
    pages, page, line = [], [], []

    def chars(ws):
        return sum(len(w["t"]) for w in ws) + max(0, len(ws) - 1)

    def close_line():
        nonlocal line
        if line:
            page.append({"color": "white" if not page else "orange", "words": line})
            line = []

    def close_page():
        nonlocal page
        close_line()
        if page:
            pages.append({"lines": page})
            page = []

    for w in words:
        tok = {"t": w["w"].upper(), "s": w["s"]}
        if line and (chars(line + [tok]) > 15 or len(line) >= 3):
            close_line()
            if len(page) >= 2:
                close_page()
        line.append(tok)
        if w["phrase_end"]:
            close_page()
    close_page()
    for i, p in enumerate(pages):
        p["start"] = p["lines"][0]["words"][0]["s"]
        nxt = pages[i + 1]["lines"][0]["words"][0]["s"] if i + 1 < len(pages) else total
        p["end"] = round(nxt, 3)
    return {"style": {"size": 69, "y": 0.525}, "pages": pages}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--captions", action="store_true", help="(re)write the caption draft")
    ap.add_argument("--force", action="store_true", help="rewrite edit.json from scratch")
    a = ap.parse_args()
    base = os.path.dirname(os.path.abspath(a.plan))
    plan = load_json(a.plan)
    cuts, words, total = build_aroll(plan, base)
    edit_path = os.path.join(base, plan.get("edit", "edit.json"))
    edit = {} if a.force or not os.path.exists(edit_path) else load_json(edit_path)
    edit.setdefault("canvas", {"w": 1080, "h": 1920, "fps": 30})
    edit["aroll"] = cuts
    edit.setdefault("inserts", [])
    edit.setdefault("captions", plan.get("captions", "captions.json"))
    edit.setdefault("output", "out/final.mp4")
    save_json(edit, edit_path)
    save_json(words, os.path.join(base, plan.get("work", "work"), "timeline_words.json"))
    cap_path = os.path.join(base, plan.get("captions", "captions.json"))
    if a.captions or not os.path.exists(cap_path):
        save_json(draft_captions(words, total), cap_path)
        print(f"caption draft -> {cap_path}")
    print(f"{len(cuts)} A-roll cuts, {total:.2f}s -> {edit_path}\n")
    line = []
    for w in words:
        line.append(f"{w['w']}@{w['s']:.2f}")
        if w["phrase_end"]:
            print(" ".join(line) + "  |")
            line = []


if __name__ == "__main__":
    main()
