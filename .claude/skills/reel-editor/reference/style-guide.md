# Edit style guide: local-service ad reels

Learned from two reference ads, each measured frame by frame:

| Style | Reference | Feel |
|-------|-----------|------|
| **A: "Bold Local"** | `ali-reel-01.md` (Abilene Auto Aesthetics, 43 s) | Calls out the city, speaker-led, fast service montage, loud caps captions, light leaks |
| **B: "Myth-Buster Cinematic"** | `derek-detail-01.md` (D-LUX Detail, 27 s) | Contrarian hook, mostly slow-mo B-roll with voiceover, music-only montages, mixed-type captions with a colour sweep, PiP proof shots |

When a new reference comes in, add its breakdown file. Then fold it in here: confirm a
style, add options to one, or add a style C.

## 0. Which style to use

- The user names one ("like the first one" = A, "like the Derek one" = B) → use that.
- The footage is mostly **talking head with a few B-roll clips**, or the ad sells a
  **city-wide service with a price** → **A**.
- The footage is mostly **cinematic B-roll** (slow-mo, macro, gimbal), the angle is
  **educational or contrarian** ("X is ruining your Y"), or the script is short (20–30 s) → **B**.
- If you're unsure, pick by footage and say which style you used and why. Don't mix
  caption systems inside one ad. Transitions can be borrowed across styles
  sparingly (one spin in an A ad is fine).

## 1. Shared principles (both references agree)

1. **Hook in the first 1.5 s** with the viewer's problem, said by the person on camera
   with captions running from frame 1.
2. **Silence is cut.** Voice segments are tight jump cuts. Only music-only montages
   (style B) are voice-free, and those are deliberate.
3. **B-roll is literal and on the word.** The shot starts on the keyword's first syllable.
4. **Captions reveal word by word on the spoken time.** A page never reflows, and the
   key word on every page is emphasised (colour in A, size/weight/sweep in B).
5. **The talking head comes back for the CTA.** The last 5–15 s are the person asking
   for the booking, with the brand name on screen.
6. **Music under everything,** ducked hard under the voice. No sound effects.
7. **Natural, bright grade.** No heavy LUT.

## 2. Style A: "Bold Local" (ref 01)

### Script (40–45 s)
| Beat | Example | Length |
|------|---------|--------|
| Location call-out + pain | "Abilene residents, if your vehicle is overdue for an interior and exterior detail…" | 0–3.4 s |
| "This is for you" | "…this video is for you." | ~1 s |
| Who + where | "At Abilene Auto Aesthetics we help vehicle owners throughout West Texas…" | ~3 s |
| Outcome | "…keep their cars looking clean, comfortable and looking their best." | ~3 s |
| Process (interior, then exterior) | "Inside, we steam clean and blow out all surfaces, shampoo…" | ~15 s |
| Care / differentiator | "We take our time… details you notice once the job is finished" | ~6 s |
| Offer + price | "Our full interior and exterior details are at $249, with final pricing depending on…" | ~7 s |
| CTA | "Click the link or contact Abilene Auto Aesthetics to request a quote and reserve your appointment today." | ~5 s |

The first ~26 s lean on B-roll. The last ~17 s are talking head only.

### Picture
- Shots average 1.6 s; B-roll runs 0.5–1.4 s; talking-head stretches run 1–3 s, then 2–7 s at the end.
- **Punch-ins:** the talking head alternates scale 1.0 and ~1.15 at every jump cut or
  re-entry, so the same zoom never shows twice in a row. The closing section uses ~1.05 / ~1.10.
- **Split screen** for "X and Y" pairs: a 50/50 top/bottom split with a 12 px white
  divider. Each half carries a one-word orange label at its centre (y 0.25 / 0.75).

### Transitions
| Name | Use | Look |
|------|-----|------|
| `cut` | Default; inside montages | — |
| `flash` | Beat changes, talking head ↔ B-roll sections (~6 per ad) | Brighten and warm, 1–2 frames of cream #F6DCAB, then an orange-to-pink leak fading over 0.25 s |
| `prism` | Covers talking-head jump cuts in the closing section (~3) | 0.2 s diagonal orange → violet → peach sweep at half coverage |
| `whip` | Into the first B-roll of a process beat (once) | Vertical smear and slide that sharpens in 3 frames |

### Captions (`"preset": "bold"`)
- **Font and size:** Saira ExtraBold Expanded (a Eurostile/Good Times stand-in),
  ALL CAPS, no punctuation, $ numerals. 69 px at 1080 wide; orange lines ×1.1.
- **Position:** centred at y ≈ 0.525 (chest). On B-roll, move it off the subject (0.20–0.45).
- **Pages:** 1–2 lines, 1–3 words per line (≤ 16 chars). Pages hard-swap with no exit animation.
- **Colour:**
  - Line 1 is white.
  - Line 2 is the orange gradient payoff (#FFC855 → #EE6C00) for the place, service,
    benefit, price, brand or CTA.
  - Single keywords and the brand name are fully orange.
- **Reveal:** words slide in from the right with motion blur in 0.13 s.
- **Icon:** a red map pin before the location line.

### Sound
The voice sits at about -16 LUFS. The music is 25–30 dB below it (`gain_db` ≈ -21, `duck_ratio` 5).

## 3. Style B: "Myth-Buster Cinematic" (ref 02)

### Script (25–30 s)
| Beat | Example | Length |
|------|---------|--------|
| Contrarian hook, on camera | "Automatic car washes are killing YOUR paint." | 0–2.4 s |
| Tease | "Here's why." | ~0.8 s |
| **Music montage #1**, no voice | Process B-roll: foam, wheels, mats | ~4 s (3 shots) |
| Explanation as voiceover over B-roll | "The brushes used in automatic car washes are often dirty and loaded with debris. Dragging that across your paint can create micro swirls and scratches…" | ~8 s |
| Punchline | "…that make your paint look like s**t." | ~1.5 s |
| **Music montage #2**, no voice | Beauty shots of the finished car: interior, rear, wheel | ~5 s (3 shots) |
| CTA on camera | "Don't let a machine ruin your paint. Book a proper hand wash with D-LUX Detail today with the link down below." | ~5 s |
| Fade to black + hold | — | ~0.9 s |

The talking head is only on screen for the hook and the CTA (about 30% of runtime).
Everything in between is B-roll.

### Picture
- Shots average 2 s; B-roll runs 1–2.3 s, longer and calmer than style A.
  Shoot or conform slow-mo (`"speed": 0.5–0.8` on 60 fps clips). Use gimbal glides,
  macro close-ups and glossy beauty angles.
- **No punch-ins** (`"zooms": [1.0]`). The talking head is a wide full-body shot,
  ideally walking toward the camera. The CTA is cut across 2–3 positions or locations with hard cuts.
- **PiP proof shot:** when the voice names a defect you can show in macro ("micro swirls",
  "scratches"), float the macro clip in a box over the B-roll (`"layout": "pip"`,
  `rect` ≈ [0.17, 0.30, 0.66, 0.27]). It pops in on a cut, fades out over 0.12 s, and
  the next PiP can follow immediately.
- **Fade in** from black (0.1 s) and **fade out** to black (0.3 s) with a 0.6 s black `tail`.

### Transitions
- Hard cuts are the default; music-montage cuts land on the beat.
- `spin`, once, into the beauty montage: a rotational zoom-blur of about 0.2 s.
- No flashes or light leaks.

### Captions (`"preset": "mixed"`)
- **Font:** a humanist sans family (Open Sans standing in for Segoe UI), white only,
  soft shadow. Mixed case; ONE word per phrase may go ALL CAPS for stress
  ("killing YOUR", "down BELOW", "MACHINE", "PROPER").
- **Size hierarchy** (`scale` × 104 px base):

  | Role | Font | Scale |
  |------|------|-------|
  | Connector / filler ("are", "The brushes", "Book a", "with", "today") | `light-italic` | 0.75–0.9 |
  | Plain phrase ("killing YOUR", "across", "look like") | `regular` | 1.0 |
  | Keyword ("Automatic", "PROPER", "car washes", "D-LUX Detail") | `bold` | 1.1–1.4 |
  | Punch phrase ("loaded with debris", "micro swirls", "YOUR PAINT") | `extrabold-italic` | 1.05–1.2 |
  | One hero word per ad ("paint") | `extrabold-italic`, `enter: pop` | 2.3–2.5 |
  | Tease ("Here's why") | `semibold-italic` | 1.25 |

- **Layout:** stack 2–4 short lines with a tight line gap (0.86), sometimes offset
  left or right (`align`/`dx`) for a hand-placed look. Put them in free space: chest
  height on the talking head, upper third on B-roll, or over the PiP.
- **Sweep:** set `"sweep": true` on 1 keyword every few seconds ("Automatic", "dirty",
  "micro swirls", "YOUR PAINT"). A teal → violet band runs across the word and settles on its last letters.
- **Motion and timing:**
  - Words slide in from the left with blur in 0.15 s, and pages fade out over 0.15 s.
  - In the CTA, a new keyword can replace the previous one in the same spot (a new
    page with the same `y`).
- **No captions** during the music-only montages.
- **Tone:** casual, and profanity is allowed only if censored ("S\*\*T"). Ask before using any.

### Sound
- The voice sits at about -16 LUFS and the ad lands around -19 LUFS overall.
- Music is higher than in A: `gain_db` ≈ -12 with `duck_ratio` 8. It swells to full
  level in the voice-less montages (the side-chain handles this automatically) and fades with the picture.
- Montage cuts sit on the music's beats.

## 4. Checklist before delivering (both styles)

1. The hook states the problem by 1.5 s (A: city in the first two words; B: a contrarian claim).
2. B-roll appears by 2.5 s (A) or 3.5 s (B).
3. There's no unintended silence, and in A no two consecutive talking-head cuts share a zoom.
4. Every named service or defect has literal B-roll or a PiP on its word.
5. Transitions follow the style's table, and none come from the other style unless deliberate.
6. Captions are proof-read word by word (brand, city, price), the emphasis is applied,
   and there are no captions in music-only montages.
7. The CTA is on camera with the brand name captioned, and the video ends on the last CTA
   word (A) or fades to black with a tail (B).
