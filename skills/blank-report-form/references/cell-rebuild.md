# Rebuilding a layout-table cell, cell by cell

Referenced from step 4 of `SKILL.md`. Every snippet below was run against the borrowed 薄透镜 official report template (whole page inside a 1×1 `w:tbl`) and produced the recorded result.

## 1. The shape of the file

Top level is three 1×1 tables, one per page; the cover blocks and every record table are nested inside their cell. `doc.tables` shows 3, the file holds 14 — so walk recursively and treat `w:p` and `w:tbl` as siblings in order.

```python
from docx.oxml.ns import qn

def blocks(tc):
    """Top-level paragraph/table elements of a cell/cell-element, in order."""
    return [k for k in tc.iterchildren() if k.tag in (qn("w:p"), qn("w:tbl"))]

def walk_body(doc):
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    for e in doc.element.body.iter():
        if e.tag == qn("w:p"):
            yield ("p", Paragraph(e, doc))
        elif e.tag == qn("w:tbl"):
            yield ("tbl", Table(e, doc))
```

Measured cell shapes worth knowing: page 1 cell 0 = `[p, tbl(成绩栏 2×8), p, tbl(信息表 3×4), p×15]`; page 2 cell 0 = `[p, tbl(信息表 5×4), p×3, tbl(器材表 2×4), p×4, tbl, p×3, tbl, p]`; page 3 cell 0 = `[p, tbl(信息表 4×4), p×90]`.

## 2. Keep the official tables, clear the rest

```python
import copy

def take_tables(tc):
    """Deep-copy the nested tables (order kept) and empty the cell."""
    tbls = [copy.deepcopy(k) for k in blocks(tc) if k.tag == qn("w:tbl")]
    for k in blocks(tc):
        tc.remove(k)
    return tbls
```

Then append back only what this report needs, in print order:

```python
grade_tbl, info_tbl = take_tables(tc)
tc.append(grade_tbl)      # official 成绩栏, untouched
P(tc, [])
tc.append(info_tbl)       # official 信息表, untouched
P(tc, [])
P(tc, ["【实验报告注意事项】"], bold=True)
...
```

## 3. Paragraphs with mixed prose and formulas

```python
from docx.oxml import parse_xml
import omml                                     # operator lab-report skill: LaTeX -> OMML via pandoc

def _rpr(bold, size):
    b = "<w:b/><w:bCs/>" if bold else ""
    return ('<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
            f'w:eastAsia="宋体"/>{b}'
            f'<w:sz w:val="{int(round(size * 2))}"/><w:szCs w:val="{int(round(size * 2))}"/>')

def P(tc, parts=None, size=11.5, bold=False):
    """Append a paragraph to a cell; str = text, ("m", latex) = inline formula."""
    xml = [f'<w:p xmlns:w="{W_NS}">']
    for part in parts or []:
        if isinstance(part, str):
            xml.append(f'<w:r><w:rPr>{_rpr(bold, size)}</w:rPr>'
                       f'<w:t xml:space="preserve">{esc(part)}</w:t></w:r>')
        else:
            xml.append(omml.inline(part[1], size))
    xml.append("</w:p>")
    tc.append(parse_xml("".join(xml)))
```

`esc()` is `&`/`<`/`>` escaping; `omml.inline` fragments carry their own namespace declarations, so only the `w:p` wrapper needs `xmlns:w`.

## 4. New tables: build in the document, then move the element in

`doc.add_table` appends to the body — writing the cells first and moving the `w:tbl` afterwards is what lets the new table inherit the document's styles (`Table Grid` exists in this template).

```python
from docx.enum.table import WD_ALIGN_VERTICAL, WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT
from docx.shared import Cm

def add_table(doc, tc, data, widths, size=10.5, row_h=0.85):
    t = doc.add_table(rows=len(data), cols=len(data[0]))
    t.style = doc.styles["Table Grid"]
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for ri, row in enumerate(data):
        for ci, val in enumerate(row):
            cell = t.cell(ri, ci)
            cell.width = Cm(widths[ci])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            write_cell_par(cell.paragraphs[0], val if isinstance(val, list) else [val], size)
        t.rows[ri].height = Cm(row_h)
        t.rows[ri].height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
    for ci, w in enumerate(widths):
        t.columns[ci].width = Cm(w)
    tc.append(t._tbl)          # moves the element out of the body into the cell
    P(tc, [], size=size)       # the cell must not end on a table
    return t
```

A blank record table is a header row of lists plus N empty rows: `[[["序号"], ["位置 ", ("m", r"x/\mathrm{mm}")], ...]] + [[str(i), "", "", ""] for i in range(1, 23)]`.

## 5. Verification one-liners

```bash
python -c "import docx,sys;d=docx.Document(sys.argv[1]);print(len(d.tables), len(d.element.body.findall('.//{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath')))" 实验报告.docx
pandoc 实验报告.docx -t markdown | grep -n 'I/I_{0}'     # LaTeX back = real OMML
python ~/.dsh/skills/lab-report/scripts/report_check.py 实验报告.docx --skeleton 骨架.docx
```

Measured result of the delivered blank form: 3 top-level tables, 21 `oMath`, `report_check.py` → 公式(原生) ✓、表编号连续 [1..5] ✓、步骤分条 ✓, plus the expected 「未写入分值」 and 「占位残留」 notices.
