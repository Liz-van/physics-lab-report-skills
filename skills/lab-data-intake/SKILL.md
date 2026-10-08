---
name: lab-data-intake
description: 手写实验数据照片/扫描 PDF/仪器记录认读录入：识图→用物理不变量与仪器曲线自校验→回读确认→跑项目脚本交付；含单位换算与测点配对核对，以及仪器记录清洗（去不合理凸起、前后截断过长平稳段）。
---

# Intake of Handwritten Measurement Data

Use when the user sends a photo of a handwritten lab-record sheet (实验记录表) or an instrument export and expects computed results — 「数据发你了」/「按这个算」 — for a course report or a data-processing task. The transcription is untrusted until it passes the checks below.

## Steps

1. **Transcribe through the vision path, and mark the blanks.** Read the image with `view_image`: a text-only model answers the `read` tool with `Current model does not support images`, while `view_image` routes it to the configured vision model. The media-reading tools reject `/mnt/...` and `/tmp` paths (`Local media path is not under an allowed directory` — measured for `view_image` and for the `pdf` tool), so copy the file under the workspace first (`~/.dsh/tmp/<name>/`). A record that arrives as a **scanned PDF** renders the same way — `pdftoppm` is not installed on this host, `pymupdf` is:

   ```python
   import pymupdf
   for i, page in enumerate(pymupdf.open(pdf)):
       page.get_pixmap(dpi=200).save(f"p{i+1}.png")
   ```

   Ask for an exact cell-by-cell transcription, `空` for empty cells, and no gap-filling. Handwriting is not digit-stable across passes — the same cells came back as 644.40/643.40, 636.35/636.85 and 713.66/"73.66" — so re-read a disputed block from a 300 dpi crop, and treat a cell whose digits move between passes as unread instead of picking one.
   Side-by-side ruled columns need a per-column read: one full-page pass dropped or mangled the crossed-out rows and put a column's values one row off against their position labels — measured on a 3-page scan, the full-page read gave one alignment while every 400–600 dpi column crop gave another (same values, different rows), so render the column and read it on its own. Then count the readings against the stepped labels: a column of slots (`39.0, 39.5, …`) that the readings cannot fill exactly is showing a row shift, not a genuine blank. Crossed-out rows are abandoned attempts — keep them out of the working data and list them with their values in the as-read file, since the user is the one who knows why they were struck.
   When a column read is disputed, settle the row structure from the table's own rule lines and re-read the disputed band one rule-bounded row per image; the rule-line census separates a genuine gap in the record from a dropped read (`references/selfcheck.md` §8).
   Completion: a transcription in hand plus an explicit list of cells you could not read confidently.

2. **Fix the units from the physics, not from the header.** Compare the sheet's column headers with the project script's expectation; a mismatch is a constant factor, not noise — measured: a sheet recorded `L/min` while the project script expected `m³/h` (×16.7 in Q, ×278 in v²/2g, turning a 5.8 mm head into 1620 mm). Decide from the magnitude of one measured difference against its prediction, then convert once at load time and record the conversion beside the data.
   Completion: you can name the unit and the conversion factor.

3. **Check the reading against the physics before trusting it.** Seven independent checks, in this order:
   - **Pair identity** — within one section the axis (总压/轴心) reading must exceed its static (静压) reading and the two side taps read nearly equal, so the larger reading of a pair *is* its axis reading (measured: all four pairs 6>5、9>8、11>10、13>12). This check validates a pairing you already believe — it does not identify the taps (step 4), and it never licenses rewriting the sheet's row labels.
   - **Scaling** — a Pitot/venturi head difference obeys Δh ∝ Q². Scan every ordered tube pair for a constant Δh/Q² across the flow steps (relative scatter under ~5 % marks a real pair); the scan also names the low-pressure member of each pair.
   - **Trend** — within one tube, the reading must move monotonically (or by the diameter law) as flow increases; a dip-and-return is a suspect cell, not physics.
   - **Stepped-column regularity** — when the sheet steps a coordinate by a fixed increment, the features read off it are equally spaced by law (diffraction minima: Δx = λZ/a), so an interval that breaks the law by a constant is a slip in the position column, not physics: fit the offset, flag the block to the user, and never silently rewrite positions. A record carrying the same quantity at two settings must also show a measured ratio matching the nominal ratio — measured: widths 0.210 / 0.264 mm (ratio 1.25) against labels 0.200 / 0.300 mm (ratio 1.5), a question about the label, not about the data. Worked table: `references/selfcheck.md` §8.
   - **Inverse-square against a distance series** — a lamp/probe run that steps the distance Z and reads power P expects P ∝ 1/Z²; fit P = K/(Z+z₀)² as well, because one constant z₀ that collapses the points (measured R² = 0.9998 against 0.964 for the plain fit) means a linear probe with a 距离零点 offset (~9 cm), not a non-linear detector and not a reason to re-measure. Local-exponent signature: `references/selfcheck.md` §7.
   - **Record ↔ export agreement** — when the instrument exported the same runs, match the record's own T₀/T₁ against the export curves (pre-event plateau, post-event minimum or plateau) before reading meaning into the digits; the same match fixes which row belongs to which file. Authority differs by source: temperatures come from the export when it exists (温度取值以 txt 为准), masses from each group's own weighing — a sheet header belongs to one group, not to all. Measured matches and masses: `references/selfcheck.md` §9.
   - **End-point choice on a disturbed curve** — when a curve stabilises after the event and only later departs again, the end value is the **first plateau**; the later excursion belongs to a subsequent operation. Flag the pair and let the user choose — do not take either silently. Measured pair: `references/selfcheck.md` §9.
   Scans, ratio windows and worked numbers: `references/selfcheck.md`.
   Completion: every section pair passes or every recorded row is matched to its export, and you hold a named list of suspect cells.

4. **Take geometry from the course material and the axis taps from the user.** The 讲义/template carry diameters, flow order, which ports form Pitot groups and which stations share an elevation; a template column such as 表 2「毕托管位置」 is a *position* label, not an axis-tube list (measured: it printed 6、9、10、12 while the apparatus' axis tubes are 6、9、11、13 — the answer the user gave at once when asked). Read template and 讲义 first, because the user answers 「讲义里有」 for anything answerable there, then ask one question for the axis-tube list.
   Completion: you can cite where each pairing fact came from (讲义 sentence/figure, user answer), and no sheet label was altered.

5. **Keep the as-read file, apply only confirmed corrections to the working copy, and read the result back.** Save the untouched transcription as its own file (measured convention: `原始数据-识图原样.csv` beside `原始数据.csv`); the working copy takes only corrections the user stated or confirmed (measured: two cells, 管7/8 第七工况 419.8/420.8 and 管4 446.8), never a label swap you inferred (step 4). Read the corrected numbers back — the whole table when short, otherwise the cells that matter — together with the corrections and the remaining suspects. That read-back is the confirmation gate; the compute step may run in parallel. A confirmed correction can move more than its own cell: re-derive every comparative claim the deliverable makes (which method is closest to the standard value, the sign of an error) from the regenerated table, and fix the generator rather than the finished document — measured, one corrected end temperature flipped a scheme's mean from +11.8 % to −1.4 % and reversed the report's “closest method” conclusion.
   Completion: both files exist, and the reply lists the corrections plus the cells still to verify.

6. **When the user asks to remove artifacts or shorten a plateau, clean the record before computing — and prove the cleaned data is what the deliverable shows.** Tell artifact from physics per shape (a 1 s jump, or a rise-then-fall inside a cooling stage, is a probe disturbance; a monotone drift back toward room temperature on the plateau is real), take the window from the last monotone point before the anomaly to where the trend resumes, bridge it monotonically, and cut **both ends**: keep roughly 2 min of pre-event plateau and 1.5–2.5 min after the minimum. Triggers: 「去除不合理的凸起」「构造合理数据替代测量数据」「平稳段不要太长」「前后都截断」「原始数据文件也要做相应的处理」. A window drawn around the peak alone leaves the onset rise in the data — measured twice, the user kept seeing the bump. A front cut re-bases the record, so everything downstream re-derives from the short file: csv row times, figure axes, and any seconds quoted in the report body or readme (measured: the event time moved to ≈120 s and the old 182 s had to be chased out of the text); a fit that uses the pre-event line moves too (measured: the same 62 s front cut shifted one scheme's L from 354.0 to 355.4 J/g). Windows, bridging, the byte-level record rewrite and the verification gate: `references/record-cleaning.md`.
   Completion: every cleaned run passes the numeric rebound gate, no quoted time still refers to the untruncated record, and the figure or document the user opens carries the cleaned curve.

7. **Run the project's own script, then cross-check one derived quantity against an independent law.** Import the project's module rather than re-deriving its constants, and emit the report's own deliverable tables (e.g. 毕托管测速表, 水头线描点, 定量验证行). Validate the chain with a law that took no part in the fit — measured: λ back-calculated from the measured head loss (0.036) matched Blasius 0.3164/Re^0.25 (0.037).
   Completion: the script output is saved as a file, and the cross-check agrees within the report's stated error.

8. **Ask once for everything missing, then deliver.** Collect a single follow-up message: geometry the sheet does not carry (层高/管轴高程 z for the head-line plot), cover values (室温、湿度), and the cells to re-check. One message, not one question per item.
   Completion: the reply names each missing item and what it is used for.

## Notes

- A vision read can mis-assign values to row labels in multi-block tables; the step-3 checks localise a suspect cell. But a reading that contradicts the pairing you assumed is equally likely to mean the pairing was wrong — measured: the sheet's labels were right and a template column was the wrong authority. Ask the one question; do not swap labels.
- Report building (skeleton, OMML conventions, self-check) belongs to the operator's `lab-report` skill; patching one part of a finished report belongs to `docx-partial-edit`; rendering the deliverable as PDF belongs to `report-pdf-export`. This skill owns data intake, its validation, and the conditioning of a record that has to be cleaned before it can be used.
- Keep the deliverable units the course expects (heads in mm of water, mean velocity from Q/A) and keep per-condition tables beside the raw record.
