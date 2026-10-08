#!/usr/bin/env python3
r"""实验报告自检清单（2026-09-16 扩充版）。

检查项：
  1. 章节是否有空缺（复用 report_inspect）
  2. 是否残留占位/待补文字
  3. 是否误把分值写进报告（如「（4分）」）
  4. 图表编号是否连续、正文是否引用
  5. 公式守恒：成品公式数 ≥ 骨架公式数；骨架里非空的公式不得丢失
  6. 符号必须写成公式：正文/表头里不得出现 m_c、T_0、m₀、u_A、ΔT、√、×、≈、− 这类纯文本符号
  7. 公式内部不得含"手搓"的 Unicode 结构（₀₁₂ ¹²³ ⁻ √ …）——公式只能由 LaTeX 生成
  8. 骨架提示语（「(多方案并行…)」等）是否残留；是否有多余的"注："
  9. 图片尺寸清单与纵横比（偏差 >3% 报警：插图必须锁定纵横比）
 10. 步骤是否分条成段（「步骤：」+ ①②③… 各自成段）
 11. 骨架固定段落比对（提示项，人工确认）

用法：
    python report_check.py <报告.docx> [--skeleton 骨架.docx]
"""
from __future__ import annotations

import io
import re
import sys
import zipfile

try:                                    # Windows 控制台默认 GBK，打印 ✓/✗ 会 UnicodeEncodeError
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:                       # pragma: no cover
    pass

from docx import Document
from docx.oxml.ns import qn

from docx_io import iter_body_items, para_text, count_formulas
from report_inspect import inspect

try:
    import omml as _omml
except Exception:                                    # pragma: no cover
    _omml = None

PLACEHOLDER = re.compile(r"待补|待填|TODO|XXX|待完善|此处|（\s*）|\(\s*\)|_{3,}")
SCORE_LEAK = re.compile(r"[（(]\s*\d+\s*分\s*[）)]")
FIG_REF = re.compile(r"图\s*([0-9]+)")
TAB_REF = re.compile(r"表\s*([0-9]+)")
FIG_CAP = re.compile(r"^\s*图\s*([0-9]+)")
TAB_CAP = re.compile(r"^\s*表\s*([0-9]+)")
# 6) 只允许出现在公式里的符号/写法
SYMBOL_TEXT = re.compile(
    r"_[0-9A-Za-z{]"
    r"|[\u2080-\u2089\u2070-\u207f\u00b2\u00b3\u00b9]"
    r"|√|×|≈|−|(?<![A-Za-z])Δ[A-Za-z]|\b[uU]\([LTm]\)"
)
HINT_LEAK = re.compile(r"[（(][^）)]{0,60}(可增加|多方案|可自行|列出计算式|待填|此处)[^）)]{0,60}[）)]")
STRAY_NOTE = re.compile(r"^\s*注\s*[:：]")
STEP_MARK = re.compile(r"[①②③④⑤⑥⑦⑧⑨⑩]")
IMG_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"


MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def _all_text(doc):
    return [para_text(obj) for kind, obj in iter_body_items(doc) if kind == "p"]


def _omml_texts(doc):
    """成品里所有公式的可见文本。"""
    out = []
    for om in doc.element.body.iter("{%s}oMath" % MATH_NS):
        out.append("".join(t.text or "" for t in om.iter("{%s}t" % MATH_NS)))
    return out


def _find_skeleton(path):
    """在报告所在目录及其父目录找骨架（实验*…报告*.docx，且不是成品本身）。"""
    from pathlib import Path
    p = Path(path).resolve()
    cands = []
    for d in (p.parent, p.parent.parent):
        for f in sorted(d.glob("*.docx")):
            if f.name.startswith("~$") or f.name == p.name:
                continue
            if "实验报告" in f.name or "报告-20" in f.name:
                cands.append(f)
    return str(cands[0]) if cands else None


def _img_report(doc, path):
    """返回 [(媒体名, 显示宽cm, 高cm, 自然宽, 高, 畸变比)]

    畸变比已计入 a:srcRect 裁剪：>1 表示被横向拉伸。
    """
    z = zipfile.ZipFile(path)
    rels = z.read("word/_rels/document.xml.rels").decode("utf-8")
    rid2media = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="media/([^"]+)"', rels))
    try:
        from PIL import Image
    except Exception:
        Image = None
    nat = {}
    if Image:
        for name in set(rid2media.values()):
            try:
                im = Image.open(io.BytesIO(z.read("word/media/" + name)))
                nat[name] = im.size
            except Exception:
                pass
    xml = z.read("word/document.xml").decode("utf-8")
    out = []
    for blk in re.findall(r"<w:drawing>.*?</w:drawing>", xml, re.S):
        ext = re.search(r'<wp:extent cx="(\d+)" cy="(\d+)"', blk)
        emb = re.search(r'r:embed="(rId\d+)"', blk)
        if not (ext and emb):
            continue
        cx, cy = int(ext.group(1)) / 360000, int(ext.group(2)) / 360000
        name = rid2media.get(emb.group(1), "?")
        nw, nh = nat.get(name, (0, 0))
        crop = re.search(r'<a:srcRect([^/]*)/>', blk)
        l = t = r = b = 0
        if crop:
            for k, attr in (("l", "l"), ("t", "t"), ("r", "r"), ("b", "b")):
                m = re.search(r'%s="(\d+)"' % attr, " " + crop.group(1) + " ")
                if m:
                    v = int(m.group(1)) / 100000
                    if k == "l":
                        l = v
                    elif k == "t":
                        t = v
                    elif k == "r":
                        r = v
                    else:
                        b = v
        sw, sh = nw * (1 - l - r), nh * (1 - t - b)
        dist = (cx / cy) / (sw / sh) if (sh and sw and cy) else 0
        out.append((name, cx, cy, nw, nh, dist))
    return out


def check(path: str, skeleton: str | None = None):
    doc = Document(path)
    texts = _all_text(doc)
    joined = "\n".join(texts)
    body = "\n".join(t for t in texts if not (FIG_CAP.match(t) or TAB_CAP.match(t)))
    results = []

    info = inspect(path)
    results.append(("章节完整", not info["missing"],
                    "空缺: " + "、".join(info["missing"]) if info["missing"] else "全部已填"))

    ph = [t for t in texts if PLACEHOLDER.search(t)]
    results.append(("无占位残留", not ph, f"{len(ph)} 处" if ph else "OK"))

    leak = [t for t in texts if SCORE_LEAK.search(t)]
    results.append(("未写入分值", not leak, f"{len(leak)} 处" if leak else "OK"))

    fig_caps = [int(m.group(1)) for t in texts if (m := FIG_CAP.match(t))]
    tab_caps = [int(m.group(1)) for t in texts if (m := TAB_CAP.match(t))]
    fig_refs = {int(m) for m in FIG_REF.findall(body)}
    tab_refs = {int(m) for m in TAB_REF.findall(body)}

    def _seq_ok(nums):
        return nums == list(range(1, len(nums) + 1))

    results.append(("图编号连续", _seq_ok(fig_caps), f"图题 {fig_caps}，正文引用 {sorted(fig_refs)}"))
    results.append(("表编号连续", _seq_ok(tab_caps), f"表题 {tab_caps}，正文引用 {sorted(tab_refs)}"))

    n_omml = count_formulas(doc)
    results.append(("公式(原生)", True, f"{n_omml} 个 OMML"))

    # ---- 5) 公式守恒（对比骨架） ----
    skel = skeleton or _find_skeleton(path)
    if skel:
        sdoc = Document(skel)
        s_n = count_formulas(sdoc)
        s_txt = {t.strip() for t in _omml_texts(sdoc) if t.strip()}
        o_list = [t.strip() for t in _omml_texts(doc)]
        missing = [s for s in sorted(s_txt)
                   if len(s) >= 4 and not any(s in o or o in s for o in o_list)]
        ok = (n_omml >= s_n) and not missing
        detail = f"成品 {n_omml} ≥ 骨架 {s_n}"
        if missing:
            detail += f"；丢失骨架公式 {len(missing)} 条: " + "、".join(missing[:6])
        results.append(("公式守恒", ok, detail))
    else:
        results.append(("公式守恒", True, "未找到骨架，跳过（可用 --skeleton 指定）"))

    # ---- 6) 符号必须写成公式 ----
    bad_sym = [t for t in texts if SYMBOL_TEXT.search(t)]
    results.append(("符号已公式化", not bad_sym,
                    "OK" if not bad_sym else
                    f"{len(bad_sym)} 处纯文本符号：{bad_sym[0][:40]}"))

    # ---- 7) 公式内部不得有手搓 Unicode ----
    fake = [t for t in _omml_texts(doc)
            if _omml is not None and (set(t) & _omml.FAKE_STRUCT)]
    results.append(("公式非手搓", not fake,
                    "OK" if not fake else f"{len(fake)} 条公式含 Unicode 结构字符：例 {fake[0][:40]}"))

    # ---- 8) 骨架提示语 / 游离注 ----
    hints = [t for t in texts if HINT_LEAK.search(t)]
    results.append(("无骨架提示语", not hints,
                    "OK" if not hints else f"{len(hints)} 处：{hints[0][:40]}"))
    notes = [t for t in texts if STRAY_NOTE.match(t)]
    results.append(("无游离注", not notes,
                    "OK" if not notes else f"{len(notes)} 处：{notes[0][:40]}"))

    # ---- 9) 图片纵横比 ----
    imgs = _img_report(doc, path)
    dist_bad = [i for i in imgs if abs(i[5] - 1) > 0.03]
    results.append(("图片纵横比", not dist_bad,
                    f"{len(imgs)} 张图" + ("，全部正常" if not dist_bad else
                                         "；异常 " + "、".join(f"{i[0]}({i[5]:.2f}×)" for i in dist_bad))))

    # ---- 10) 步骤分条：实验内容区里不得有大段挤多条①②③ ----
    crowded = []
    for i, t in enumerate(texts):
        if not re.match(r"^实验内容\s*\d", t.strip()):
            continue
        for s in texts[i + 1:i + 16]:
            if re.match(r"^表\s*\d|^实验内容\s*\d|^【", s.strip()):
                break
            if len(STEP_MARK.findall(s)) >= 3:
                crowded.append(s)
    results.append(("步骤分条", not crowded,
                    "OK" if not crowded else
                    f"{len(crowded)} 段步骤挤在一起：{crowded[0][:50]}"))

    # ---- 11) 骨架段落比对（提示） ----
    if skel:
        sdoc = Document(skel)
        s_paras = {re.sub(r"\s+", "", para_text(p)) for kind, p in iter_body_items(sdoc)
                   if kind == "p" and para_text(p)}
        o_paras = {re.sub(r"\s+", "", t) for t in texts}
        diff = sorted({p for p in s_paras if len(p) >= 12 and p not in o_paras
                       and not HINT_LEAK.search(p)})
        results.append(("骨架文字比对", True,
                        f"{len(diff)} 处骨架文字未原样出现（删提示语/替换表题属正常，建议人工过一眼）"))
    return results, info


def _main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    skel = None
    args = list(argv)
    if "--skeleton" in args:
        i = args.index("--skeleton")
        skel = args[i + 1]
        del args[i:i + 2]
    results, info = check(args[0], skel)
    for name, ok, detail in results:
        print(f"[{'✓' if ok else '✗'}] {name:<12} {detail}")
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
