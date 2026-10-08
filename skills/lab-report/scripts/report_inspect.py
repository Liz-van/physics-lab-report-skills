#!/usr/bin/env python3
r"""盘点实验报告 docx：列出章节、判断每节是否已填写。

用于流程第 0 步（增量补全：只补缺失部分）。

用法：
    python report_inspect.py <报告.docx>
    python report_inspect.py <报告.docx> --json
"""
from __future__ import annotations

import json
import re
import sys

from docx_io import iter_body_items, para_text, count_formulas
from docx.oxml.ns import qn

M_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath"
A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}blip"

# 报告常见章节（顺序即文档顺序）
# 标题匹配（归一化后 fullmatch）
SECTION_PATTERNS = [
    ("实验目的", r"实验目的"),
    ("仪器用具", r"仪器用具|仪器与用具|实验仪器"),
    ("原理概述", r"原理概述|实验原理|原理概述与实验规划|实验规划与基本原理概述"),
    ("实验前思考题", r"实验前思考题|预习思考题"),
    ("实验内容", r"实验内容|实验内容、步骤、结果及讨论|实验内容、步骤、结果"),
    ("实验步骤", r"实验步骤|实验步骤、结果|步骤、结果"),
    ("实验记录", r"实验记录|数据记录|记录表格"),
    ("数据处理", r"数据处理|数据处理、分析与讨论|数据处理与分析|数据处理、分析讨论"),
    ("分析讨论", r"分析讨论|分析与讨论|误差分析|结果与讨论"),
    ("实验后思考题", r"实验后思考题"),
    ("结论", r"结论"),
    ("附件", r"附件"),
    ("注意事项", r"实验报告注意事项|实验安全与实验室注意事项|实验注意事项"),
]

COVER_RE = re.compile(r"^(专业|年级|姓名|学号|日期|教师签名|成绩|课程名称|学院)\s*$")
BRACKET_RE = re.compile(r"^[【\[（(]\s*([^】\]）)]+?)\s*[】\]）)]")


def _norm(t: str) -> str:
    """归一化标题：去掉【】、（）、尾冒号句号等。"""
    t = t.strip()
    m = BRACKET_RE.match(t)
    if m:
        t = m.group(1)
    t = re.sub(r"[（(].*?[)）]", "", t)
    return t.strip(" \u3000:：。、")


def _match_head(norm: str):
    if not norm or len(norm) > 20:
        return None
    for name, pat in SECTION_PATTERNS:
        if re.fullmatch(pat, norm):
            return name
    return None


def _count_images(element) -> int:
    return len(element.findall(f".//{A_NS}"))


def detect_headings(items):
    """返回 [(item_index, section_name, raw_title)]，同名字节只取首次出现。

    优先用【】包裹的标题；若全文没有【】标题，再回退到纯文本标题匹配。
    """
    bracket_hits, plain_hits, cover_hit = [], [], None
    seen = set()
    for idx, (kind, obj) in enumerate(items):
        if kind != "p":
            continue
        raw = para_text(obj)
        if not raw:
            continue
        norm = _norm(raw)
        if cover_hit is None and COVER_RE.fullmatch(norm):
            cover_hit = (idx, "封面", raw)
        name = _match_head(norm)
        if not name or name in seen:
            continue
        seen.add(name)
        (bracket_hits if BRACKET_RE.match(raw.strip()) else plain_hits).append(
            (idx, name, raw))

    chosen = bracket_hits if len(bracket_hits) >= 3 else (
        bracket_hits + plain_hits)
    if cover_hit:
        chosen = chosen + [cover_hit]
    chosen.sort(key=lambda x: x[0])
    return chosen


def inspect(path: str):
    from docx import Document
    doc = Document(path)
    items = list(iter_body_items(doc))
    marks = detect_headings(items)

    sections = []
    for k, (idx, name, title) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(items)
        span = items[idx + 1:end]
        chars = tables = formula = images = 0
        for kind, obj in span:
            if kind == "p":
                # 表格内的段落也会作为 p 事件出现，这里统一计入，
                # tbl 事件只计数不重复计字数
                chars += len(para_text(obj))
                formula += len(obj._p.findall(f".//{M_NS}"))
                images += _count_images(obj._p)
            else:
                tables += 1
        sections.append({
            "section": name,
            "title": title,
            "filled": (chars > 20) or tables > 0 or images > 0,
            "chars": chars,
            "tables": tables,
            "formulas": formula,
            "images": images,
        })

    all_ps = [obj for kind, obj in items if kind == "p"]
    return {
        "file": str(path),
        "paragraphs": len(all_ps),
        "tables": len(doc.element.body.findall('.//' + qn('w:tbl'))),
        "formulas_total": count_formulas(doc),
        "sections": sections,
        "missing": [s["section"] for s in sections if not s["filled"]],
    }


def _main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    as_json = "--json" in argv
    path = [a for a in argv if not a.startswith("-")][0]
    info = inspect(path)
    if as_json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
        return 0
    print(f"文件: {info['file']}")
    print(f"段落 {info['paragraphs']} | 表格 {info['tables']} | 公式 {info['formulas_total']}")
    print("-" * 56)
    print(f"{'章节':<12}{'状态':<6}{'字数':>6}{'表':>4}{'式':>4}{'图':>4}")
    for s in info["sections"]:
        print(f"{s['section']:<12}{'已填' if s['filled'] else '空缺':<6}"
              f"{s['chars']:>6}{s['tables']:>4}{s['formulas']:>4}{s['images']:>4}")
    if info["missing"]:
        print("待补章节:", "、".join(info["missing"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
