"""
质量数据看板 - Streamlit App
运行: streamlit run kanban.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ============ 页面配置 ============
st.set_page_config(
    page_title="质量数据看板",
    page_icon="📊",
    layout="wide"
)

st.title("📊 质量数据看板")
st.markdown("---")

# ============ 侧边栏：文件上传 ============
with st.sidebar:
    st.header("📁 数据上传")
    uploaded_file = st.file_uploader(
        "上传检测数据文件",
        type=["xlsx", "xls", "csv"],
        help="支持 .xlsx / .xls / .csv 格式"
    )

# ============ 列名智能映射 ============
COLUMN_MAPPING = {
    "日期": ["日期", "检测日期", "date", "Date", "DATE"],
    "产品型号": ["产品型号", "型号", "产品", "model", "Model", "MODEL"],
    "硬度值": ["硬度值", "硬度值（HRC）", "硬度值(HRC)", "硬度(HRC)", "硬度", "hardness", "Hardness", "HARDNESS"],
    "判定结果": ["判定结果", "结果", "判定", "result", "Result", "RESULT"],
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """将各种列名变体统一映射为标准列名"""
    rename_map = {}
    for std_name, variants in COLUMN_MAPPING.items():
        for variant in variants:
            if variant in df.columns:
                rename_map[variant] = std_name
                break
    df.rename(columns=rename_map, inplace=True)
    return df


# ============ 数据读取与处理 ============
df = None

if uploaded_file is not None:
    try:
        # 根据文件类型读取
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # 清洗列名：去除空格、换行、制表符等隐藏字符
        df.columns = df.columns.astype(str).str.strip().str.replace(r'\s+', '', regex=True)

        # 智能列名映射
        df = normalize_columns(df)

        st.sidebar.success(f"✅ 文件读取成功，共 {len(df)} 条记录")

    except Exception as e:
        st.sidebar.error(f"❌ 文件读取失败：{e}")
        st.stop()
else:
    st.info("👈 请在左侧上传检测数据文件（支持 .xlsx / .csv）")
    st.stop()

# ============ 列名校验 ============
REQUIRED_COLS = ["日期", "产品型号", "硬度值"]

missing_cols = [col for col in REQUIRED_COLS if col not in df.columns]
if missing_cols:
    st.error(f"❌ 文件缺少必要列：{', '.join(missing_cols)}")
    st.write(f"当前文件列名：{list(df.columns)}")
    st.stop()

# ============ 数据类型转换 ============
df["日期"] = pd.to_datetime(df["日期"], errors="coerce")
df["硬度值"] = pd.to_numeric(df["硬度值"], errors="coerce")

# 删除日期或硬度值为空的行
df.dropna(subset=["日期", "硬度值"], inplace=True)
df.sort_values("日期", inplace=True)
df.reset_index(drop=True, inplace=True)

# ============ 自动判定逻辑 ============
HARDNESS_LOWER = 58.0
HARDNESS_UPPER = 62.0

if "判定结果" not in df.columns:
    df["判定结果"] = df["硬度值"].apply(
        lambda x: "合格" if HARDNESS_LOWER <= x <= HARDNESS_UPPER
        else ("硬度偏低" if x < HARDNESS_LOWER else "硬度偏高")
    )
    st.sidebar.info("ℹ️ 未检测到「判定结果」列，已按 58~62 HRC 自动判定")
else:
    df["判定结果"] = df["判定结果"].astype(str).str.strip()

# ============ 指标卡片 ============
st.subheader("📈 核心指标")

total = len(df)
qualified = df[df["判定结果"] == "合格"]
qualified_count = len(qualified)
qualified_rate = qualified_count / total * 100 if total > 0 else 0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("检测总数", f"{total} 件")
with col2:
    st.metric("合格数量", f"{qualified_count} 件")
with col3:
    st.metric("合格率", f"{qualified_rate:.1f}%")
with col4:
    st.metric("硬度均值", f"{df['硬度值'].mean():.1f} HRC")

st.markdown("---")

# ============ 图表区域 ============
col_left, col_right = st.columns(2)

# --- 图1：硬度趋势折线图 ---
with col_left:
    st.subheader("📉 硬度趋势")
    fig_trend = px.line(
        df,
        x="日期",
        y="硬度值",
        color="产品型号",
        markers=True,
        labels={"日期": "日期", "硬度值": "硬度值 (HRC)", "产品型号": "产品型号"},
    )
    fig_trend.add_hline(y=HARDNESS_UPPER, line_dash="dash", line_color="red",
                        annotation_text=f"上限 {HARDNESS_UPPER}")
    fig_trend.add_hline(y=HARDNESS_LOWER, line_dash="dash", line_color="blue",
                        annotation_text=f"下限 {HARDNESS_LOWER}")
    fig_trend.update_layout(height=350, margin=dict(t=30, b=30))
    st.plotly_chart(fig_trend, use_container_width=True)

# --- 图2：判定结果饼图 ---
with col_right:
    st.subheader("🥧 判定结果分布")
    judge_counts = df["判定结果"].value_counts().reset_index()
    judge_counts.columns = ["判定结果", "数量"]

    color_map = {"合格": "#2ecc71", "硬度偏低": "#3498db", "硬度偏高": "#e74c3c"}
    fig_pie = px.pie(
        judge_counts,
        names="判定结果",
        values="数量",
        color="判定结果",
        color_discrete_map=color_map,
        hole=0.4,
    )
    fig_pie.update_layout(height=350, margin=dict(t=30, b=30))
    st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")

# --- 图3：按产品型号统计 ---
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("🏭 各型号合格率")
    model_stats = df.groupby("产品型号").apply(
        lambda g: pd.Series({
            "总数": len(g),
            "合格数": len(g[g["判定结果"] == "合格"]),
        })
    ).reset_index()
    model_stats["合格率(%)"] = (model_stats["合格数"] / model_stats["总数"] * 100).round(1)

    fig_bar = px.bar(
        model_stats,
        x="产品型号",
        y="合格率(%)",
        text="合格率(%)",
        color="产品型号",
        labels={"产品型号": "产品型号", "合格率(%)": "合格率 (%)"},
    )
    fig_bar.update_layout(height=320, showlegend=False, margin=dict(t=30, b=30))
    fig_bar.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    st.plotly_chart(fig_bar, use_container_width=True)

with col_b:
    st.subheader("📦 各型号硬度分布")
    fig_box = px.box(
        df,
        x="产品型号",
        y="硬度值",
        color="产品型号",
        labels={"产品型号": "产品型号", "硬度值": "硬度值 (HRC)"},
    )
    fig_box.update_layout(height=320, showlegend=False, margin=dict(t=30, b=30))
    st.plotly_chart(fig_box, use_container_width=True)

st.markdown("---")

# ============ 数据明细表 ============
with st.expander("📋 查看原始数据明细", expanded=False):
    st.dataframe(df, use_container_width=True, height=400)

# ============ 页脚 ============
st.markdown("---")
st.caption("质量数据看板 v1.0 | 判定标准：硬度 58~62 HRC 为合格")