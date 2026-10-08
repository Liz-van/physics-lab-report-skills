---
name: lab-handout-archive
description: 老师发来新版实验指引/讲义/报告模板，要「保存」或删旧版：md5 核对入实验文件夹、与文件夹里的旧版 diff 并报告变化、列旧版清单待确认后删除。
---

# 实验讲义 / 指引 归档与版本更新

Use when the user forwards an updated course handout (实验指引 / 讲义 / 报告模板 docx) for a 大物实验 experiment and asks to keep it — measured as 「保存这两个文件」, sometimes only after the files arrived with no text at all. This is the intake side: the report skills consume these files, they do not maintain them.

## Steps

1. **Treat the bare file as "not yet a task".** A handout that arrives with no instruction is covered by the standing file rule (MEMORY.md): stay silent, do not act on it, and wait. The task starts with the explicit follow-up — 「保存这两个文件」/「归档」/「删掉旧版」.
   Completion: you are working from a stated instruction, not from the arrival of a file.

2. **Save into the experiment's own folder, name preserved, md5-checked.** One folder per experiment, named as the course names it: `<实验根目录>/<实验名>/`. Copy each handout under its own name with the transfer tail (the `---<hash>` suffix a chat transfer appends) removed, then `md5sum` source and destination and confirm they match. Do not overwrite: if that name already exists, report it instead of replacing anything.
   Completion: both files sit in their folders with matching md5, and nothing was overwritten.

3. **Diff the new handout against the copy already in the folder, and report what changed.** Compare `word/document.xml` text (split on `</w:p>`, strip tags) plus the `w:tbl` and `word/media/` counts — a bumped table count is how a re-scored template shows up first. Report the changes as short, concrete lines: 分值重排 (e.g. 原理概述 12→10), new page-section headers (预习报告 / 实验记录 / 分析与讨论), figure numbering and marks, new required sections, changed parameters (measured: a driving frequency 0.525 Hz → 0.56 Hz, a 选做 marker becoming （选）（+1 分）), and whether the file is a *new* version at all (compare bytes first — an identical resend needs no work).
   ```python
   import zipfile, re
   z = zipfile.ZipFile(p)
   txt = re.sub(r'<[^>]+>', '', re.sub(r'</w:p>', '\n', z.read('word/document.xml').decode('utf8')))
   ```
   Completion: the reply names the changed items, not merely 「已保存」.

4. **List the superseded versions and stop there.** Print each old file with its path and size and ask 删/留. Never delete in the same turn as saving — the standing rule is list first, then act only on an explicit confirmation. When a rename is asked for instead, rename and say so.
   Completion: the old files are listed with sizes and no deletion happened yet.

5. **After a confirmed delete, show the final folder state.** Delete exactly what was listed, then print what remains in each folder, so the user sees the same list they approved.
   Completion: the reported folder contents match the confirmed list.

## Notes

- These handouts are the input for report work: producing a report, a preview, or a blank form belongs to the operator's `lab-report` / `lab-preview` skills, data transcription to `lab-data-intake`, and PDF rendering to `report-pdf-export`. This skill owns only the versioned intake of the teacher's files.
- Keep the course's folder and file naming; do not introduce a second scheme or move existing files. An explicit request to reorganize one experiment folder into `实验报告/{代码,数据,图表}` (「整理一下文件夹」) is a different task — `lab-folder-organize`.
- Deletion on the Windows mount through WSL does not use the Recycle Bin — say so when deleting.
