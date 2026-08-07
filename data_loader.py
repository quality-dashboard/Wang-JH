"""数据读取、筛选与质量监控 v3.0"""
import pandas as pd
import numpy as np
from config import (
    DQ_MISSING_RATE_WARN, DQ_DUPLICATE_RATE_WARN,
    DQ_OUTLIER_STD_K, DQ_TIME_GAP_MAX_HOURS,
)


def load_and_clean(file) -> pd.DataFrame:
    """读取并清洗数据，自动适配 xlsx/csv"""
    if file.name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(file, engine="openpyxl")
    else:
        df = pd.read_csv(file)

    df.columns = df.columns.str.strip().str.lower()

    col_map = {
        "硬度值": "硬度值", "hardness": "硬度值", "hrc": "硬度值",
        "日期": "日期", "date": "日期", "检测日期": "日期",
        "产品型号": "产品型号", "型号": "产品型号", "model": "产品型号",
        "班组": "班组", "班次": "班组", "shift": "班组",
        "设备": "设备", "设备编号": "设备", "machine": "设备",
        "操作员": "操作员", "检测员": "操作员",
    }
    df.rename(columns={k: v for k, v in col_map.items() if k in df.columns},
              inplace=True)

    if "硬度值" in df.columns:
        df["硬度值"] = pd.to_numeric(df["硬度值"], errors="coerce")
    if "日期" in df.columns:
        df["日期"] = pd.to_datetime(df["日期"], errors="coerce")

    return df


def auto_judge(df: pd.DataFrame, usl: float, lsl: float) -> pd.DataFrame:
    """根据规格限自动判定"""
    conditions = [df["硬度值"] > usl, df["硬度值"] < lsl]
    choices = ["不合格", "不合格"]
    df["判定结果"] = np.select(conditions, choices, default="合格")
    return df


# ==================== 新增：数据质量监控 ====================
def check_data_quality(df: pd.DataFrame) -> dict:
    """
    返回数据质量报告字典：
    {
        total_rows, missing_rate, duplicate_count,
        outlier_count, time_gaps, warnings: list[str]
    }
    """
    report = {"warnings": []}
    n = len(df)
    report["total_rows"] = n

    # 1. 缺失率
    missing = df.isnull().sum().sum()
    total_cells = n * len(df.columns)
    report["missing_rate"] = missing / total_cells if total_cells > 0 else 0
    if report["missing_rate"] > DQ_MISSING_RATE_WARN:
        report["warnings"].append(
            f"⚠️ 缺失率 {report['missing_rate']:.1%} 超过阈值 {DQ_MISSING_RATE_WARN:.0%}"
        )

    # 2. 重复记录
    dup_count = df.duplicated().sum()
    report["duplicate_count"] = int(dup_count)
    if n > 0 and dup_count / n > DQ_DUPLICATE_RATE_WARN:
        report["warnings"].append(
            f"⚠️ 重复记录 {dup_count} 条 ({dup_count/n:.1%})"
        )

    # 3. 异常值（仅检查硬度值）
    outlier_count = 0
    if "硬度值" in df.columns:
        vals = df["硬度值"].dropna()
        if len(vals) > 1:
            mean_v, std_v = vals.mean(), vals.std()
            outlier_count = int(((vals - mean_v).abs() > DQ_OUTLIER_STD_K * std_v).sum())
    report["outlier_count"] = outlier_count
    if outlier_count > 0:
        report["warnings"].append(f"⚠️ 发现 {outlier_count} 个异常值 (>{DQ_OUTLIER_STD_K}σ)")

    # 4. 时间连续性
    time_gaps = []
    if "日期" in df.columns:
        dates = df["日期"].dropna().sort_values()
        if len(dates) > 1:
            diffs = dates.diff().dt.total_seconds().dropna()
            max_gap_sec = DQ_TIME_GAP_MAX_HOURS * 3600
            gap_indices = diffs[diffs > max_gap_sec].index
            for idx in gap_indices:
                pos = dates.index.get_loc(idx)
                t_prev = dates.iloc[pos - 1] if pos > 0 else None
                t_curr = dates.iloc[pos]
                hours = diffs.loc[idx] / 3600
                time_gaps.append({
                    "from": str(t_prev), "to": str(t_curr), "hours": round(hours, 1)
                })
    report["time_gaps"] = time_gaps
    if time_gaps:
        report["warnings"].append(f"⚠️ 发现 {len(time_gaps)} 处时间断档 (>{DQ_TIME_GAP_MAX_HOURS}h)")

    return report


# ==================== 新增：动态筛选 ====================
def get_filter_options(df: pd.DataFrame) -> dict:
    """提取筛选器可选项"""
    opts = {}
    if "日期" in df.columns:
        valid_dates = df["日期"].dropna()
        opts["date_min"] = valid_dates.min().date() if len(valid_dates) else None
        opts["date_max"] = valid_dates.max().date() if len(valid_dates) else None
    else:
        opts["date_min"] = opts["date_max"] = None

    opts["models"] = sorted(df["产品型号"].unique().tolist()) if "产品型号" in df.columns else []
    opts["shifts"] = sorted(df["班组"].unique().tolist()) if "班组" in df.columns else []
    opts["machines"] = sorted(df["设备"].unique().tolist()) if "设备" in df.columns else []
    return opts


def apply_filters(df: pd.DataFrame,
                  date_range=None,
                  selected_models=None,
                  selected_shift=None,
                  selected_machine=None) -> pd.DataFrame:
    """应用所有筛选条件"""
    filtered = df.copy()

    if date_range and len(date_range) == 2 and "日期" in filtered.columns:
        start, end = date_range
        mask = (filtered["日期"].dt.date >= start) & (filtered["日期"].dt.date <= end)
        filtered = filtered[mask]

    if selected_models and "产品型号" in filtered.columns:
        filtered = filtered[filtered["产品型号"].isin(selected_models)]

    if selected_shift and selected_shift != "全部" and "班组" in filtered.columns:
        filtered = filtered[filtered["班组"] == selected_shift]

    if selected_machine and selected_machine != "全部" and "设备" in filtered.columns:
        filtered = filtered[filtered["设备"] == selected_machine]

    return filtered.reset_index(drop=True)