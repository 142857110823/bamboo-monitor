"""
预警与任务管理页
展示预警清单、任务状态管理、巡护建议
"""
import os
import sys
import streamlit as st
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.config import APP_TITLE, PAGE_ICON, USE_MOCK_DATA
from core.database import init_db, get_alerts, get_tasks, save_task, update_task_status, save_alerts
from core.alert_engine import generate_alerts
from core.mock_generator import generate_mock_dashboard_data

# ============ 页面配置 ============
st.set_page_config(page_title=f"预警与任务 - {APP_TITLE}", page_icon=PAGE_ICON, layout="wide")

css_path = os.path.join(os.path.dirname(__file__), "..", "assets", "custom.css")
if os.path.exists(css_path):
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

init_db()

# ============ 页面标题 ============
st.title("预警中心与任务管理")
st.markdown("基于分类结果的异常区域自动识别、预警管理和巡护任务分派")
st.markdown("---")

# ============ 选项卡 ============
tab_alerts, tab_tasks = st.tabs(["预警清单", "任务管理"])

# ============ 预警清单 ============
with tab_alerts:
    # 尝试从分析结果生成预警
    has_analysis = st.session_state.get("analysis_complete", False)
    prediction_map = st.session_state.get("prediction_map")
    bounds_wgs84 = st.session_state.get("geo_bounds_wgs84")
    analysis_meta = st.session_state.get("analysis_meta", {})

    alerts = []

    if has_analysis and prediction_map is not None and bounds_wgs84 is not None:
        pixel_area_ha = analysis_meta.get("pixel_area_ha", 0.01)
        alerts = generate_alerts(prediction_map, bounds_wgs84, pixel_area_ha)
        st.session_state["alerts_list"] = alerts
    elif USE_MOCK_DATA:
        mock_data = generate_mock_dashboard_data()
        alerts = mock_data["recent_alerts"]

    # 也从数据库加载历史预警
    db_alerts = get_alerts(limit=20)
    if db_alerts:
        st.caption(f"数据库中共有 {len(db_alerts)} 条历史预警记录")

    if alerts:
        # 统计概览
        severity_counts = {"high": 0, "medium": 0, "low": 0}
        for a in alerts:
            sev = a.get("severity", "low")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        cols = st.columns(4)
        cols[0].metric("总预警数", len(alerts))
        cols[1].metric("高风险", severity_counts["high"], delta_color="inverse")
        cols[2].metric("中风险", severity_counts["medium"])
        cols[3].metric("低风险", severity_counts["low"])

        st.markdown("---")

        # 预警筛选
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            severity_filter = st.multiselect(
                "按严重程度筛选",
                ["high", "medium", "low"],
                default=["high", "medium", "low"],
                format_func=lambda x: {"high": "高风险", "medium": "中等风险", "low": "低风险"}.get(x, x),
            )
        with filter_col2:
            type_filter = st.multiselect(
                "按预警类型筛选",
                ["degradation", "low_coverage", "fragmentation"],
                default=["degradation", "low_coverage", "fragmentation"],
                format_func=lambda x: {
                    "degradation": "退化预警",
                    "low_coverage": "低覆盖度",
                    "fragmentation": "碎片化",
                }.get(x, x),
            )

        filtered_alerts = [
            a for a in alerts
            if a.get("severity") in severity_filter and a.get("alert_type") in type_filter
        ]

        # 展示预警详情
        severity_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        type_labels = {
            "degradation": "退化预警",
            "low_coverage": "低覆盖度",
            "fragmentation": "碎片化",
        }

        for i, alert in enumerate(filtered_alerts):
            icon = severity_icons.get(alert["severity"], "⚪")
            type_label = type_labels.get(alert["alert_type"], alert["alert_type"])

            with st.expander(
                f"{icon} {type_label} — {alert.get('location_desc', '未知位置')} "
                f"| 影响面积: {alert.get('affected_area_ha', 0)} 公顷",
                expanded=(alert["severity"] == "high")
            ):
                detail_cols = st.columns([1, 1, 1])
                detail_cols[0].markdown(f"**位置**: {alert.get('location_desc', '未知')}")
                detail_cols[1].markdown(f"**置信度**: {alert.get('confidence', 0):.0%}")
                detail_cols[2].markdown(f"**坐标**: ({alert.get('center_lat', 0):.4f}, {alert.get('center_lon', 0):.4f})")

                st.markdown(f"**建议操作**: {alert.get('suggested_action', '无')}")

                # 生成巡护任务按钮
                if st.button(f"生成巡护任务", key=f"task_btn_{i}"):
                    task = {
                        "alert_id": alert.get("id", ""),
                        "task_desc": f"巡护核查: {alert.get('location_desc', '')} - {type_label}",
                        "status": "pending",
                        "priority": "urgent" if alert["severity"] == "high" else "normal",
                        "notes": alert.get("suggested_action", ""),
                    }
                    save_task(task)
                    st.success("巡护任务已生成！请前往「任务管理」查看。")
    else:
        st.info("当前没有预警信息。请先在「数据上传与分析」页面完成影像分析。")

# ============ 任务管理 ============
with tab_tasks:
    st.subheader("巡护任务列表")

    # 任务状态筛选
    status_filter = st.selectbox(
        "筛选任务状态",
        ["all", "pending", "in_progress", "completed", "cancelled"],
        format_func=lambda x: {
            "all": "全部任务",
            "pending": "待处理",
            "in_progress": "进行中",
            "completed": "已完成",
            "cancelled": "已取消",
        }.get(x, x),
    )

    tasks = get_tasks(status=status_filter if status_filter != "all" else None, limit=50)

    if tasks:
        status_icons = {
            "pending": "⏳",
            "in_progress": "🔄",
            "completed": "✅",
            "cancelled": "❌",
        }
        priority_labels = {
            "urgent": "🔴 紧急",
            "normal": "🟡 普通",
            "low": "🟢 低优先级",
        }

        for i, task in enumerate(tasks):
            s_icon = status_icons.get(task.get("status", "pending"), "⏳")
            p_label = priority_labels.get(task.get("priority", "normal"), "普通")

            with st.expander(
                f"{s_icon} {task.get('task_desc', '未命名任务')} | {p_label}",
                expanded=(task.get("status") == "pending")
            ):
                info_cols = st.columns(3)
                info_cols[0].markdown(f"**创建时间**: {task.get('created_at', '未知')[:19]}")
                info_cols[1].markdown(f"**当前状态**: {task.get('status', 'pending')}")
                info_cols[2].markdown(f"**关联位置**: {task.get('location_desc', '未知')}")

                if task.get("notes"):
                    st.markdown(f"**备注**: {task['notes']}")

                # 状态更新操作
                action_cols = st.columns(4)
                task_id = task.get("id", "")

                if task.get("status") == "pending":
                    if action_cols[0].button("开始执行", key=f"start_{i}"):
                        update_task_status(task_id, "in_progress")
                        st.rerun()
                    if action_cols[1].button("取消任务", key=f"cancel_{i}"):
                        update_task_status(task_id, "cancelled")
                        st.rerun()

                elif task.get("status") == "in_progress":
                    if action_cols[0].button("标记完成", key=f"complete_{i}"):
                        update_task_status(task_id, "completed")
                        st.rerun()
                    if action_cols[1].button("取消任务", key=f"cancel2_{i}"):
                        update_task_status(task_id, "cancelled")
                        st.rerun()
    else:
        st.info("暂无巡护任务。在预警清单中点击「生成巡护任务」可创建新任务。")

# ============ 熊猫小助手悬浮组件 ============
from components.panda_chat import render_panda_assistant
render_panda_assistant()
