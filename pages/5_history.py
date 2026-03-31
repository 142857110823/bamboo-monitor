"""
历史记录查询页
展示数据库中的历史分析记录和预警日志
"""
import os
import sys
import streamlit as st
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.config import APP_TITLE, PAGE_ICON, USE_MOCK_DATA
from core.database import init_db, get_analysis_history, get_alerts
from core.mock_generator import generate_mock_dashboard_data

# ============ 页面配置 ============
st.set_page_config(page_title=f"历史记录 - {APP_TITLE}", page_icon=PAGE_ICON, layout="wide")

css_path = os.path.join(os.path.dirname(__file__), "..", "assets", "custom.css")
if os.path.exists(css_path):
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

init_db()

# ============ 页面标题 ============
st.title("历史记录")
st.markdown("查看历史分析记录和预警日志")
st.markdown("---")

# ============ 选项卡 ============
tab_records, tab_alerts = st.tabs(["分析记录", "预警日志"])

# ============ 分析记录 ============
with tab_records:
    st.subheader("历史分析记录")

    # 从数据库获取数据
    records = get_analysis_history(limit=50)

    # 如果数据库为空且处于演示模式，使用 mock 数据
    if not records and USE_MOCK_DATA:
        st.caption("数据库中暂无记录，展示模拟历史数据")
        mock_data = generate_mock_dashboard_data()
        records = mock_data["history_records"]

    if records:
        # 汇总统计
        total_records = len(records)
        success_count = sum(1 for r in records if r.get("status") == "success")

        cols = st.columns(3)
        cols[0].metric("总分析次数", total_records)
        cols[1].metric("成功次数", success_count)
        cols[2].metric("成功率", f"{success_count / total_records * 100:.0f}%" if total_records > 0 else "N/A")

        st.markdown("---")

        # 数据表格
        display_cols = {
            "created_at": "分析时间",
            "filename": "文件名",
            "file_size_mb": "文件大小(MB)",
            "image_width": "宽度",
            "image_height": "高度",
            "bamboo_area_ha": "竹林面积(公顷)",
            "coverage_pct": "覆盖度(%)",
            "processing_time_s": "耗时(秒)",
            "status": "状态",
            "model_version": "模型版本",
        }

        df = pd.DataFrame(records)
        # 只展示存在的列
        available_cols = [c for c in display_cols.keys() if c in df.columns]
        df_display = df[available_cols].copy()
        df_display.columns = [display_cols[c] for c in available_cols]

        # 格式化分析时间显示
        if "分析时间" in df_display.columns:
            df_display["分析时间"] = df_display["分析时间"].apply(lambda x: str(x)[:19] if x else "")

        st.dataframe(
            df_display,
            width="stretch",
            hide_index=True,
        )

        # 详情查看
        st.markdown("---")
        st.subheader("记录详情")
        selected_idx = st.selectbox(
            "选择一条记录查看详情",
            range(len(records)),
            format_func=lambda i: f"{str(records[i].get('created_at', ''))[:19]} - {records[i].get('filename', '未知')}",
        )

        if selected_idx is not None:
            record = records[selected_idx]
            detail_cols = st.columns(3)

            detail_cols[0].markdown(f"""
            **基本信息**
            - 文件: {record.get('filename', '未知')}
            - 大小: {record.get('file_size_mb', 0)} MB
            - 尺寸: {record.get('image_width', 0)} x {record.get('image_height', 0)}
            - 坐标系: {record.get('crs_original', '未知')}
            """)

            detail_cols[1].markdown(f"""
            **分析结果**
            - 竹林面积: {record.get('bamboo_area_ha', 0)} 公顷
            - 覆盖度: {record.get('coverage_pct', 0)}%
            - 竹林像素: {record.get('bamboo_pixels', 0):,}
            - 总像素: {record.get('total_pixels', 0):,}
            """)

            detail_cols[2].markdown(f"""
            **处理信息**
            - 模型版本: {record.get('model_version', '未知')}
            - 处理耗时: {record.get('processing_time_s', 0)} 秒
            - 状态: {record.get('status', '未知')}
            - 时间: {str(record.get('created_at', ''))[:19]}
            """)
    else:
        st.info("暂无分析记录。完成影像分析后，记录将自动保存到数据库中。")

# ============ 预警日志 ============
with tab_alerts:
    st.subheader("预警日志")

    alert_logs = get_alerts(limit=50)

    if not alert_logs and USE_MOCK_DATA:
        st.caption("数据库中暂无预警记录，展示模拟预警数据")
        mock_data = generate_mock_dashboard_data()
        alert_logs = mock_data["recent_alerts"]

    if alert_logs:
        severity_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}

        # 汇总
        high_count = sum(1 for a in alert_logs if a.get("severity") == "high")
        medium_count = sum(1 for a in alert_logs if a.get("severity") == "medium")

        cols = st.columns(3)
        cols[0].metric("总预警数", len(alert_logs))
        cols[1].metric("高风险", high_count)
        cols[2].metric("中风险", medium_count)

        st.markdown("---")

        # 预警表格
        alert_df = pd.DataFrame(alert_logs)
        display_cols = {
            "created_at": "时间",
            "alert_type": "类型",
            "severity": "严重程度",
            "location_desc": "位置",
            "affected_area_ha": "影响面积(公顷)",
            "confidence": "置信度",
            "suggested_action": "建议操作",
        }

        available_cols = [c for c in display_cols.keys() if c in alert_df.columns]
        df_display = alert_df[available_cols].copy()
        df_display.columns = [display_cols[c] for c in available_cols]

        if "时间" in df_display.columns:
            df_display["时间"] = df_display["时间"].apply(lambda x: str(x)[:19] if x else "")

        if "类型" in df_display.columns:
            type_map = {"degradation": "退化", "low_coverage": "低覆盖", "fragmentation": "碎片化"}
            df_display["类型"] = df_display["类型"].map(type_map).fillna(df_display["类型"])

        if "严重程度" in df_display.columns:
            sev_map = {"high": "高", "medium": "中", "low": "低"}
            df_display["严重程度"] = df_display["严重程度"].map(sev_map).fillna(df_display["严重程度"])

        st.dataframe(df_display, width="stretch", hide_index=True)
    else:
        st.info("暂无预警日志。完成影像分析后，系统会自动生成预警信息。")

# ============ 熊猫小助手悬浮组件 ============
from components.panda_chat import render_panda_assistant
render_panda_assistant()
