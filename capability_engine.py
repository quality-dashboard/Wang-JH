"""
capability_engine.py — 过程能力计算引擎
计算 Cp / Cpk / Pp / Ppk
（Python 3.9 兼容版）
"""
from typing import Optional

import numpy as np


def compute_capability(data: np.ndarray, usl: float, lsl: float) -> Optional[dict]:
    """
    计算过程能力指标。

    参数:
        data: 硬度值数组
        usl: 上规格限
        lsl: 下规格限

    返回:
        dict 或 None（数据不足/标准差为零时）
    """
    n = len(data)
    if n < 2:
        return None

    mean = float(np.mean(data))
    std_within = float(np.std(data, ddof=1))  # 样本标准差

    if std_within == 0:
        return None

    # Cp = (USL - LSL) / (6σ)
    cp = (usl - lsl) / (6 * std_within)

    # Cpk = min(Cpu, Cpl)
    cpu = (usl - mean) / (3 * std_within)
    cpl = (mean - lsl) / (3 * std_within)
    cpk = min(cpu, cpl)

    # Pp 和 Ppk 用总体标准差
    std_overall = float(np.std(data, ddof=0))
    if std_overall == 0:
        pp = 0.0
        ppk = 0.0
    else:
        pp = (usl - lsl) / (6 * std_overall)
        ppu = (usl - mean) / (3 * std_overall)
        ppl = (mean - lsl) / (3 * std_overall)
        ppk = min(ppu, ppl)

    return {
        "Cp": round(cp, 4),
        "Cpk": round(cpk, 4),
        "Pp": round(pp, 4),
        "Ppk": round(ppk, 4),
        "mean": mean,
        "std_within": std_within,
        "std_overall": std_overall,
        "n": n,
    }