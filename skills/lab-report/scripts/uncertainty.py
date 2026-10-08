#!/usr/bin/env python3
r"""不确定度与有效数字工具（大学物理实验标准流程）。

纯标准库实现，无第三方依赖。

用法示例：
    python uncertainty.py a 10.2 10.3 10.1 10.2 10.3
    python uncertainty.py b 0.05
    python uncertainty.py result 21.05 0.32 g
"""
from __future__ import annotations

import math
import sys
from decimal import Decimal, ROUND_HALF_UP

# 极差法系数 d_n (n=2..10)
D_N = {2: 1.13, 3: 1.69, 4: 2.06, 5: 2.33, 6: 2.53,
       7: 2.70, 8: 2.85, 9: 2.97, 10: 3.08}


def sig(x: float, n: int) -> float:
    """保留 n 位有效数字。"""
    if x == 0 or not math.isfinite(x):
        return x
    exp = math.floor(math.log10(abs(x)))
    q = Decimal(1).scaleb(exp - n + 1)
    return float(Decimal(str(x)).quantize(q, rounding=ROUND_HALF_UP))


def mean(values) -> float:
    v = list(values)
    return sum(v) / len(v)


def std(values) -> float:
    """样本标准差（n-1）。"""
    v = list(values)
    n = len(v)
    if n < 2:
        raise ValueError("样本标准差至少需要 2 个数据")
    m = mean(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1))


def type_a(values, method: str = "bessel") -> float:
    """A 类不确定度。

    method='bessel'（n>=6）用 s/sqrt(n)；method='range' 用极差/d_n。
    """
    v = list(values)
    n = len(v)
    if n < 2:
        raise ValueError("A 类不确定度至少需要 2 次测量")
    if method == "range":
        if n not in D_N:
            raise ValueError(f"极差法支持 n=2..10，当前 n={n}")
        return (max(v) - min(v)) / D_N[n]
    if method != "bessel":
        raise ValueError("method 只能是 'bessel' 或 'range'")
    return std(v) / math.sqrt(n)


def type_b(delta: float, dist: str = "uniform") -> float:
    """B 类不确定度。delta 为仪器误差限。

    dist: uniform -> Δ/√3（默认）；triangular -> Δ/√6；normal -> Δ/3
    """
    k = {"uniform": math.sqrt(3), "triangular": math.sqrt(6), "normal": 3.0}.get(dist)
    if k is None:
        raise ValueError("dist 只能是 uniform / triangular / normal")
    return abs(delta) / k


def combine(*u_list) -> float:
    """直接量合成：各分量平方和开根。"""
    return math.sqrt(sum(float(u) ** 2 for u in u_list))


def propagate(*rel_terms) -> float:
    """间接量相对不确定度合成：传入 (系数, 相对不确定度) 对。

    u_r(y) = sqrt( Σ (p_i * u_r(x_i))^2 )
    """
    total = 0.0
    for p, u in rel_terms:
        total += (p * u) ** 2
    return math.sqrt(total)


def expanded(uc: float, k: float = 2.0) -> float:
    """扩展不确定度，默认 k=2（约 95%）。"""
    return k * uc


def align_digits(mean_value: float, u: float) -> tuple[float, float]:
    """把 U 修约到 1~2 位有效数字，并让 x̄ 末位与 U 对齐。"""
    u = abs(u)
    if u == 0:
        return mean_value, 0.0
    exp = math.floor(math.log10(u))
    # 首位为 1 或 2 时保留 2 位有效数字，否则 1 位
    lead = u / (10 ** exp)
    nd = 2 if lead < 3 else 1
    u_r = sig(u, nd)
    q = Decimal(1).scaleb(exp - nd + 1)
    m_r = float(Decimal(str(mean_value)).quantize(q, rounding=ROUND_HALF_UP))
    return m_r, u_r


def format_result(mean_value: float, u: float, unit: str = "", k: float = 2.0):
    """返回 (结果字符串, 相对不确定度百分比)。"""
    m_r, u_r = align_digits(mean_value, u)
    # 按对齐后的 U 决定小数位
    nd = max(0, -Decimal(str(u_r)).as_tuple().exponent)
    s = f"{m_r:.{nd}f} ± {u_r:.{nd}f}"
    if unit:
        s += f" {unit}"
    rel = f"{u / abs(mean_value) * 100:.2f}%" if mean_value else "N/A"
    return s, rel


def _main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd == "a":
        vals = [float(x) for x in argv[1:]]
        n = len(vals)
        method = "bessel" if n >= 6 else "range"
        ua = type_a(vals, method)
        print(f"n={n}  mean={mean(vals):.6g}  s={std(vals) if n>1 else float('nan'):.6g}")
        print(f"u_A({method}) = {ua:.6g}")
    elif cmd == "b":
        delta = float(argv[1])
        dist = argv[2] if len(argv) > 2 else "uniform"
        print(f"u_B({dist}) = {type_b(delta, dist):.6g}")
    elif cmd == "result":
        m = float(argv[1]); u = float(argv[2])
        unit = argv[3] if len(argv) > 3 else ""
        k = float(argv[4]) if len(argv) > 4 else 2.0
        U = expanded(u, k)
        s, rel = format_result(m, U, unit)
        print(f"U(k={k}) = {U:.6g}")
        print(f"结果: {s}   (相对不确定度 {rel})")
    else:
        print(f"未知命令: {cmd}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
