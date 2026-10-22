"""Job-specific: builds edit.json + captions.json for the Becris re-edit (style A)."""
import json
OFF = 0.45                      # trim the dead air before "Attention"
W = json.load(open('work/orig/words.json'))
s = lambda i, d=0.0: round(W[i]['s'] + d - OFF, 3)
o = lambda t: round(t - OFF, 3)
SRC = "raw/becris_clean.mp4"

def ins(a, b, t_in, speed=1.0, zoom=1.0, focus=(0.5, 0.45), ti="cut", to="cut"):
    return {"start": o(a), "end": o(b), "src": SRC, "in": t_in, "speed": speed, "zoom": zoom,
            "focus": list(focus), "trans_in": ti, "trans_out": to}

inserts = [
    ins(0.45, 2.75, 18.80),                                  # neighbourhood + truck foam: "Attention Alexandria"
    ins(2.75, 3.75, 2.90),                                   # dirty rear seats: "rough"
    ins(3.75, 4.90, 5.05, zoom=1.08),                        # dirty console: "messy"
    ins(4.90, 6.30, 12.70, ti="flash"),                      # clean premium interior: "Becris Detailing"
    ins(6.30, 7.05, 21.45, zoom=1.1),                        # rinse: "we come straight to you"
    ins(7.05, 8.40, 7.25, speed=0.97),                       # mobile rig: "fully mobile"
    ins(8.40, 10.05, 9.12, ti="flash"),                      # clean seat: "$50 off"
    ins(10.05, 11.55, 10.85),                                # clean bench: "full detail"
    {"start": o(11.55), "end": o(12.85), "layout": "split", "trans_in": "flash", "trans_out": "flash",
     "top": {"src": SRC, "in": 13.40, "focus": [0.5, 0.4]},
     "bottom": {"src": SRC, "in": 26.50, "focus": [0.5, 0.35]}},
    ins(12.85, 13.60, 3.70, zoom=1.1),                       # stained seats
    ins(13.60, 15.15, 13.90, speed=0.6),                     # extracted + deep cleaned (slow-mo)
    ins(15.15, 16.25, 15.62, ti="whip"),                     # engine bay
    ins(16.25, 16.85, 17.00),                                # headlight A
    ins(16.85, 17.35, 17.85, zoom=1.1),                      # headlight B
    ins(17.35, 18.60, 25.30, speed=0.85, ti="flash"),        # exterior washed
    ins(18.60, 20.05, 26.45),                                # foamed Jeep: "deep glossy shine"
    ins(20.05, 21.55, 20.00, zoom=1.2, focus=(0.65, 0.5)),   # truck, punched in: "top to bottom"
    ins(21.55, 23.95, 12.65, speed=0.55, zoom=1.1, ti="prism"),  # slow push on clean interior: urgency
    ins(23.95, 25.60, 23.35),                                # wheel brushing: "click get quote below"
    ins(25.60, 26.95, 9.20, zoom=1.15),                      # clean seat: "secure $50 off"
    ins(26.95, 28.90, 10.85, speed=0.8, zoom=1.15),          # clean bench: "we'll contact you"
    ins(28.90, 31.90, 26.40, speed=0.5, zoom=1.05, ti="flash"),  # end card background
    {"start": o(29.05), "end": o(31.90), "layout": "pip", "shape": "circle", "src": "raw/logo.mp4",
     "in": 0.0, "rect": [0.25, 0.17, 0.5, 0.28125], "fade_in": 0.2},
]

def page(lines, y=None, icon=None, start=None):
    p = {"lines": [{"color": c, "words": [{"t": t, "s": tt} for t, tt in ws], **extra}
                   for c, ws, extra in lines]}
    if y is not None: p["y"] = y
    if icon: p["icon"] = icon
    p["start"] = start if start is not None else min(w["s"] for l in p["lines"] for w in l["words"])
    return p

Wt, Or = "white", "orange"
pages = [
    page([(Wt, [("ATTENTION", s(0))], {}), (Or, [("ALEXANDRIA", s(1))], {})], icon="pin"),
    page([(Wt, [("AND", s(2)), ("SURROUNDING", s(3))], {}), (Or, [("AREAS", s(4))], {})]),
    page([(Wt, [("IS", s(5)), ("YOUR", s(6)), ("CAR", s(7)), ("STILL", s(8))], {}),
          (Or, [("LOOKING", s(9)), ("ROUGH", s(11))], {})]),
    page([(Or, [("AND", s(12)), ("MESSY", s(13))], {"size": 92})]),
    page([(Wt, [("WELL", s(14)), ("HERE", s(15)), ("AT", s(16))], {}),
          (Or, [("BECRIS", s(17)), ("DETAILING", s(18))], {})]),
    page([(Wt, [("WE", s(19)), ("COME", s(20)), ("STRAIGHT", s(21))], {}),
          (Or, [("TO", s(21, 0.27)), ("YOU", s(22))], {})]),
    page([(Wt, [("WERE", s(23)), ("FULLY", s(24))], {}), (Or, [("MOBILE", s(25))], {})]),
    page([(Wt, [("AND", s(26)), ("RIGHT", s(27)), ("NOW", s(28))], {}),
          (Wt, [("WERE", s(29)), ("OFFERING", s(30))], {})]),
    page([(Or, [("$50", s(31)), ("OFF", s(33))], {"size": 130})]),
    page([(Wt, [("OF", s(34)), ("A", s(34, 0.12))], {}), (Or, [("FULL", s(35)), ("DETAIL", s(36))], {})]),
    page([(Or, [("INTERIOR", s(37))], {})], y=0.25),
    page([(Or, [("EXTERIOR", s(39))], {})], y=0.75, start=s(37)),
    page([(Wt, [("STAINED", s(41)), ("SEATS", s(42))], {}), (Or, [("EXTRACTED", s(43))], {})]),
    page([(Wt, [("AND", s(44)), ("DEEP", s(45))], {}), (Or, [("CLEANED", s(46))], {})]),
    page([(Wt, [("ENGINE", s(47)), ("BAY", s(48))], {}), (Or, [("DEGREASED", s(49, 0.09))], {})]),
    page([(Wt, [("HEADLIGHTS", s(51))], {}), (Or, [("RESTORED", s(53))], {})]),
    page([(Wt, [("AND", s(54)), ("THE", s(55)), ("EXTERIOR", s(56))], {}), (Or, [("WASHED", s(58))], {})]),
    page([(Wt, [("AND", s(59)), ("FINISHED", s(60)), ("TO", s(61)), ("A", s(62))], {}),
          (Or, [("DEEP", s(63)), ("GLOSSY", s(64)), ("SHINE", s(65))], {})]),
    page([(Or, [("TOP", s(67)), ("TO", s(68)), ("BOTTOM", s(69))], {"size": 92})]),
    page([(Wt, [("THIS", s(70)), ("IS", s(71)), ("A", s(72))], {}),
          (Or, [("LIMITED", s(73)), ("TIME", s(74)), ("OFFER", s(75))], {})]),
    page([(Wt, [("FOR", s(76)), ("THE", s(77)), ("FIRST", s(78))], {}),
          (Or, [("10", s(79)), ("PEOPLE", s(80))], {})]),
    page([(Wt, [("THAT", s(81)), ("BOOK", s(82))], {"size": 84})]),
    page([(Wt, [("SO", s(83)), ("CLICK", s(84))], {}),
          (Or, [("GET", s(85)), ("QUOTE", s(86)), ("BELOW", s(87))], {})]),
    page([(Wt, [("TO", s(88)), ("SECURE", s(89))], {}), (Or, [("$50", s(91)), ("OFF", s(93))], {"size": 110})]),
    page([(Wt, [("AND", s(94)), ("WELL", s(95)), ("CONTACT", s(96)), ("YOU", s(97))], {}),
          (Or, [("FOR", s(98)), ("THE", s(99)), ("BEST", s(100)), ("DATE", s(101))], {})]),
    page([(Wt, [("OR", o(29.3)), ("CALL", o(29.45)), ("US", o(29.6)), ("AT", o(29.72))], {}),
          (Or, [("(412)", o(29.95)), ("654-1307", o(30.2))], {"size": 84})], y=0.6),
]
total = o(31.9)
for i, p in enumerate(pages):
    if "end" not in p:
        nxt = next((q["start"] for q in pages[i + 1:] if q["start"] > p["start"]), total)
        p["end"] = round(nxt, 3)
pages[10]["end"] = pages[11]["end"] = o(12.85)          # split labels end with the split
pages[24]["end"] = o(28.9)                               # last VO page ends at the end-card flash

edit = {"canvas": {"w": 1080, "h": 1920, "fps": 30},
        "grade": {"contrast": 1.03, "saturation": 1.06},
        "aroll": [{"src": SRC, "in": OFF, "out": 31.9, "zoom": 1.0}],
        "inserts": inserts, "captions": "captions.json", "voice_lufs": -15,
        "fade_out": 0.25, "output": "out/becris_reedit_A.mp4"}
json.dump(edit, open('edit.json', 'w'), indent=1)
json.dump({"style": {"preset": "bold", "y": 0.5}, "pages": pages}, open('captions.json', 'w'), indent=1)
print(len(inserts), "inserts,", len(pages), "pages, total", total)
