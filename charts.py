"""
charts.py — 所有图表绘制函数
使用 Plotly 绘制，返回 go.Figure 对象
"""
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from config import RESULT_COLORS


# ============================================================
# SPC 控制图
# ============================================================
def plot_xbar_chart(spc: dict, subgroup_size: int):
    """
    绘制 Xbar 控制图。
    返回 (fig, violations)
    """
    from spc_engine import detect_violations

    means = spc["xbar_means"]
    x_labels = [f"#{i+1}" for i in range(len(means))]

    fig = go.Figure()

    # 控制限
    fig.add_hline(y=spc["xbar_ucl"], line_dash="dash", line_color="red",
                  annotation_text=f"UCL={spc['xbar_ucl']:.2f}")
    fig.add_hline(y=spc["xbar_lcl"], line_dash="dash", line_color="red",
                  annotation_text=f"LCL={spc['xbar_lcl']:.2f}")
    fig.add_hline(y=spc["xbar_bar"], line_dash="dot", line_color="blue",
                  annotation_text=f"X̄̄={spc['xbar_bar']:.2f}")

    # 数据点
    fig.add_trace(go.Scatter(
        x=x_labels, y=means,
        mode="lines+markers",
        name="X̄",
        line=dict(color="#2c3e50", width=1.5),
        marker=dict(size=6, color="#3498db"),
    ))

    fig.update_layout(
        title=f"X̄ 控制图（子组 n={subgroup_size}）",
        xaxis_title="子组编号",
        yaxis_title="均值 (HRC)",
        height=380,
        margin=dict(t=50, b=30, l=50, r=20),
    )

    violations = detect_violations(spc)
    return fig, violations


def plot_r_chart(spc: dict):
    """绘制 R 控制图"""
    ranges = spc["r_ranges"]
    x_labels = [f"#{i+1}" for i in range(len(ranges))]

    fig = go.Figure()

    fig.add_hline(y=spc["r_ucl"], line_dash="dash", line_color="red",
                  annotation_text=f"UCL={spc['r_ucl']:.2f}")
    fig.add_hline(y=spc["r_lcl"], line_dash="dash", line_color="red",
                  annotation_text=f"LCL={spc['r_lcl']:.2f}")
    fig.add_hline(y=spc["r_bar"], line_dash="dot", line_color="blue",
                  annotation_text=f"R̄={spc['r_bar']:.2f}")

    fig.add_trace(go.Scatter(
        x=x_labels, y=ranges,
        mode="lines+markers",
        name="R",
        line=dict(color="#2c3e50", width=1.5),
        marker=dict(size=6, color="#e67e22"),
    ))

    fig.update_layout(
        title="R 控制图（极差）",
        xaxis_title="子组编号",
        yaxis_title="极差 (HRC)",
        height=380,
        margin=dict(t=50, b=30, l=50, r=20),
    )
    return fig


# ============================================================
# 仪表盘（Gauge）
# ============================================================
def plot_gauge(value: float, title: str, threshold: float = 1.33):
    """绘制过程能力仪表盘"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"size": 18}},
        number={"suffix": "", "font": {"size": 32}},
        gauge={
            "axis": {"range": [0, 2.5], "tickwidth": 1},
            "bar": {"color": "#3498db"},
            "steps": [
                {"range": [0, 1.0], "color": "#fdedec"},
                {"range": [1.0, threshold], "color": "#fef9e7"},
                {"range": [threshold, 2.5], "color": "#eafaf1"},
            ],
            "threshold": {
                "line": {"color": "red", "width": 3},
                "thickness": 0.8,
                "value": threshold,
            },
        },
    ))
    fig.update_layout(height=280, margin=dict(t=50, b=10, l=30, r=30))
    return fig


# ============================================================
# 趋势图
# ============================================================
def plot_trend(df, usl: float, lsl: float):
    """硬度值趋势图（带规格限）"""
    fig = go.Figure()

    x_axis = df["日期"] if "日期" in df.columns else list(range(len(df)))

    fig.add_trace(go.Scatter(
        x=x_axis, y=df["硬度值"],
        mode="lines+markers",
        name="硬度值",
        line=dict(color="#3498db", width=1.5),
        marker=dict(size=4),
    ))

    fig.add_hline(y=usl, line_dash="dash", line_color="red",
                  annotation_text=f"USL={usl}")
    fig.add_hline(y=lsl, line_dash="dash", line_color="red",
                  annotation_text=f"LSL={lsl}")

    fig.update_layout(
        title="硬度趋势图",
        xaxis_title="日期",
        yaxis_title="硬度 (HRC)",
        height=350,
        margin=dict(t=50, b=30, l=50, r=20),
    )
    return fig


# ============================================================
# 饼图（合格/不合格）
# ============================================================
def plot_pie(df):
    """合格率饼图"""
    if "判定结果" not in df.columns:
        return go.Figure()

    counts = df["判定结果"].value_counts()
    labels = counts.index.tolist()
    values = counts.values.tolist()
    colors = [RESULT_COLORS.get(l, "#95a5a6") for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        marker=dict(colors=colors),
        textinfo="label+percent",
        hole=0.4,
    ))
    fig.update_layout(
        title="合格率分布",
        height=350,
        margin=dict(t=50, b=20, l=20, r=20),
    )
    return fig


# ============================================================
# 型号柱状图
# ============================================================
def plot_model_bar(df):
    """各型号均值硬度柱状图"""
    if "产品型号" not in df.columns:
        fig = go.Figure()
        fig.update_layout(title="各型号均值硬度（无型号数据）", height=350)
        return fig

    stats = df.groupby("产品型号")["硬度值"].agg(["mean", "count"]).reset_index()
    stats.columns = ["型号", "均值", "数量"]

    fig = go.Figure(go.Bar(
        x=stats["型号"],
        y=stats["均值"],
        text=stats["数量"].apply(lambda x: f"n={x}"),
        textposition="outside",
        marker_color="#3498db",
    ))
    fig.update_layout(
        title="各型号平均硬度",
        xaxis_title="产品型号",
        yaxis_title="均值 (HRC)",
        height=350,
        margin=dict(t=50, b=30, l=50, r=20),
    )
    return fig


# ============================================================
# 箱线图
# ============================================================
def plot_box(df):
    """按型号分组的箱线图"""
    if "产品型号" in df.columns:
        fig = go.Figure()
        for model in df["产品型号"].unique():
            subset = df[df["产品型号"] == model]["硬度值"]
            fig.add_trace(go.Box(y=subset, name=str(model)))
        fig.update_layout(title="各型号硬度分布（箱线图）", height=350,
                          margin=dict(t=50, b=30, l=50, r=20))
    else:
        fig = go.Figure(go.Box(y=df["硬度值"], name="全部数据"))
        fig.update_layout(title="硬度分布（箱线图）", height=350,
                          margin=dict(t=50, b=30, l=50, r=20))
    return fig


# ============================================================
# 直方图（带规格限）
# ============================================================
def plot_histogram(data, usl: float, lsl: float, mean_val: float):
    """硬度分布直方图 + 规格限 + 均值线"""
    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=data,
        nbinsx=25,
        name="频次",
        marker_color="#3498db",
        opacity=0.7,
    ))

    fig.add_vline(x=usl, line_dash="dash", line_color="red",
                  annotation_text=f"USL={usl}")
    fig.add_vline(x=lsl, line_dash="dash", line_color="red",
                  annotation_text=f"LSL={lsl}")
    fig.add_vline(x=mean_val, line_dash="dot", line_color="green",
                  annotation_text=f"μ={mean_val:.2f}")

    fig.update_layout(
        title="硬度分布直方图",
        xaxis_title="硬度 (HRC)",
        yaxis_title="频次",
        height=380,
        margin=dict(t=50, b=30, l=50, r=20),
    )
    return fig