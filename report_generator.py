"""一键报告生成模块 v3.0"""
from datetime import datetime
from config import REPORT_COMPANY, REPORT_DEPARTMENT, REPORT_TITLE


def generate_text_report(df, spc_result: dict, cap_result: dict,
                         usl: float, lsl: float,
                         violations: dict, dq_report: dict) -> str:
    """生成纯文本报告，支持页面显示 + 复制 + 下载"""

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(df)
    qualified = int((df["判定结果"] == "合格").sum()) if "判定结果" in df.columns else 0
    rate = qualified / total * 100 if total > 0 else 0
    mean_val = df["硬度值"].mean()
    std_val = df["硬度值"].std()

    # SPC 摘要
    spc_lines = []
    if spc_result:
        spc_lines.append(f"  X̄̄ = {spc_result.get('xbar_bar', 'N/A'):.3f}")
        spc_lines.append(f"  R̄  = {spc_result.get('r_bar', 'N/A'):.3f}")
        spc_lines.append(f"  X̄ UCL = {spc_result.get('xbar_ucl', 'N/A'):.3f}")
        spc_lines.append(f"  X̄ LCL = {spc_result.get('xbar_lcl', 'N/A'):.3f}")
        spc_lines.append(f"  σ̂     = {spc_result.get('sigma_est', 'N/A'):.3f}")
    else:
        spc_lines.append("  数据不足，未生成控制图")

    # 判异摘要
    viol_lines = []
    has_viol = False
    for rule, indices in violations.items():
        if indices:
            has_viol = True
            viol_lines.append(f"  - {rule}: 子组 {[i+1 for i in indices]}")
    if not has_viol:
        viol_lines.append("  ✅ 无异常，过程受控")

    # CPK 摘要
    cpk = cap_result.get("Cpk", "N/A") if cap_result else "N/A"
    ppk = cap_result.get("Ppk", "N/A") if cap_result else "N/A"
    cp = cap_result.get("Cp", "N/A") if cap_result else "N/A"
    cpk_str = f"{cpk:.3f}" if isinstance(cpk, float) else str(cpk)
    ppk_str = f"{ppk:.3f}" if isinstance(ppk, float) else str(ppk)
    cp_str = f"{cp:.3f}" if isinstance(cp, float) else str(cp)

    # 结论
    conclusion = "✅ 过程能力充足，建议维持当前工艺参数。"
    if isinstance(cpk, float):
        if cpk < 1.0:
            conclusion = "❌ 过程能力严重不足，需立即排查原因并采取纠正措施。"
        elif cpk < 1.33:
            conclusion = "⚠️ 过程能力不足，建议优化工艺或加强检验频次。"

    report = f"""{'='*60}
{REPORT_TITLE}
{REPORT_COMPANY} · {REPORT_DEPARTMENT}
生成时间：{now_str}
{'='*60}

【一、基本统计】
  检测总数：{total} 件
  合格数量：{qualified} 件
  合 格 率：{rate:.1f}%
  硬度均值：{mean_val:.2f} HRC
  标 准 差：{std_val:.2f} HRC
  规格范围：{lsl} ~ {usl} HRC

【二、数据质量概览】
  缺失率：{dq_report.get('missing_rate', 0):.1%}
  重复记录：{dq_report.get('duplicate_count', 0)} 条
  异常值：{dq_report.get('outlier_count', 0)} 个
  时间断档：{len(dq_report.get('time_gaps', []))} 处
{"  ".join(dq_report.get("warnings", [])) or "  ✅ 数据质量良好"}

【三、SPC 控制图分析】
{chr(10).join(spc_lines)}

  判异结果：
{chr(10).join(viol_lines)}

【四、过程能力分析】
  Cp  = {cp_str}
  Cpk = {cpk_str}
  Ppk = {ppk_str}

【五、综合结论】
  {conclusion}

{'='*60}
本报告由质量数据看板 v3.0 自动生成
{'='*60}"""
    return report