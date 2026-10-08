#!/usr/bin/env python3
r"""统一作图规范（大学物理实验）。

- 中文字体、数字/公式 Times 风格
- 无网格；图题由调用方放在图上方（本模块只画图，不写题）
- 300 dpi 输出 PNG

用法：
    python plot_utils.py --selftest --out /tmp/fig_selftest.png
"""
from __future__ import annotations

import sys
from pathlib import Path


def setup_style():
    """设置 matplotlib 全局样式，返回 plt 模块。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import rcParams

    for f in ["Noto Sans CJK SC", "WenQuanYi Zen Hei", "Source Han Sans SC",
              "SimSun", "Microsoft YaHei", "DejaVu Sans"]:
        rcParams["font.sans-serif"] = [f] + list(rcParams.get("font.sans-serif", []))
    rcParams["axes.unicode_minus"] = False
    rcParams["figure.dpi"] = 300
    rcParams["savefig.dpi"] = 300
    rcParams["savefig.bbox"] = "tight"
    rcParams["axes.grid"] = False
    rcParams["font.size"] = 11
    rcParams["axes.linewidth"] = 0.8
    rcParams["mathtext.fontset"] = "stix"
    return plt


def line_plot(x, y, xlabel="", ylabel="", title="", label=None,
              marker="o", linestyle="-", out=None, figsize=(5.2, 3.6)):
    plt = setup_style()
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(x, y, marker=marker, linestyle=linestyle, label=label,
            markersize=5, linewidth=1.2)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    if label:
        ax.legend()
    return _finish(fig, out)


def scatter_fit(x, y, xlabel="", ylabel="", label="数据", fit_label=None,
                degree=1, out=None, figsize=(5.2, 3.6), show_equation=True):
    """散点 + 线性(或多项式)拟合线，返回 (fig, info)。"""
    import numpy as np
    plt = setup_style()
    xa = np.asarray(x, dtype=float)
    ya = np.asarray(y, dtype=float)
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(xa, ya, "o", label=label, markersize=5)
    coef = np.polyfit(xa, ya, degree)
    xs = np.linspace(xa.min(), xa.max(), 200)
    ax.plot(xs, np.polyval(coef, xs), "-", linewidth=1.2,
            label=fit_label or f"{degree} 次拟合")
    info = {"coef": coef.tolist()}
    if degree == 1:
        k, b = coef
        yhat = np.polyval(coef, xa)
        ss_res = float(((ya - yhat) ** 2).sum())
        ss_tot = float(((ya - ya.mean()) ** 2).sum())
        r2 = 1 - ss_res / ss_tot if ss_tot else float("nan")
        info.update({"k": float(k), "b": float(b), "r2": r2})
        if show_equation:
            ax.text(0.05, 0.95, f"$y = {k:.4g}\\,x + {b:.4g}$\n$R^2 = {r2:.5f}$",
                    transform=ax.transAxes, va="top")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend()
    fig, _ = _finish(fig, out)
    return fig, info


def _finish(fig, out):
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out)
    return fig, out


def _selftest(out):
    import math
    x = list(range(1, 11))
    y = [2.0 * xi + 1.0 + 0.1 * math.sin(xi) for xi in x]
    fig, info = scatter_fit(x, y, xlabel="x", ylabel="y", out=out)
    print(f"selftest OK -> {out}")
    print(f"k={info['k']:.4f} b={info['b']:.4f} R2={info['r2']:.6f}")
    return 0


def _main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--selftest":
        out = "/tmp/fig_selftest.png"
        if "--out" in argv:
            out = argv[argv.index("--out") + 1]
        return _selftest(out)
    print(f"未知参数: {argv[0]}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
