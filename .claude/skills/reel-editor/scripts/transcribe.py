"""Word-level transcription with timestamps (offline, Vosk).

    python3 transcribe.py CLIP [--out words.json]

Writes [{"w": "word", "s": start, "e": end}, ...] and prints the transcript with
word indices and pauses so takes can be picked by index.

The small English Vosk model is looked up in $REEL_VOSK_MODEL or
~/.cache/reel-editor/vosk-model-small-en-us-0.15. If it is missing it is pulled
from the npm registry (package `transcribe2texts` bundles it), because model
hosts like huggingface/alphacephei are often blocked in sandboxes.
The small model mishears brand names, prices and places: always proof-read the
words against what you can see/infer before using them for captions.
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CACHE, need, run  # noqa: E402

MODEL_NAME = "vosk-model-small-en-us-0.15"


def ensure_model():
    path = os.environ.get("REEL_VOSK_MODEL") or os.path.join(CACHE, MODEL_NAME)
    if os.path.isdir(path):
        return path
    need("npm")
    os.makedirs(CACHE, exist_ok=True)
    print("fetching Vosk model via npm (transcribe2texts)...", file=sys.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        run(["npm", "pack", "transcribe2texts", "--silent"], cwd=tmp)
        tgz = glob.glob(os.path.join(tmp, "*.tgz"))[0]
        run(["tar", "xzf", tgz, "-C", CACHE, "--strip-components=1",
             f"package/{MODEL_NAME}"])
    return path


def ensure_vosk():
    try:
        import vosk  # noqa: F401
    except ImportError:
        # vosk depends on `srt`, whose sdist fails to build on some Pythons; it
        # is a single pure-python module, so drop it in place if needed.
        try:
            import srt  # noqa: F401
        except ImportError:
            with tempfile.TemporaryDirectory() as tmp:
                run([sys.executable, "-m", "pip", "download", "--no-deps",
                     "--no-binary", ":all:", "srt", "-d", tmp])
                run(["tar", "xzf", glob.glob(os.path.join(tmp, "srt-*.tar.gz"))[0], "-C", tmp])
                import site
                dest = site.getsitepackages()[0]
                src = glob.glob(os.path.join(tmp, "srt-*", "srt.py"))[0]
                with open(src) as a, open(os.path.join(dest, "srt.py"), "w") as b:
                    b.write(a.read())
        run([sys.executable, "-m", "pip", "install", "--no-deps", "vosk", "cffi", "tqdm",
             "requests", "websockets"])


def transcribe(clip):
    need("ffmpeg")
    ensure_vosk()
    from vosk import KaldiRecognizer, Model, SetLogLevel
    SetLogLevel(-1)
    model = Model(ensure_model())
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "a.wav")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", clip, "-vn", "-ac", "1",
                        "-ar", "16000", wav], check=True)
        wf = wave.open(wav, "rb")
        rec = KaldiRecognizer(model, wf.getframerate())
        rec.SetWords(True)
        words = []
        while True:
            data = wf.readframes(4000)
            if not data:
                break
            if rec.AcceptWaveform(data):
                words += json.loads(rec.Result()).get("result", [])
        words += json.loads(rec.FinalResult()).get("result", [])
    return [{"w": w["word"], "s": round(w["start"], 3), "e": round(w["end"], 3)} for w in words]


def print_transcript(words, pause=0.35):
    line = []
    for i, w in enumerate(words):
        if i and w["s"] - words[i - 1]["e"] > pause:
            print(" ".join(line))
            print(f"   ~ pause {w['s'] - words[i - 1]['e']:.2f}s")
            line = []
        line.append(f"[{i}]{w['w']}@{w['s']:.2f}")
    if line:
        print(" ".join(line))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    ap.add_argument("--out")
    a = ap.parse_args()
    words = transcribe(a.clip)
    out = a.out or os.path.splitext(a.clip)[0] + ".words.json"
    with open(out, "w") as f:
        json.dump(words, f)
    print_transcript(words)
    print(f"\n{len(words)} words -> {out}", file=sys.stderr)
