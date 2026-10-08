# Self-checks for a transcribed measurement sheet

Referenced from steps 2–3 and 6 of `SKILL.md`. Every number and snippet below was run against a real
13-tube Pitot/venturi sheet (8 flow conditions + one Q = 0 zero reference) and produced the recorded result.

## 1. Unit factor: decide from a physical magnitude

The compute script assumed `流量计流量` in m³/h; the sheet's own header said L/min.

| quantity | L/min → m³/h | effect on v | effect on v²/2g |
|---|---|---|---|
| factor | ÷ 16.667 | × 16.667 | × 277.8 |

Deciding test: take the largest measured head difference of a known-geometry pair and compare it with the
prediction from the recorded flow. Measured: Δh = 447 mm at the throat (d8 inlet → d4 throat), i.e.
(v₂²−v₁²)/2g = 15·v₁²/2g. With the value read as m³/h the prediction was ~100 000 mm; read as L/min it was
359 mm against 447 measured (within the usual 公称/实际 diameter difference). The unit was L/min.

Also confirm the scale against the instrument's own range when the 讲义 states it (a meter rated
4–500 L/h cannot be reading 1020 L/min), and prefer the reading whose predicted magnitude is in the
same decade as the measurement.

## 2. Pair scan: Δh ∝ Q², by relative scatter

```python
import itertools, math
# flow steps already in m³/h; h[tube][cond] = reading in mm
rows = []
for a, b in itertools.permutations(range(1, 14), 2):
    d = [h[a][k] - h[b][k] for k in range(len(flow))]
    if min(d) <= 0:
        continue                                    # wrong side: total must exceed static
    r = [d[k] / flow[k] ** 2 for k in range(len(flow))]
    m = sum(r) / len(r)
    sd = (sum((x - m) ** 2 for x in r) / len(r)) ** 0.5 / m
    rows.append((sd, a, b, m, min(d), max(d)))
rows.sort()
for sd, a, b, m, mn, mx in rows[:8]:
    print(f"{a}->{b}: Δh/Q²={m:.2f}  scatter={sd*100:.2f}%  Δh {mn:.1f}~{mx:.1f} mm")
```

Measured output: the four true Pitot pairs came back at 0.3–2 % scatter, while pairs that only share a
Q²-dependence through one strongly varying tube (the throat, or a nearly constant tube vs a falling one)
sat at 3–7 %. **The scan alone does not decide the pairing** — the within-pair inequality and the user's
axis-tap answer do; use the scan to reject impossible pairs and to catch a misread row.

## 3. Plausibility window: c = √(Δh / (v̄²/2g))

The total-pressure tube sits on the pipe axis (讲义: 总水头测压管置于轴线), so Δh is the *axis* velocity
head, not the mean one:

```python
def hv(Q_m3h, d_mm):                 # velocity head of the MEAN velocity, mm
    A = math.pi * d_mm ** 2 / 4 * 1e-6
    v = (Q_m3h / 3600) / A
    return v * v / (2 * 9.801) * 1000

c = math.sqrt(dh / hv(Q, d))         # per condition
```

Measured: the d10 pair → c = 0.91–1.15; the d8 pairs → c ≈ 1.15–1.5 (cross-section pairs included in the
scan reach 1.6). Inside every promising pair the largest c sits at the lowest flow (Re ≈ 2.7×10³,
transitional) and declines as Re rises — printed lists step 1.39 → 1.28, 1.31 → 1.16, 1.53 → 1.34. So:
- **accept** c ≈ 1.05–1.4 for turbulent, and a smooth decline toward that band as Q rises;
- **reject** a constant c ≈ 2+ (that is the laminar 2.0 profile, not this apparatus) or a c that jumps
  between conditions with no Re trend — both mean a wrong diameter or a misread row.

## 4. Trend check inside a tube

Print each tube across the flow steps and look for a dip-and-return. Measured suspects: one tube ran
452.3 / 464.2 / 465.0 / **462.9** / 467.0 …, and two neighbouring side taps **dropped 12 mm and returned**
at one step. Both were flagged for the user to re-read; neither was silently smoothed.

## 5. Where the pairing actually comes from

Order of authority, cheapest first:

1. **The user, for which tubes are the axis (总压) taps.** Measured: asked once, the answer came back at
   once — 「6、9、11、13是总压管」, i.e. 11 and 13 are axis tubes whose same-section static partners are
   10 and 12. In this apparatus the axis tube is *not* always the higher-numbered tap.
2. The 讲义 sentence/figure: which test ports form Pitot groups (「4、5、6 号和 7、8、9 号…」), where the
   diameter changes (「9 号之后至 12 号之前…管径为 10 mm」), and which stations share an elevation.
3. The data, via sections 2–3: Δh ∝ Q² fixes the pairs and c = √(Δh/(v̄²/2g)) ≈ 1.05–1.4 fixes the
   diameter; inside a pair the larger reading is the axis reading (measured: 6>5、9>8、11>10、13>12).

**Do not promote a template column to item 1.** The 表 2「毕托管位置」 column printed 6、9、10、12 — a
position label, not the axis-tube list. Trusting it made the sheet look impossible (row 10 below row 11,
row 12 below row 13), the working copy was "corrected" by swapping those two label pairs, and the reply
reported 11/13 as static taps. Both were wrong: the as-read labels were correct and the swap was reverted
before delivery. A label swap changes no Δh, so the derived tables were identical either way — the error is
invisible in the numbers and surfaces only in the claimed apparatus pairing, which is exactly why the
pairing must come from the user rather than be inferred.

A reading that contradicts a pairing you assumed is therefore not evidence of a misread row. Localise real
misreads with sections 3–4 (c outside its window, or a dip-and-return inside one tube) and ask the user the
one question for the rest.

## 6. Independent cross-check before delivering

Pick a derived quantity that no fit touched. Measured: two mid-pipe sections 300 mm apart gave
E₁ − E₂ = 32.3 mm at v̄ = 0.685 m/s, d = 8 mm →

```
λ = h_w · d / (L · v̄²/2g) = 32.3 × 8 / (300 × 24.0) = 0.036
Blasius: 0.3164 / Re^0.25, Re = 5461  →  0.0368
```

Agreement to ~2 % validates flow reading, unit conversion, diameters and the head arithmetic in one shot.
Report the pair, the formula, and any geometry you assumed (here L ≈ 300 mm from the figure) so the
cross-check stays auditable.

## 7. Distance-series linearity: 1/Z² and the zero-point offset

A power-versus-distance run (tungsten lamp, probe stepped 20 → 75 cm) is meant to show P ∝ 1/Z². Measured
on a 12-point record:

| test | result |
|---|---|
| P·Z² (constant if 1/Z² holds) | 49 480 → 20 756, monotone, ×2.4 |
| linear P vs 1/Z² | R² = 0.964 (0.920 forced through the origin); residuals +12.2 at Z=20 → +5.4 at Z=75 |
| P = K/(Z+z₀)² | z₀ = −8.83 cm, K ≈ 15 396, R² = 0.999 80; P·(Z+z₀)² spread only 7.5 % |
| local exponent ln(Pᵢ/Pᵢ₊₁)/ln(Zᵢ₊₁/Zᵢ) | 3.41 → 2.28, falling toward 2 |

Read it as: readings smooth and monotone, no outliers, and one constant distance offset reproduces them to
0.02 %. So the probe is linear and the record is good — the operator measured Z from the lamp housing, not
the filament, leaving a zero point ~9 cm beyond the source. **Do not report a non-linear detector and do not
ask for the run to be redone.** The local exponent is the fastest tell: above 2 everywhere and approaching 2
as Z grows is the signature of z₀ < 0 (a positive offset would push it below 2).

## 8. A ruled sheet: census the rows from the rules, and test a stepped column for a constant slip

Referenced from steps 1 and 3 of `SKILL.md`. Measured on a 4-page single-slit diffraction record
(缝宽标称 0.200 mm / 0.300 mm, λ = 632.8 nm, Z = 60 cm), whose position column turned out to carry a
+1.0 mm slip after its 16th row.

**Row census from the printed rules.** Count the rows from the table's own rule lines, not from the read:
the darkness profile of one column band gives the line positions; `lines − 1` is that block's row capacity,
and the first block-row is the header.

```python
import pymupdf, io
from PIL import Image
d = pymupdf.open(pdf); pix = d[0].get_pixmap(dpi=200)
im = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L"); w, h = im.size; px = im.load()
x0, x1 = int(w*0.04), int(w*0.45)
rows = [sum(1 for x in range(x0, x1, 2) if px[x, y] < 140) for y in range(h)]
thr = max(rows)*0.55
lines = [y for y in range(1, h-1) if rows[y] > thr and rows[y] >= rows[y-1] and rows[y] >= rows[y+1]]
lines = [y for i, y in enumerate(lines) if i == 0 or y-lines[i-1] > 6]
```

Measured: the strongest column gave 23 lines → 22 rows → 21 data rows + header, matching the 21 pairs its
read returned — so the three positions the first pass appeared to skip were a genuine gap in the record,
not a dropped read. Run the profile on the darkest (left) column: fainter right-hand columns returned
20/17 lines and cannot be used as a census.

**Single-row crops for the disputed band.** Crop each rule-bounded row (line *k* to line *k+1*) as its own
600 dpi image and read several in one call (`view_image` `paths=[...]`, answer format "图1: x / I"). One
row per image cannot drift against its neighbour; this is what confirmed the tail rows and retired the
row-shift hypothesis.

**Constant-slip test on a stepped column.** When the sheet steps a coordinate by a fixed increment, the
physics fixes the spacing of the features read off it — diffraction minima are equally spaced, Δx = λZ/a —
so an interval that breaks the law by a constant is a transcription slip in the position column, not
physics. Fit the offset that restores uniform spacing and check the whole tail, not only the broken
interval:

| position column | minima (mm) | spacings | Δx̄ | a from Δx̄ |
|---|---|---|---|---|
| as recorded | 40.22 42.01 44.83 46.63 48.46 50.27 52.07 | 1.79 / **2.82** / 1.80 / 1.83 / 1.81 / 1.80 | — | — |
| tail −1.0 mm | 40.22 42.01 43.83 45.63 47.46 49.27 51.07 | 1.79 / 1.82 / 1.80 / 1.83 / 1.81 / 1.80 | 1.807 mm | 0.210 mm (标称 0.200) |

One value written too high (`42.500 → 43.800` where the row should read `42.800`) shifts every later
reading by the same constant, because the writer keeps adding the step to the wrong base. **Flag the block
and let the user confirm it; do not silently rewrite positions** — it moves the fitted centre x₀ and every
per-order result (here a₃ read 0.177 mm against 0.210 mm for k = 1, 2).

**Nominal-vs-measured ratio across a multi-table record.** When one record carries the same quantity at two
settings, the measured ratio must match the nominal ratio. Measured: the two slits' widths came out in the
ratio 1.25 (0.210 / 0.264 mm) while the labels read 0.200 / 0.300 = 1.5 — so the label, not the data, was
the thing to ask about. Ask before a nominal label reaches the deliverable: a %-deviation printed in the
report is a claim about that label.

## 9. Calorimetry sheet against its export: which source wins, and where a curve ends

Referenced from step 3 of `SKILL.md`.

**Authority between the two sources.** Temperatures come from the export when it exists (the user's rule:
温度取值以 txt 为准); the sheet supplies the masses, and each group's mass is its own weighing — a header or
leading value belongs to one group only. Measured: a header carried 286.15 g while the 保温杯 groups read
286.35 / 286.84 / 286.60 / 286.31 / 286.36 g and the 量热器 groups 26.78 / 26.90 / 26.87 g; the user ruled
each group uses its own value.

**Matching a record row to its file.** The recorded T₀/T₁ must show up on the export curves as a pre-event
plateau and a post-event minimum or plateau; that match orders ①②③ when the filenames alone leave it
ambiguous and settles a disputed cell. Measured: the recorded 45.4 ℃ was a curve maximum, and
12.5 / 8.2 / 15.2 / 16.4 / 17.8 ℃ reproduced the curves' minima or plateaus to 0.1 ℃ — enough to settle a
17.8-vs-15.4 conflict in favour of the plateau the record had read.

**End point on a disturbed curve.** When a curve stabilises after the event and only later departs again,
the end value is the **first plateau**; the later excursion belongs to a later operation on the same day.
Measured: a run held 16.0–16.3 ℃ (t ≈ 1240–1300 s) after the ice went in, returned to 21.6 ℃, then dropped
to 12.5 ℃ at t ≈ 1730 s. The recorded 12.5 gave L = 407 J/g (+21.9 %); the first plateau gave 319 J/g
(−4.4 %), and the user ruled for the plateau. Flag the pair and let the user choose — do not take either
silently.
