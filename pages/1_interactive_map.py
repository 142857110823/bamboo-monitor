"""
交互式地图页
展示竹林分类结果的栅格叠加、保护区标记、预警标注
"""
import os
import sys
import streamlit as st
import folium
from streamlit_folium import st_folium

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.config import (
    APP_TITLE, PAGE_ICON,
    WANGLANG_CENTER_LAT, WANGLANG_CENTER_LON,
)
from core.map_renderer import (
    create_base_map, add_protection_area_marker,
    add_prediction_overlay, add_alert_markers,
    build_analysis_map,
)

# ============ 页面配置 ============
st.set_page_config(page_title=f"交互式地图 - {APP_TITLE}", page_icon=PAGE_ICON, layout="wide")

css_path = os.path.join(os.path.dirname(__file__), "..", "assets", "custom.css")
if os.path.exists(css_path):
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ============ 页面标题 ============
st.title("交互式地图")
st.markdown("竹林分类结果空间可视化 | 支持图层控制和区域查看")
st.markdown("---")

# ============ 侧边栏图层控制 ============
with st.sidebar:
    st.subheader("图层控制")
    show_bamboo = st.checkbox("竹林分类结果", value=True)
    show_markers = st.checkbox("保护区标记", value=True)
    show_alerts = st.checkbox("预警标注", value=True)
    st.markdown("---")
    st.subheader("地图设置")
    opacity = st.slider("竹林图层透明度", 0.0, 1.0, 0.7, 0.05)
    map_tile = st.selectbox("底图样式", [
        "OpenStreetMap",
        "CartoDB positron",
        "CartoDB dark_matter",
    ])

# ============ 获取分析结果 ============
has_analysis = st.session_state.get("analysis_complete", False)
prediction_map = st.session_state.get("prediction_map")
bounds_wgs84 = st.session_state.get("geo_bounds_wgs84")
analysis_meta = st.session_state.get("analysis_meta", {})

# 如果没有分析结果，显示提示信息
if not has_analysis:
    st.warning("尚未完成影像分析，地图仅展示保护区基础位置。请前往「数据上传与分析」页面上传影像数据并完成分析。")

# ============ 构建地图 ============
if has_analysis and prediction_map is not None and bounds_wgs84 is not None:
    # 统计信息条
    stat_cols = st.columns(3)
    bamboo_pixels = int((prediction_map == 1).sum())
    total_pixels = int(prediction_map.size)
    coverage = bamboo_pixels / total_pixels * 100 if total_pixels > 0 else 0

    stat_cols[0].metric("竹林面积", f"{analysis_meta.get('bamboo_area_ha', bamboo_pixels * 0.01):,.2f} 公顷")
    stat_cols[1].metric("竹林覆盖度", f"{analysis_meta.get('coverage_pct', coverage):.1f}%")
    stat_cols[2].metric("影像尺寸", f"{prediction_map.shape[1]} x {prediction_map.shape[0]} 像素")

    st.markdown("---")

    # 构建地图
    west, south, east, north = bounds_wgs84
    center_lat = (south + north) / 2
    center_lon = (west + east) / 2

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles=map_tile,
        control_scale=True,
    )

    # 添加竹林分类图层
    if show_bamboo:
        m = add_prediction_overlay(m, prediction_map, bounds_wgs84)

    # 添加保护区标记
    if show_markers:
        m = add_protection_area_marker(m, center_lat, center_lon)

    # 添加预警标注
    if show_alerts:
        alerts = st.session_state.get("alerts_list", [])
        if alerts:
            m = add_alert_markers(m, alerts)

    # 图层控制面板
    folium.LayerControl().add_to(m)

    # 渲染地图
    st_folium(m, width=None, height=600, returned_objects=[])

    # 图例说明
    st.markdown("---")
    legend_cols = st.columns(4)
    legend_cols[0].markdown("🟩 **绿色区域** = 竹林分布")
    legend_cols[1].markdown("📍 **绿色标记** = 保护区中心")
    legend_cols[2].markdown("🔴 **红色标记** = 高风险预警")
    legend_cols[3].markdown("🟡 **橙色标记** = 中等风险预警")

else:
    # 无分析结果时展示基础地图
    st.warning("尚未完成影像分析，地图仅展示保护区基础位置。请前往「数据上传与分析」页面进行操作。")

    m = create_base_map()
    m = add_protection_area_marker(m)
    folium.LayerControl().add_to(m)

    st_folium(m, width=None, height=500, returned_objects=[])

# ============ 熊猫小助手悬浮组件 ============
from components.panda_chat import render_panda_assistant
render_panda_assistant()
