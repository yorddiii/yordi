---
name: reel-editor
description: Edit raw phone clips (talking-head takes + B-roll) into a finished 9:16 local-service ad reel in the learned house style - jump-cut talking head with punch-in zooms, literal B-roll on every service word, split screen, cream flash / prism light-leak / whip transitions, word-by-word white+orange extended-font captions, ducked music bed. Use whenever the user sends raw clips to edit "like the reference", asks for an ad/reel/TikTok edit, or sends a new example ad to learn from.
---

# Reel editor

You are the editor. The scripts do the mechanical work (transcribe, cut, render). You
make every creative decision: which takes, which B-roll on which word, which
transitions, and the caption wording and colours. Those decisions follow
`reference/style-guide.md`. **Read it first, every time.** Per-reference shot lists
live next to it (`reference/ali-reel-01.md`, ...).

Requirements: `ffmpeg`, `python3` with `numpy` + `Pillow`. `transcribe.py`
installs `vosk` and fetches its model on first use, via npm when the usual model
hosts are blocked.

`S=.claude/skills/reel-editor/scripts`. Keep the user's footage and the work files in a
project folder such as `reels/<job>/` with `raw/`, `work/` and `out/`. Large videos
stay out of git.

## Workflow for a new job

1. **Gather.** Get the raw clips into `reels/<job>/raw/`. Ask only for what you can't
   infer: business name, city or service area, the services shown, price or offer, the
   CTA, and a music track if they have one. If you get no music, render without music
   and say so.
2. **Ingest.** Run `python3 $S/ingest.py reels/<job>/raw --work reels/<job>/work`.
   Open **every** `work/sheets/*.png` and write down what each clip shows: talking head
   or B-roll, which service, usable time ranges, shaky or blurry parts. Then read
   `work/ingest.md`, which has the indexed transcript of each take.
3. **Proof-read the transcript.** The offline model mishears brand names, cities and
   prices ("appling auto" → "Abilene Auto", "two forty nine" → "$249"). Fix
   `work/words/<clip>.json` entries in place. Keep the times and change only `"w"`.
4. **Choose takes.** Write `plan.json` (format in `plan.py`'s docstring). Build the
   script in the style-guide beat order (hook with location → for you → who and where
   → outcome → process → care → price → CTA). For each beat take the best clean take
   and drop flubs, restarts and filler (`drop` takes word indices). Then run
   `python3 $S/plan.py reels/<job>/plan.json --captions`. It cuts every pause longer
   than 0.22 s, alternates zoom 1.0 / 1.15 at each jump cut, writes `edit.json` and
   `captions.json`, and prints every word with its **output** time.
5. **Lay B-roll and transitions** in `edit.json` → `inserts` (schema in `render.py`):
   - Every service or benefit noun gets a literal B-roll shot that starts on that
     word's output time and ends where the next phrase starts. B-roll runs 0.5–1.4 s per shot.
   - Use a split screen for "X and Y" pairs (interior/exterior, before/after).
   - `flash` goes on beat changes, both into and out of B-roll sections, about 6 per ad.
     `whip` goes into the first B-roll of a process beat, once. In the B-roll-free
     closing section, set `"join": "prism"` on about every second or third A-roll cut.
   - The last ~15 s (care → price → CTA) stay talking head only.
   - Fit tight zooms by setting `zoom`/`focus` per cut so the head stays in the top
     third. Never put the same zoom on two consecutive cuts.
6. **Captions** (`captions.json`): fix the auto pages so they follow the style guide.
   Use 1–2 lines with 1–3 words each. Line 1 is white and line 2 is the orange payoff.
   Single keywords and the brand name are fully orange. Write `$249`, not "two forty
   nine", and drop the apostrophes. Add `"icon": "pin"` on the location page. On B-roll,
   move `y` off the subject. For a split screen use two overlapping pages at
   `y` 0.25 and 0.75. Each word's `s` is its output time: when you merge or retype
   words, keep the `s` of the spoken word.
7. **Preview.** Run `python3 $S/render.py reels/<job>/edit.json --preview` (540×960,
   fast). You can render a section with `--from/--to`. Review it with
   `python3 $S/analyze.py out/final_preview.mp4 --out work/review`: open the sheets,
   and look at frame strips (`--strip START DUR`) around each transition. Check it
   against the style-guide checklist (§6) and fix whatever is off.
8. **Final.** Run `python3 $S/render.py reels/<job>/edit.json`, which writes 1080×1920 at
   30 fps (H.264 CRF 17, AAC 192k) to `out/final.mp4`. Send it to the user with
   SendUserFile, along with a short list of the editorial choices you made.

## Learning from a new example ad

1. Run `python3 $S/analyze.py EXAMPLE --out reels/_refs/<name> --transcribe`. Read
   `report.md` and every sheet, then run `--strip` on each transition and on caption
   close-ups to see the motion frame by frame.
2. Write `reference/<name>.md` in the same format as `ali-reel-01.md`: specs, shot list
   with zoom/transition/caption pages, measured transition frames, corrected transcript.
3. Update `reference/style-guide.md`. Confirm the rules this example matches, add new
   techniques as named options (and say when to use them), and note contradictions as
   variants rather than overwriting. When a new technique needs code (new transition,
   caption animation, layout), add it to `render.py` next to the existing ones and
   document it in the schema docstring.

## Renderer notes

- The A-roll is concatenated and the **voice comes only from A-roll**. Inserts cover the
  picture while the voice keeps playing, so B-roll is a pure overlay.
- Times in `inserts` and `captions.json` are output seconds, snapped to frames.
- Transitions are frame-level effects around a boundary, so they never shift the timing.
- Audio: 12–15 ms fades at every cut, then highpass, a light compressor and loudnorm to
  `voice_lufs` (-16). Music gets looped, set to `gain_db` (-21), side-chain ducked
  under the voice, and faded out over the last second.
