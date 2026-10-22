# Edit style guide: local-service talking-head ad

Learned from `ali-reel-01.md` (Abilene Auto Aesthetics, 43 s, 9:16). Every number
below was measured from that video frame by frame. When a new reference ad comes
in, add its breakdown next to this file and update the rules here wherever it
confirms, extends or contradicts them.

## 1. Script skeleton (what the edit is built around)

| # | Beat | Reference line | Length |
|---|------|----------------|--------|
| 1 | **Location call-out + pain hook** | "Abilene residents, if your vehicle is overdue for an interior and exterior detail…" | 0–3.4 s |
| 2 | **"This is for you"** | "…this video is for you." | 3.4–4.4 s |
| 3 | **Who we are + where** | "At Abilene Auto Aesthetics we help vehicle owners throughout West Texas…" | 4.4–7.4 s |
| 4 | **Outcome** | "…keep their cars looking clean, comfortable and looking their best." | 7.4–10.3 s |
| 5 | **Process, part 1 (interior)** | "Inside, we steam clean and blow out all surfaces, shampoo your carpets and upholstery, then we finish with interior protectants designed to protect your vehicle from harmful UV rays." | 10.3–19.4 s |
| 6 | **Process, part 2 (exterior)** | "On the exterior we start off by cleaning the wheels and tires thoroughly, handwashing the vehicle, removing years of built-up dirt and grime." | 19.4–25.7 s |
| 7 | **Care / differentiator** | "We take our time on the vehicle and focus on the details you notice once the job is finished, so your car doesn't just look clean from the street." | 25.7–31.5 s |
| 8 | **Offer + price anchor** | "Our full interior and exterior details are at $249, with final pricing depending on the size and condition of the vehicle." | 31.5–38.5 s |
| 9 | **CTA** | "Click the link or contact Abilene Auto Aesthetics to request a quote and reserve your appointment today." | 38.5–43.2 s |

The first ~26 s (beats 1–6) are **B-roll heavy**. The last ~17 s (beats 7–9: trust,
price, CTA) are **talking head only**, because that's where the viewer needs to see
the person.

## 2. Picture

- **Format:** 9:16, speaker centred, framed from mid-thigh up. The car or product sits
  behind them and the business setting fills the background.
- **Pacing:** 26 cuts/transitions in 43 s, so an average shot of 1.6 s. B-roll shots run
  0.5–1.4 s. Talking-head stretches run 1–3 s in the B-roll half and 2–7 s in the closing half.
- **Silence:** the voice never pauses. Every gap between words is cut out (jump cuts).
- **Punch-in zooms:** the talking head alternates between a wide frame (scale 1.0) and
  a tighter one (about 1.15×, centred slightly above the chest). The zoom changes at
  every jump cut or re-entry from B-roll, so the same zoom never shows twice in a row.
  The closing section uses about 1.05× and about 1.10×.
- **B-roll is literal:** each B-roll shot shows exactly the noun or verb being said, at
  the moment it's said: "steam clean" shows steam, "wheels and tires" shows a wheel
  being scrubbed, "harmful UV rays" shows the car in the sun.
- **B-roll starts on the keyword's first syllable** (± 2 frames) and lasts until the
  next phrase starts.
- **Split screen** (2.13–3.39 s): when the line names two things ("interior and
  exterior"), the frame is split top and bottom 50/50 with a white divider about 12 px
  wide at 1080. Each half is labelled with one orange word at its own centre: INTERIOR
  at y≈0.25, EXTERIOR at y≈0.75, with the second label appearing when that word is said.
- **Grade:** bright, clean and natural, with a mild contrast and saturation lift. No
  heavy LUT.

## 3. Transitions

There are only four kinds. Hard cuts are the default.

| Name | Where it's used | Measured look (23 fps ref) |
|------|-----------------|----------------------------|
| `cut` | Inside B-roll montages, and talking head to B-roll mid-beat | — |
| `flash` (cream light-leak) | **Beat changes**, talking head ↔ B-roll section boundaries (2.13, 3.39, 10.26, 14.48, 19.35, 25.65 s) | 2 frames brighten and warm up, then 1–2 frames of solid cream **#F6DCAB**, then the new shot arrives with an orange-to-pink leak that fades over about 0.25 s |
| `prism` (rainbow leak) | **Covers talking-head jump cuts** in the long closing section (29.48, 31.52, 38.52 s, roughly every 2–7 s) | About 0.2 s: a diagonal orange → violet → peach sweep covering about half the frame, with the image still visible underneath |
| `whip` | The first B-roll of a new process beat (12.17 s, "all surfaces") | Vertical motion blur and a downward slide: the old shot smears for 1 frame, the new one arrives heavily blurred and sharpens within 3 frames |

Use about 6 flashes, 1 whip and 3 prisms in a 40–45 s ad. Don't use a flash on every cut.

## 4. Captions (the biggest part of the look)

- **Font:** an extended, squared, heavy sans in the Eurostile Extended / Good Times
  family. We use **Saira ExtraBold Expanded** (OFL, bundled). ALL CAPS, no
  punctuation (DOESNT, not DOESN'T). Numbers are written as numerals with `$` ($249).
- **Size:** a 17-character line fills about 73% of the frame width (font size 69 px at 1080 wide).
  Orange lines are about 10% bigger than white ones.
- **Position:** horizontally centred at **y ≈ 0.525** (the speaker's chest, below the
  face). On B-roll, move it to wherever it avoids the subject (0.20–0.45 is common).
- **Pages:** 1–2 lines, 1–3 words per line (≤ ~16 chars). A page hard-swaps to the
  next with no exit animation.
- **Colour logic:**
  - Line 1 is white **#FAFAFA**.
  - Line 2 is the orange payoff: a vertical gradient from **#FFC855** at the top to
    **#EE6C00** at the bottom, with a dark-brown soft shadow.
  - It shows the place ("WEST TEXAS"), the service ("INTERIOR AND EXTERIOR"), the
    benefit ("LOOK CLEAN", "DETAILS YOU NOTICE"), the price ("$249"), the brand
    ("ABILENE AUTO AESTHETICS", orange on both lines) or the CTA ("YOUR APPOINTMENT").
  - Single-keyword pages are fully orange ("INSIDE", "ALL SURFACES", "HANDWASHING",
    "HARMFUL UV RAYS").
  - Plain connective phrases are white only ("THEN WE FINISH", "CLICK THE", "OR").
- **Reveal:** each word appears **on its own spoken start time**. The page layout is
  final from the start, so words never shift. A word enters over about 0.13 s: a slide
  of about 4% of the width from the right, horizontal motion blur, and a fade from 0 to 1.
- **Icon:** a red map-pin to the left of the location line ("📍 THROUGHOUT WEST TEXAS").

## 5. Sound

- The voice is the whole show, kept clean and dense. The finished mix sits at about
  -18 LUFS integrated. We normalise the voice to -16 LUFS for reels.
- A **quiet music bed** sits under the voice the whole time, about 25–30 dB below
  it, with nothing loud enough to compete. The ad never drops to silence.
- **No sound effects** on the flashes or whip; the reference uses none.

## 6. Checklist before delivering

1. Hook names the **city/area** in the first two words, and the pain point by 2 s.
2. B-roll (or split screen) is on screen within the first 2.5 s.
3. No silence anywhere, and no two consecutive talking-head cuts at the same zoom.
4. Every service named in the process beats has a literal B-roll shot.
5. Flash on beat changes, prism on closing-section jump cuts, one whip.
6. Captions are proof-read word for word (brand name, city, price), and the payoff words are orange.
7. The last 15 s are talking head only: trust, price, CTA.
8. The video ends right on the last CTA word.
