# Cleaning an instrument record before it is used

Referenced from step 6 of `SKILL.md`. The numbers below come from a K-type thermometer export
(MS6514, resolution 0.1 °C) whose curves had to be conditioned before the report could use them.
The shipped deliverable carried the cleaned record files, the derived tables and the regenerated curves.

## 1. Decide artifact vs physics, per shape

| shape in the record | verdict |
|---|---|
| 1 s jump of several °C, decaying over tens of seconds | contact disturbance (probe lifted, ice on the tip) — artifact |
| temperature **rising then falling** inside a cooling stage | artifact (measured: 18.5 → 20.4 → 18.6 °C over ~90 s) |
| ringing after such a spike (two or three decaying swings) | the same artifact — one window, not two |
| monotone slow drift toward room temperature on the plateau | physical (the vessel is below room temperature) — keep it, and say so |

## 2. The window must cover the whole non-monotone stretch

Take the last point where the trend was still monotone before the anomaly, and the first point where it
resumes. A window drawn around the peak alone leaves the onset rise in the data and the regenerated
figure looks unchanged — measured: a first pass used 398–452 s of a stretch that starts rising at 365 s,
and the user twice reported the figure had not been updated at all. Windows that shipped: 365–452,
340–440, 310–470, 246–310 s.

## 3. Bridge monotonically, then quantize

Replace the window with a monotone cubic (PCHIP / Fritsch–Carlson limited Hermite) between the two
measured endpoint values. Endpoint slopes come from a least-squares fit on ±30 s outside the window,
clipped so the bridge cannot rise where the stage is cooling. Write the values back quantized to the
instrument resolution (0.1 °C) — the record must not carry more decimals than the instrument does.

## 4. Truncate both ends at the record layer

The protocol reads "continue to the minimum, then about 2 min more"; records ran 3–5 min past
stabilisation, and some started long before the event (one export began ~20 min early, the rest carried
the pre-event plateau from t = 0). Cut each run **in the record file itself** so txt, derived csv,
cleaned csv, plots and report all end at the same place:

- **back** — leave ~1.5–2.5 min of plateau after the minimum (shipped ends 1350 / 730 / 700 / 700 /
  650 / 460 s);
- **front** — keep ~2 min of pre-event plateau, enough for the T₀ window the analysis uses
  (`[t_B-40, t_B-10]`); shipped starts 1130 / 150 / 146 / 149 / 125 / 62 s, giving 220–580 s records.

Carry the consequences into the rebuild: the truncated record re-bases its own time axis, so the event
sits at ≈120 s in the csv and every seconds value quoted in the report body or readme (e.g.
`投冰 t = 182 s`) must be regenerated rather than copied; and the pre-event line AB is fitted from what
survives the front cut, so a shorter lead-in moves the extrapolated T₀′/T₁′ and the reported L
(measured: 354.0 → 355.4 J/g after a 62 s front cut on one run).

## 5. Write the processed record byte-level; keep the untouched original

The export is fixed-width text with CRLF and a non-UTF-8 unit column. Rewrite only the numeric token of
each affected line and keep every other byte, alignment and line ending intact; never re-serialise the
file. Keep the pristine export in the source package, write the processed record into the deliverable
package, and point the pipeline at the processed record (`convert → csv → cleaned → analyse`) — when a
report is rebuilt from new data, give it its own package and leave the previous one untouched. Prove the
edit per file: count the lines whose only difference from the original is the numeric field; expect
exactly one structural difference, at the truncation boundary.

## 6. Verify numerically, then look at the artifact

Numeric gate per cleaned run: `max(T − running minimum)` over the post-event series, skipping the first
~30 s of mixing, must be ≤ ~0.2 °C. A residual of 0.4–1.4 °C means the window is still short — that much
survived a first pass and is exactly what the user kept seeing. Then check what the user actually opens:
the figure file must be newly written (mtime), an image embedded in a docx is a **copy taken at build
time** (see `docx-partial-edit` step 5), and a crop of the panel should be looked at rather than inferred
from the numbers.
