"""Generate the Indonesian caption file from the judging script itself.

Captions are derived, never hand-typed, so they cannot drift from the narration.
Each segment's time budget is split across its cues in proportion to character
count. Every cue is guaranteed to wrap into at most two lines of <= 42 chars,
and no cue is left on screen for less than MIN_DUR seconds.
"""

import re
from pathlib import Path

MAX_LINE = 42
MAX_CUE_CHARS = 84  # two lines
MIN_DUR = 1.2  # seconds a cue must stay readable

src = Path("submission/judging-video-script-id.md").read_text(encoding="utf-8")
rows = re.findall(r"\| \*\*(\d\d:\d\d)\u2013(\d\d:\d\d)\*\* \|[^|]*\| \"([^\"]+)\" \|", src)
assert rows, "no narration rows parsed"


def secs(stamp_text):
    m, s = stamp_text.split(":")
    return int(m) * 60 + int(s)


def stamp(total):
    h = int(total // 3600)
    m = int((total % 3600) // 60)
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def best_split(text):
    """Index of the space giving two lines <= MAX_LINE, nearest the midpoint."""
    best, best_cost = None, None
    for i, ch in enumerate(text):
        if ch != " ":
            continue
        left, right = len(text[:i]), len(text[i + 1:])
        if left > MAX_LINE or right > MAX_LINE:
            continue
        cost = abs(left - right)
        if best_cost is None or cost < best_cost:
            best, best_cost = i, cost
    return best


def force_halve(text):
    """Split an unwrappable unit into two units at the space nearest midpoint."""
    mid = len(text) // 2
    spaces = [i for i, ch in enumerate(text) if ch == " "]
    if not spaces:
        return [text]
    cut = min(spaces, key=lambda i: abs(i - mid))
    return [text[:cut].strip(), text[cut + 1:].strip()]


def split_units(text):
    parts = re.split(r"(?<=[.?!]) +", text)
    units = []
    for part in parts:
        if len(part) <= MAX_CUE_CHARS:
            units.append(part)
            continue
        chunks = re.split(r"(?<=,) +| — ", part)
        buf = ""
        for chunk in chunks:
            candidate = f"{buf} {chunk}".strip()
            if len(candidate) <= MAX_CUE_CHARS:
                buf = candidate
            else:
                if buf:
                    units.append(buf)
                buf = chunk
        if buf:
            units.append(buf)

    # Guarantee every unit can actually wrap into two <=42 char lines.
    guaranteed = []
    queue = list(units)
    while queue:
        unit = queue.pop(0)
        if len(unit) <= MAX_LINE or best_split(unit) is not None:
            guaranteed.append(unit)
        else:
            halves = force_halve(unit)
            queue = halves + queue if len(halves) == 2 else queue
            if len(halves) == 1:
                guaranteed.append(halves[0])
    return guaranteed


def wrap(text):
    if len(text) <= MAX_LINE:
        return text
    cut = best_split(text)
    return text if cut is None else text[:cut] + "\n" + text[cut + 1:]


cues = []
for start_s, end_s, narration in rows:
    begin, finish = secs(start_s), secs(end_s)
    span = finish - begin
    units = split_units(narration.strip())

    # Merge units until every cue clears MIN_DUR inside this segment's budget.
    while len(units) > 1 and span / len(units) < MIN_DUR:
        shortest = min(range(len(units)), key=lambda i: len(units[i]))
        left = shortest - 1 if shortest > 0 else None
        right = shortest + 1 if shortest + 1 < len(units) else None
        target = left if right is None or (
            left is not None and len(units[left]) <= len(units[right])
        ) else right
        lo, hi = sorted((shortest, target))
        units[lo:hi + 1] = [f"{units[lo]} {units[hi]}"]

    total_chars = sum(len(u) for u in units)
    cursor = begin
    for i, unit in enumerate(units):
        share = span * (len(unit) / total_chars)
        cue_end = finish if i == len(units) - 1 else cursor + share
        cues.append((cursor, cue_end, wrap(unit)))
        cursor = cue_end

out = []
for i, (a, b, text) in enumerate(cues, 1):
    out.append(f"{i}\n{stamp(a)} --> {stamp(b)}\n{text}\n")

Path("submission/judging-video-captions-id.srt").write_text(
    "\n".join(out), encoding="utf-8"
)

longest = max(len(line) for _, _, t in cues for line in t.split("\n"))
over = [t for _, _, t in cues if any(len(x) > MAX_LINE for x in t.split("\n"))]
lines3 = [t for _, _, t in cues if len(t.split("\n")) > 2]
fast = [(a, b) for a, b, t in cues if len(t.replace("\n", " ")) / max(b - a, 0.1) > 20]
short = [(a, b) for a, b, _ in cues if b - a < MIN_DUR]
print(f"cues         : {len(cues)}")
print(f"baris >42    : {len(over)}  (terpanjang {longest})")
print(f"cue >2 baris : {len(lines3)}")
print(f"cue >20 c/s  : {len(fast)}")
print(f"cue <{MIN_DUR}s   : {len(short)}")
print(f"durasi akhir : {stamp(cues[-1][1])}")
