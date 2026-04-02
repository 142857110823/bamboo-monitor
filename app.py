"""
大熊猫主食竹智能监测与决策支持系统 - 驾驶舱首页
KPI指标卡片 + 趋势折线图 + 地图概览 + 最近预警
"""
import os
import sys
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(__file__))

from core.config import (
    APP_TITLE, PAGE_ICON,
    WANGLANG_CENTER_LAT, WANGLANG_CENTER_LON, DEFAULT_ZOOM,
)
from core.database import init_db, get_dashboard_stats, get_yearly_bamboo_area
from core.authoritative_data import WANG_LANG_DATA, YEARLY_TREND_DATA, alerts_data
import pandas as pd


# ============ 页面配置 ============
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# 注入自定义CSS
css_path = os.path.join(os.path.dirname(__file__), "assets", "custom.css")
if os.path.exists(css_path):
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ============ 初始化数据库 ============
init_db()

# ============ 侧边栏 ============
with st.sidebar:
    st.image("https://img.icons8.com/emoji/96/panda-emoji.png", width=80)
    st.title("导航菜单")
    st.markdown("---")
    st.markdown("**系统状态**")
    st.success("当前运行模式：生产模式")

    st.markdown("---")
    st.caption("大熊猫主食竹智能监测系统 v1.0")

# ============ 页面标题 ============
st.title("大熊猫主食竹智能监测与决策支持系统")
st.markdown("基于遥感影像与随机森林模型的竹林资源智能监测平台 | 王朗自然保护区")
st.markdown("---")

# ============ 加载数据 ============
# 使用权威数据（基于中国科学院成都山地所等机构的研究）

# 核心KPI指标
kpi = {
    "reserve_area_km2": WANG_LANG_DATA["kpi_baseline"]["reserve_area_km2"],
    "bamboo_monitoring_accuracy": WANG_LANG_DATA["kpi_baseline"]["bamboo_monitoring_accuracy"],
    "bamboo_coverage_ratio": WANG_LANG_DATA["kpi_baseline"]["bamboo_coverage_ratio"],
    "bamboo_elevation_range": WANG_LANG_DATA["kpi_baseline"]["bamboo_elevation_range"],
}

# 年度趋势数据
trend_data = pd.DataFrame(YEARLY_TREND_DATA)
trend_data_source = "四川王朗国家级自然保护区近 7 年（2019-2025）大熊猫主食竹面积完整合规数据集"

# 预警数据
recent_alerts = alerts_data
heatmap_points = []

# ============ KPI 指标卡片 ============
st.subheader("核心监测指标")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="保护区面积",
        value=f"{kpi['reserve_area_km2']} 平方公里",
        delta="王朗自然保护区",
        delta_color="normal",
    )

with col2:
    st.metric(
        label="监测精度",
        value=f"{kpi['bamboo_monitoring_accuracy']}%",
        delta="基于中科院2026年研究",
        delta_color="normal",
    )

with col3:
    st.metric(
        label="竹林占比",
        value=f"{kpi['bamboo_coverage_ratio']}%",
        delta="岷山山系平均水平",
        delta_color="normal",
    )

with col4:
    st.metric(
        label="海拔分布",
        value=kpi['bamboo_elevation_range'],
        delta="缺苞箭竹主要分布",
        delta_color="normal",
    )

st.markdown("---")

# ============ 趋势图 + 地图概览 双列布局 ============
left_col, right_col = st.columns([1.2, 1])

with left_col:
    st.subheader("竹林面积变化趋势")
    
    # 显示数据来源说明
    if trend_data_source == "权威研究数据（2020-2026）":
        st.caption(f"📊 数据来源：{trend_data_source}")
        st.caption("🔬 权威来源：中国科学院成都山地所、四川农业大学")
    elif trend_data_source == "真实监测数据":
        st.caption(f"📊 数据来源：{trend_data_source}")
    elif trend_data_source == "模拟数据":
        st.caption("📊 数据来源：模拟演示数据")
    else:
        st.caption("📊 数据来源：暂无数据")

    if trend_data is not None and not trend_data.empty:
        fig = go.Figure()

        # 分离数据点：2019-2024年为实测/推演值，2025年为预测值
        actual_data = trend_data[trend_data["year"] <= 2024]
        forecast_data = trend_data[trend_data["year"] == 2025]

        # 添加实测/推演值折线
        fig.add_trace(go.Scatter(
            x=actual_data["year"],
            y=actual_data["area_km2"],
            mode="lines+markers+text",
            name="实测/推演值",
            line=dict(color="#2E7D32", width=1.5),  # 深绿色，线宽1.5pt
            marker=dict(size=8, color="#2E7D32", symbol="circle"),  # 实心圆形，大小8pt
            text=actual_data["area_km2"],
            textposition="top center",
            hovertemplate="<b>%{x}年</b><br>面积: %{y:.2f} km²<br>数据类型: %{customdata}<extra></extra>",
            customdata=actual_data["data_type"]
        ))

        # 添加预测值折线
        if not forecast_data.empty:
            fig.add_trace(go.Scatter(
                x=forecast_data["year"],
                y=forecast_data["area_km2"],
                mode="lines+markers+text",
                name="趋势预测值",
                line=dict(color="#2E7D32", width=1.5, dash="solid"),  # 深绿色，线宽1.5pt
                marker=dict(size=8, color="#2E7D32", symbol="circle-open"),  # 空心圆形，大小8pt
                text=forecast_data["area_km2"],
                textposition="top center",
                hovertemplate="<b>%{x}年</b><br>面积: %{y:.2f} km²<br>数据类型: %{customdata}<extra></extra>",
                customdata=forecast_data["data_type"]
            ))

        fig.update_layout(
            xaxis_title="年份",
            yaxis_title="面积（km²）",
            template="plotly_white",
            height=400,
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(
                dtick=1, 
                gridcolor="#E8F5E9",
                range=[2018.5, 2025.5],
                tickfont=dict(family="SimSun, Heiti, sans-serif", size=11)  # 宋体/黑体，10-12号
            ),
            yaxis=dict(
                gridcolor="#E8F5E9", 
                range=[90, 110],  # 刻度范围90-110 km²
                dtick=2,  # 刻度间隔2 km²
                tickfont=dict(family="SimSun, Heiti, sans-serif", size=11)  # 宋体/黑体，10-12号
            ),
            font=dict(family="Microsoft YaHei, sans-serif"),
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        st.plotly_chart(fig, width="stretch")
        
        # 显示数据表格
        with st.expander("查看详细数据"):
            display_columns = ["year", "area_km2", "data_type"]
            column_names = {
                "year": "年份", 
                "area_km2": "大熊猫主食竹分布面积（km²）",
                "data_type": "数据属性"
            }
            
            st.dataframe(trend_data[display_columns], 
                        column_config=column_names,
                        hide_index=True)
    else:
        st.info("暂无趋势数据，请先完成至少一次影像分析")

with right_col:
    st.subheader("竹林密度分布概览")

    m = folium.Map(
        location=[WANGLANG_CENTER_LAT, WANGLANG_CENTER_LON],
        zoom_start=DEFAULT_ZOOM,
        tiles="OpenStreetMap",
    )

    # 保护区中心标记
    folium.Marker(
        [WANGLANG_CENTER_LAT, WANGLANG_CENTER_LON],
        popup=folium.Popup("王朗自然保护区", max_width=200),
        tooltip="王朗保护区中心",
        icon=folium.Icon(color="green", icon="tree-conifer", prefix="glyphicon"),
    ).add_to(m)

    # 添加竹林密度热力图
    if heatmap_points:
        HeatMap(
            heatmap_points,
            radius=20,
            blur=15,
            gradient={0.2: "#ffffb2", 0.4: "#a1dab4", 0.6: "#41b6c4", 0.8: "#2c7fb8", 1.0: "#253494"},
            name="竹林密度热力图",
        ).add_to(m)
        folium.LayerControl().add_to(m)

    st_folium(m, width=None, height=400, returned_objects=[])

st.markdown("---")

# ============ 最近预警信息 ============
st.subheader("最近预警信息")

if recent_alerts:
    severity_colors = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    type_labels = {
        "degradation": "退化预警",
        "low_coverage": "低覆盖度",
        "fragmentation": "碎片化",
    }

    alert_cols = st.columns(min(len(recent_alerts), 3))

    for i, alert in enumerate(recent_alerts[:3]):
        with alert_cols[i]:
            severity_icon = severity_colors.get(alert["severity"], "⚪")
            type_label = type_labels.get(alert["alert_type"], alert["alert_type"])

            st.markdown(f"""
            **{severity_icon} {type_label}**

            - **位置**: {alert["location_desc"]}
            - **影响面积**: {alert["affected_area_ha"]} 公顷
            - **置信度**: {alert["confidence"]:.0%}
            - **建议**: {alert["suggested_action"]}
            """)
else:
    st.success("当前没有活跃预警")

st.markdown("---")

# ============ 系统使用指引 ============
with st.expander("系统使用指引", expanded=False):
    st.markdown("""
    ### 快速开始

    1. **数据上传与分析**: 在「数据上传与分析」页面上传GeoTIFF格式的双时相NDVI合成影像
    2. **查看分布图**: 分析完成后，前往「交互式地图」查看竹林分布的空间可视化结果
    3. **预警管理**: 在「预警与任务」页面查看系统自动识别的异常区域和巡护建议
    4. **数据导出**: 在「数据导出」页面下载分析结果和统计报表

    ### 数据要求

    - **文件格式**: GeoTIFF (.tif)
    - **波段要求**: 波段1=夏季NDVI，波段2=冬季NDVI
    - **数据来源**: GEE预处理生成的双时相NDVI合成影像
    - **坐标系**: UTM投影（系统会自动转换为WGS84用于地图展示）
    """)

# ============ 了解我们 ============
st.markdown("---")
with st.expander("了解我们", expanded=False):
    st.markdown("""
    ### 大熊猫主食竹智能监测与决策支持系统

    本系统由高校创新实践团队开发，旨在利用遥感技术与机器学习方法，
    对大熊猫国家公园王朗自然保护区内的主食竹资源进行智能监测与分析。

    #### 项目背景
    大熊猫是我国特有的珍稀濒危物种，竹子是其最主要的食物来源。
    准确掌握竹林资源的时空分布变化对于大熊猫栖息地保护具有重要意义。
    本系统结合 Google Earth Engine 遥感数据预处理和随机森林分类模型，
    实现了对竹林分布的自动化监测、预警和决策支持。

    #### 技术路线
    - **数据获取**: 基于 Google Earth Engine 平台获取 Sentinel-2 多时相遥感影像
    - **特征工程**: 提取双时相（夏季/冬季）NDVI 合成特征，利用竹林常绿特性进行区分
    - **模型推理**: 采用随机森林（Random Forest）分类器进行竹林/非竹林二分类
    - **可视化**: 基于 Streamlit + Folium 构建交互式 Web 地图展示平台
    - **决策支持**: 自动生成退化预警、碎片化检测和巡护任务建议

    ---
    *大熊猫主食竹智能监测系统 v1.0 | 2024-2025*
    """)

# ============ 熊猫小助手悬浮组件 ============
from components.panda_chat import render_panda_assistant
render_panda_assistant()
