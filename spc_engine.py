"""
spc_engine.py — SPC 计算引擎
实现 Xbar-R 控制图计算 + 西电判异准则
（Python 3.9 兼容版）
"""
from typing import Optional

import numpy as np

# Xbar-R 控制图系数表（按子组大小 n 查表）
# 来源：GB/T 4091 / AIAG SPC Manual
_D2 = {2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326,
       6: 2.534, 7: 2.704, 8: 2.847, 9: 2.970, 10: 3.078}
_D3 = {2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0,
       6: 0.0, 7: 0.076, 8: 0.136, 9: 0.184, 10: 0.223}
_D4 = {2: 3.267, 3: 2.574, 4: 2.282, 5: 2.114,
       6: 2.004, 7: 1.924, 8: 1.864, 9: 1.816, 10: 1.777}
_A2 = {2: 1.880, 3: 1.023, 4: 0.729, 5: 0.577,
       6: 0.483, 7: 0.419, 8: 0.373, 9: 0.337, 10: 0.308}


def compute_xbar_r(data: np.ndarray, subgroup_size: int) -> Optional[dict]:
    """
    计算 Xbar-R 控制图参数。

    参数:
        data: 一维数组，所有硬度值（按时间顺序）
        subgroup_size: 子组大小

    返回:
        dict 或 None（数据不足时）
    """
    n = len(data)
    if n < subgroup_size * 2:
        return None

    # 按子组分组（丢弃末尾不完整的子组）
    num_subgroups = n // subgroup_size
    trimmed = data[: num_subgroups * subgroup_size]
    groups = trimmed.reshape(num_subgroups, subgroup_size)

    # 各子组均值和极差
    xbar_means = groups.mean(axis=1)
    r_ranges = groups.max(axis=1) - groups.min(axis=1)

    # 总均值和平均极差
    xbar_bar = xbar_means.mean()
    r_bar = r_ranges.mean()

    # 查表系数
    k = min(max(subgroup_size, 2), 10)
    a2 = _A2[k]
    d3 = _D3[k]
    d4 = _D4[k]
    d2 = _D2[k]

    # 控制限
    xbar_ucl = xbar_bar + a2 * r_bar
    xbar_lcl = xbar_bar - a2 * r_bar
    r_ucl = d4 * r_bar
    r_lcl = d3 * r_bar

    # 估计标准差 σ̂ = R̄ / d2
    sigma_est = r_bar / d2 if d2 > 0 else 0

    return {
        "xbar_means": xbar_means,
        "r_ranges": r_ranges,
        "xbar_bar": xbar_bar,
        "r_bar": r_bar,
        "xbar_ucl": xbar_ucl,
        "xbar_lcl": xbar_lcl,
        "r_ucl": r_ucl,
        "r_lcl": r_lcl,
        "sigma_est": sigma_est,
        "num_subgroups": num_subgroups,
        "subgroup_size": subgroup_size,
    }


def detect_violations(spc: dict) -> dict:
    """
    西电判异准则（4条）：
    1. 1点超出控制限
    2. 连续9点在中心线同侧
    3. 连续6点递增或递减
    4. 连续14点交替上下

    返回: {"规则描述": [违规子组索引列表], ...}
    """
    means = spc["xbar_means"]
    ucl = spc["xbar_ucl"]
    lcl = spc["xbar_lcl"]
    center = spc["xbar_bar"]
    n = len(means)

    violations = {
        "准则1：1点超出控制限": [],
        "准则2：连续9点在中心线同侧": [],
        "准则3：连续6点递增或递减": [],
        "准则4：连续14点交替上下": [],
    }

    # 准则1
    for i in range(n):
        if means[i] > ucl or means[i] < lcl:
            violations["准则1：1点超出控制限"].append(i)

    # 准则2：连续9点同侧
    for i in range(n - 8):
        segment = means[i: i + 9]
        if all(v > center for v in segment) or all(v < center for v in segment):
            for j in range(i, i + 9):
                if j not in violations["准则2：连续9点在中心线同侧"]:
                    violations["准则2：连续9点在中心线同侧"].append(j)

    # 准则3：连续6点递增或递减
    for i in range(n - 5):
        segment = means[i: i + 6]
        increasing = all(segment[j] < segment[j + 1] for j in range(5))
        decreasing = all(segment[j] > segment[j + 1] for j in range(5))
        if increasing or decreasing:
            for j in range(i, i + 6):
                if j not in violations["准则3：连续6点递增或递减"]:
                    violations["准则3：连续6点递增或递减"].append(j)

    # 准则4：连续14点交替上下
    for i in range(n - 13):
        segment = means[i: i + 14]
        alternating = True
        for j in range(12):
            direction1 = segment[j + 1] - segment[j]
            direction2 = segment[j + 2] - segment[j + 1]
            if direction1 * direction2 >= 0:
                alternating = False
                break
        if alternating:
            for j in range(i, i + 14):
                if j not in violations["准则4：连续14点交替上下"]:
                    violations["准则4：连续14点交替上下"].append(j)

    return violations