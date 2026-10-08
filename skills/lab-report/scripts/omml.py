#!/usr/bin/env python3
r"""LaTeX -> Word 原生公式(OMML)。**只接受 LaTeX 输入**。

2026-09-16 起硬规则（用户要求，见 SKILL.md §硬规则）：
  * 所有公式一律用 LaTeX 描述，由 pandoc 编译成原生 OMML；
  * LaTeX 源码必须是**纯 ASCII**（中文只允许写在 \\text{...} 里；单位 ℃ 可直接写）：
    禁止用 Unicode 字符"手搓"公式结构——
      下标  ₀₁₂…   → 写 _0 _1 _2
      上标  ¹²³ ⁻¹  → 写 ^2 ^{-1}
      根号  √       → 写 \\sqrt{}
      乘号  ×       → 写 \\times
      约等  ≈       → 写 \\approx
      减号  −       → 写 -
      点乘  ·       → 写 \\cdot
      角度  °       → 写 ^\\circ
      撇    ′       → 写 '
      希腊  Δ α μ   → 写 \\Delta \\alpha \\mu
  * 生成的 OMML 统一字体（ASCII 用 Cambria Math、中文用宋体），不把本机字体名写进文档。

用法：
    python omml.py --selftest              # 自检
    python omml.py --latex 'L=\\frac{a}{b}'  # 打印单条 OMML
    python omml.py --from-json f.json out.txt

依赖：pandoc（apt install pandoc）；python-docx 仅注入时需要。
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

MATH_RE = re.compile(r"<m:oMath[ >].*?</m:oMath>", re.S)
NS = ('xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
      'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"')

# LaTeX 里禁止出现的字符 -> 建议写法
FIX_HINT = {
    "₀": "_0", "₁": "_1", "₂": "_2", "₃": "_3", "₄": "_4", "₅": "_5",
    "₆": "_6", "₇": "_7", "₈": "_8", "₉": "_9",
    "ₓ": "_x", "ₐ": "_a", "ₑ": "_e", "ₘ": "_m", "ₙ": "_n", "ₚ": "_p",
    "⁰": "^0", "¹": "^1", "²": "^2", "³": "^3", "⁴": "^4", "⁵": "^5",
    "⁶": "^6", "⁷": "^7", "⁸": "^8", "⁹": "^9",
    "⁻": "^{-}", "⁺": "^{+}", "ⁿ": "^n", "⁼": "^=",
    "√": r"\sqrt{}", "×": r"\times", "≈": r"\approx", "−": "-",
    "·": r"\cdot", "°": r"^\circ", "′": "'", "″": "''",
    "≤": r"\leq", "≥": r"\geq", "≠": r"\neq", "±": r"\pm",
    "Δ": r"\Delta", "δ": r"\delta", "α": r"\alpha", "β": r"\beta",
    "γ": r"\gamma", "λ": r"\lambda", "μ": r"\mu", "π": r"\pi",
    "ρ": r"\rho", "σ": r"\sigma", "τ": r"\tau", "Σ": r"\Sigma",
    "Ω": r"\Omega", "ω": r"\omega", "∫": r"\int", "∞": r"\infty",
    "→": r"\to", "⇒": r"\Rightarrow", "∂": r"\partial", "∇": r"\nabla",
}

# 生成物里若出现这些字符，说明结构是"手搓"的（pandoc 只会用 m:sSub / m:rad 表达）
FAKE_STRUCT = set("₀₁₂₃₄₅₆₇₈₉ₐₑₒₓₕₖₗₘₙₚₛₜ⁻⁺⁼ⁿⁱ⁰¹²³⁴⁵⁶⁷⁸⁹√")


# 允许直接写在公式里的单位字符（不是"手搓结构"，是中文报告惯例）
ALLOW_LITERAL = {"℃"}


def bad_chars(tex: str) -> list[str]:
    """返回 LaTeX 源码里不合规的字符（非 ASCII，且不在 \\text{} 内）。"""
    stripped = re.sub(r"\\text\{[^{}]*\}", "", tex)
    return sorted({c for c in stripped if ord(c) > 127 and c not in ALLOW_LITERAL})


def check_latex(tex: str) -> None:
    bad = bad_chars(tex)
    if bad:
        tips = "、".join(f"{c!r}→{FIX_HINT.get(c, '?')}" for c in bad)
        raise ValueError(f"公式必须用纯 LaTeX 写法（不要 Unicode 字符）：{tips}\n  {tex}")


def clean_fragment(frag: str, size_pt: float | None = None,
                   cjk_font: str = "宋体") -> str:
    """统一生成物字体/字号，避免把本机字体名（Noto Sans CJK SC 等）写进文档。"""
    frag = re.sub(r'\sw:eastAsia="[^"]*"', f' w:eastAsia="{cjk_font}"', frag)
    frag = re.sub(r'\sw:hint="[^"]*"', "", frag)
    if size_pt:
        hp = int(round(size_pt * 2))
        frag = re.sub(r'<w:sz w:val="\d+"/>', f'<w:sz w:val="{hp}"/>', frag)
    return frag


def _pandoc_bin() -> str:
    p = shutil.which("pandoc")
    if not p:
        raise RuntimeError("未找到 pandoc，请先安装：apt install pandoc")
    return p


def latex_to_omml(items, keep_o_math_para: bool = False,
                  size_pt: float | None = None):
    """批量把 LaTeX 转成 OMML 片段。

    items: list[str] 或 list[dict{"latex": str, "display": bool}]
    返回 list[str]，每个元素是一段可直接注入的 <m:oMath ...> XML。
    display=True 的公式在 pandoc 侧写成 $$...$$（独立行），注入时可放进
    oMathPara 居中显示；display=False 用于行内混排。
    """
    norm = []
    for it in items:
        if isinstance(it, str):
            norm.append({"latex": it, "display": True})
        else:
            norm.append({"latex": it["latex"], "display": bool(it.get("display", True))})
    for it in norm:
        check_latex(it["latex"])

    lines = []
    for it in norm:
        tex = it["latex"].strip()
        # 注意：pandoc 要求 $ 内侧不能有空格，否则不识别为公式
        lines.append(f"$${tex}$$" if it["display"] else f"${tex}$")
        lines.append("")  # 每个公式独立成段
    md = "\n".join(lines)

    tmpd = Path(tempfile.mkdtemp(prefix="omml_"))
    try:
        src = tmpd / "f.md"
        out = tmpd / "f.docx"
        src.write_text(md, encoding="utf-8")
        subprocess.run([_pandoc_bin(), str(src), "-o", str(out)],
                       check=True, capture_output=True)
        with zipfile.ZipFile(out) as z:
            doc = z.read("word/document.xml").decode("utf-8")
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)

    found = MATH_RE.findall(doc)
    if len(found) != len(norm):
        raise RuntimeError(f"公式数量不匹配：期望 {len(norm)}，实际 {len(found)}")
    out_xml = []
    for frag in found:
        inner = frag[frag.index(">") + 1: frag.rindex("</m:oMath>")]
        frag = f"<m:oMath {NS}>{inner}</m:oMath>"
        out_xml.append(clean_fragment(frag, size_pt))
    return out_xml


_CACHE: dict = {}


def inline(latex: str, size_pt: float | None = None) -> str:
    """单条行内公式（带缓存，同一公式只编译一次）。"""
    key = (latex, size_pt)
    if key not in _CACHE:
        _CACHE[key] = latex_to_omml([{"latex": latex, "display": False}],
                                    size_pt=size_pt)[0]
    return _CACHE[key]


def block(latex: str, size_pt: float | None = None) -> str:
    """单条独立居中公式（带缓存）。"""
    key = ("blk", latex, size_pt)
    if key not in _CACHE:
        _CACHE[key] = latex_to_omml([{"latex": latex, "display": True}],
                                    size_pt=size_pt)[0]
    return _CACHE[key]


def make_o_math_para(omml_frag: str) -> str:
    """把 oMath 包成独立段落用的 oMathPara（居中显示公式）。"""
    return (f'<m:oMathPara {NS}><m:oMathParaPr><m:jc m:val="center"/>'
            f'</m:oMathParaPr>{omml_frag}</m:oMathPara>')


def insert_omml_into_paragraph(paragraph, omml_frag: str):
    """把 OMML 追加到指定段落末尾。"""
    from docx.oxml import parse_xml
    paragraph._p.append(parse_xml(omml_frag))


def append_formula_paragraph(doc, omml_frag: str, center: bool = True):
    """新增一个段落并放入公式，返回该段落。"""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    p = doc.add_paragraph()
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    insert_omml_into_paragraph(p, omml_frag)
    return p


def omml_math_text(frag: str) -> str:
    """取 OMML 里的可见文本（用于自检/指纹）。"""
    return "".join(re.findall(r"<m:t[^>]*>(.*?)</m:t>", frag, re.S))


def _selftest():
    # 1) 禁止 Unicode 输入
    for bad in ["m₀C₀", "u_A=√2×0.02/√3", "T₁−T₀", r"L(J·g⁻¹)"]:
        try:
            check_latex(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"未拦住非法写法: {bad}")
    for good in [r"m_0c_0", r"u_A=\sqrt{2}\times0.02/\sqrt{3}", r"T_1-T_0",
                 r"L/(\mathrm{J\cdot g^{-1}})", r"T_{\text{实际}}"]:
        check_latex(good)

    # 2) 结构正确：下标/上标/根号/分数
    frags = latex_to_omml([
        {"latex": r"m_0c_0", "display": False},
        {"latex": r"\sqrt{2}\times0.02/\sqrt{3}\approx0.016", "display": False},
        {"latex": r"\lambda=\frac{1}{m}\left[m_0c_0(T_0-T_1)\right]", "display": True},
        {"latex": r"u_C=\sqrt{u_A^2+u_B^2}", "display": False},
        {"latex": r"T'=0^\circ\mathrm{C}", "display": False},
    ], size_pt=10.5)
    assert len(frags) == 5
    joined = "".join(frags)
    for token in ("m:sSub", "m:sSup", "m:f", "m:rad", "m:t"):
        assert token in joined, f"缺少结构 {token}"
    for f in frags:
        assert "<m:oMath " in f and "</m:oMath>" in f
        assert not (set(omml_math_text(f)) & FAKE_STRUCT), f"生成物含手搓字符: {f[:120]}"
        assert "Noto" not in f and "w:eastAsia" not in f  # 不写本机字体名
    # 3) 缓存
    a, b = inline(r"m_0c_0"), inline(r"m_0c_0")
    assert a == b
    print("omml.py selftest OK：拦住 Unicode 写法；下标/上标/根号/分数结构齐全；字体/字号已统一")
    return 0


def _main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--selftest":
        return _selftest()
    if argv[0] == "--latex":
        print(latex_to_omml([{"latex": argv[1], "display": False}])[0])
        return 0
    if argv[0] == "--from-json":
        data = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        frags = latex_to_omml(data)
        print(f"生成 {len(frags)} 条 OMML")
        if len(argv) > 2:
            Path(argv[2]).write_text("\n\n".join(frags), encoding="utf-8")
            print("已写出:", argv[2])
        return 0
    print(f"未知参数: {argv[0]}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
