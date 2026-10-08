---
name: blank-report-form
description: 做一份空白报告 / 不用做数据处理：以同课程官方模板为骨架，用讲义内容搭出可手写填写的报告表。
---

# Building a Blank Fillable Report

Use when the deliverable is a **form**, not a filled report — 「只需要做一份空白报告」「不用做数据处理」「留空白表格」「空白的，我手填」 — for a course experiment. The content comes from the 讲义's own structure: purpose, apparatus, safety notes, steps, questions, and empty record tables.

## Steps

1. **Settle the skeleton before writing anything, and say which file you took.** Look in the experiment's own folder first. When it holds only the 讲义 and no report docx, stop and ask the user to approve borrowing another experiment's official report from the same course — measured: the 单缝衍射 folder had one lecture PDF, and the approved skeleton was the sibling optics experiment's `薄透镜焦距和透镜组基本参数的测量-实验报告.docx` (same course, same three page headers, same fonts). Do not invent a layout. Record the source and the approval in the project's `代码/readme.md`.
   Completion: you can name the skeleton file and who approved it.

2. **Extract the lecture's content, reading embedded formulas as pictures.** `pymupdf`'s `page.get_text()` recovers the prose but not numbered formulas — in this 讲义 the equations (B2-1…B2-5) are images, so the extraction left the caption line bare (`处的光强为：` then `（B2-1）`). Render the pages and read them with `view_image`; the media tools reject `/mnt/...` and `/tmp` paths, so copy the PNGs under the workspace first:

   ```python
   import pymupdf
   for i, page in enumerate(pymupdf.open(pdf)):
       page.get_pixmap(dpi=150).save(f"p{i+1}.png")
   ```

   Take: 实验目的, 器材(含型号), 注意事项, 实验内容与步骤, 数据分析要求, 实验前/后思考题.
   Completion: every numbered formula is transcribed as LaTeX, and the question list is in hand.

3. **Map the skeleton's page tables, and keep the official blocks.** The whole page sits in a 1×1 `w:tbl`, so `doc.paragraphs` returns a handful of items while `cell.text` and `cell.paragraphs` hide the nested tables (measured on the borrowed template: 14 tables, only 3 at top level — 成绩栏 2×8, 信息表 3×4 / 5×4 / 4×4, 器材表 2×4). Walk the body recursively. Keep the official 成绩栏 and 信息表 blocks by deep-copying their `w:tbl` elements; rebuild everything else.
   Completion: you can list each page's nested tables and say which ones you keep.

4. **Rebuild one cell at a time, in print order, ending on a paragraph.** Per cell: collect the top-level `w:p`/`w:tbl` children → deep-copy the `w:tbl`s you keep → remove them all → append the kept table, then your new paragraphs, then your new tables, in the order they should print; close with an empty `w:p`, as the template's own cells do. Build new tables with `doc.add_table(...)` so they inherit the document's styles (`Table Grid`), write their cells, then move the element in with `tc.append(t._tbl)`. Helpers, run against this template: `references/cell-rebuild.md`.
   Completion: reopening the file shows the intended block order on each page.

5. **Print the prompts and the structure; leave every answer blank.** Headers, 注意事项, 步骤 and 题干 print; answer space is empty paragraphs (measured: 14 after the theory block, 4–6 after each question). Symbols and relations inside prompts and table headers go in as native OMML from LaTeX (`\theta_k`, `I/I_0`, `Z^{-2}`) — never Unicode subscripts. Record tables get a header row plus empty rows with `row.height = Cm(0.85)` and `WD_ROW_HEIGHT_RULE.AT_LEAST` so a pen fits, and the row count traces to a measurement interval — the lecture's, or a teacher's red annotation on the 讲义 where it overrides the lecture (measured: a red 0.5–1 mm → 0.2–0.3 mm note on the fringe-pattern measurement took those tables from 22 rows to 40; every 5 cm from 20 to 100 cm → 17 rows).
   Completion: no cell holds an answer, and each blank table's row count traces back to a measurement interval.

6. **Verify by reopening, then prove the formulas are real equations.** Reopen with python-docx and count `oMath` (measured: 21); `pandoc <doc> -t markdown` must render each symbol back to LaTeX; `report_check.py` reports 表 1–5 连续 and 步骤分条 OK. Grep the finished document for the **skeleton experiment's name**: a borrowed template can carry it in the body titles, not only in the page headers (measured: a report from the borrowed 薄透镜 skeleton still read that experiment's name in four body section titles while its page headers were already correct). The same check also flags 「未写入分值」 when the official template's marks were kept, and 「占位残留」 for the blank `______` rules — both are expected in a blank form: report them as expected instead of silently "fixing" them.
   Completion: the counts and the round-trip are recorded, and each warning is named as expected or as a defect.

7. **Report the choices "blank" left open, one line each.** Measured open items after delivery: whether to keep the official template's 分值 marks (（3 分）（2 分）…), and whether to embed the 讲义's figures (AB2-1…AB2-5) into the theory page. State them with the one-line change each needs, and say plainly that no computed data and no cover personal data were written.
   Completion: the reply gives the path, what each page prints, and the open choices.

## Notes

- A blank form is a **build**, not a patch: `docx-partial-edit` owns adding one part to a finished document without disturbing the rest, the operator's `lab-report` skill owns filling a report with computed content and its conventions, `report-pdf-export` owns a print/PDF copy. This skill owns the fillable form.
- Keep the generator as a project script (measured: `实验报告/代码/make_blank_report.py`) with the skeleton path, output path and content blocks in a config block, so a later 「把分值去掉」 is one edit and one re-run rather than a manual docx edit — and so a record that reads more points than the estimate (measured: 36 and 47 readings against the 40 rows built) is `rows=N` plus a re-run instead of dropped readings.
- Work from a local copy when the skeleton sits on a Windows mount: one `docx.Document()` open of the `/mnt/d` template raised `PackageNotFoundError` while the file was present, and the same read succeeded after `cp` to a local path. The finished docx goes back with a plain `cp`.
