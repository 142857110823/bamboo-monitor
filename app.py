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
    APP_TITLE, PAGE_ICON, USE_MOCK_DATA,
    WANGLANG_CENTER_LAT, WANGLANG_CENTER_LON, DEFAULT_ZOOM,
)
from core.database import init_db, get_dashboard_stats, get_yearly_bamboo_area
from core.mock_generator import generate_mock_dashboard_data
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

    if USE_MOCK_DATA:
        st.info("当前运行模式：演示模式（模拟数据）")
    else:
        st.success("当前运行模式：生产模式")

    st.markdown("---")
    st.caption("大熊猫主食竹智能监测系统 v1.0")

# ============ 页面标题 ============
st.title("大熊猫主食竹智能监测与决策支持系统")
st.markdown("基于遥感影像与随机森林模型的竹林资源智能监测平台 | 王朗自然保护区")
st.markdown("---")

# ============ 加载数据 ============
# 获取数据库中真实存在的年份数据
yearly_data = get_yearly_bamboo_area()
has_real_trend_data = len(yearly_data) >= 2  # 至少需要2年数据才能显示趋势

if USE_MOCK_DATA and not has_real_trend_data:
    # 只有在没有真实数据时才使用模拟数据
    dashboard_data = generate_mock_dashboard_data()
    kpi = dashboard_data["kpi"]
    trend_data = dashboard_data["trend_data"]
    recent_alerts = dashboard_data["recent_alerts"]
    heatmap_points = dashboard_data["heatmap_points"]
    trend_data_source = "模拟数据"
else:
    db_stats = get_dashboard_stats()
    latest_record = db_stats["latest_record"]
    
    # 使用最新的真实数据作为KPI
    if latest_record:
        current_area = latest_record.get("bamboo_area_ha", 0)
        # 计算变化率（如果有至少2年的数据）
        if len(yearly_data) >= 2:
            prev_area = yearly_data[-2]["area_ha"]
            change_rate = ((current_area - prev_area) / prev_area * 100) if prev_area > 0 else 0
        else:
            change_rate = 0
    else:
        current_area = 0
        change_rate = 0
    
    kpi = {
        "total_area_ha": current_area,
        "change_rate_pct": round(change_rate, 1),
        "connectivity_index": 0,
        "health_score": 0,
    }
    
    # 将真实数据转换为DataFrame格式
    if yearly_data:
        trend_data = pd.DataFrame(yearly_data)
        trend_data_source = "真实监测数据"
    else:
        trend_data = None
        trend_data_source = "无数据"
    
    # 预警和热力图数据
    from core.database import get_alerts
    recent_alerts = get_alerts(limit=5)
    heatmap_points = []

# ============ KPI 指标卡片 ============
st.subheader("核心监测指标")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="竹林总面积",
        value=f"{kpi['total_area_ha']:,.0f} 公顷",
        delta=f"{kpi['change_rate_pct']:+.1f}%",
        delta_color="normal",
    )

with col2:
    # 预警数量
    alert_count = len(recent_alerts)
    st.metric(
        label="活跃预警",
        value=f"{alert_count} 处",
        delta=f"发现 {sum(1 for a in recent_alerts if a.get('severity') == 'high')} 处高风险",
        delta_color="inverse",
    )

with col3:
    st.metric(
        label="连通性指数",
        value=f"{kpi['connectivity_index']:.2f}",
        delta="良好" if kpi['connectivity_index'] > 0.7 else "需关注",
        delta_color="normal" if kpi['connectivity_index'] > 0.7 else "inverse",
    )

with col4:
    st.metric(
        label="健康度评分",
        value=f"{kpi['health_score']} 分",
        delta="优良" if kpi['health_score'] >= 80 else "一般",
        delta_color="normal" if kpi['health_score'] >= 80 else "inverse",
    )

st.markdown("---")

# ============ 趋势图 + 地图概览 双列布局 ============
left_col, right_col = st.columns([1.2, 1])

with left_col:
    st.subheader("竹林面积变化趋势")
    
    # 显示数据来源说明
    if trend_data_source == "真实监测数据":
        st.caption(f"📊 数据来源：{trend_data_source} ({len(yearly_data)}年)")
    elif trend_data_source == "模拟数据":
        st.caption("📊 数据来源：模拟演示数据")
    else:
        st.caption("📊 数据来源：暂无数据")

    if trend_data is not None and not trend_data.empty:
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=trend_data["year"],
            y=trend_data["area_ha"],
            mode="lines+markers",
            name="竹林面积",
            line=dict(color="#2E7D32", width=3),
            marker=dict(size=10, color="#2E7D32", line=dict(width=2, color="#FFFFFF")),
            fill="tozeroy",
            fillcolor="rgba(46, 125, 50, 0.1)",
            hovertemplate="<b>%{x}年</b><br>竹林面积: %{y:,.0f} 公顷<extra></extra>",
        ))

        # 根据实际数据范围设置X轴
        x_min = min(trend_data["year"])
        x_max = max(trend_data["year"])
        
        fig.update_layout(
            xaxis_title="年份",
            yaxis_title="面积（公顷）",
            template="plotly_white",
            height=400,
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(
                dtick=1, 
                gridcolor="#E8F5E9",
                range=[x_min - 0.5, x_max + 0.5]  # 根据实际数据范围设置
            ),
            yaxis=dict(gridcolor="#E8F5E9", range=[
                min(trend_data["area_ha"]) * 0.95,
                max(trend_data["area_ha"]) * 1.05
            ]),
            font=dict(family="Microsoft YaHei, sans-serif"),
            hovermode="x unified",
        )

        st.plotly_chart(fig, width="stretch")
        
        # 显示数据表格
        with st.expander("查看详细数据"):
            # 检查record_count列是否存在
            display_columns = ["year", "area_ha"]
            column_names = {"year": "年份", "area_ha": "竹林面积 (公顷)"}
            
            if "record_count" in trend_data.columns:
                display_columns.append("record_count")
                column_names["record_count"] = "分析次数"
            
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

    本系统由四川大学创新实践团队开发，旨在利用遥感技术与机器学习方法，
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

    #### 团队成员
    | 姓名 | 职责 |
    |------|------|
    | 团队成员 | 遥感数据处理与 GEE 脚本开发 |
    | 团队成员 | 机器学习模型训练与验证 |
    | 团队成员 | Web 系统开发与部署 |
    | 团队成员 | 野外调查与数据验证 |

    #### 致谢
    感谢王朗自然保护区管理局提供的支持，感谢中科院成都生物研究所的技术指导。

    ---
    *大熊猫主食竹智能监测系统 v1.0 | 2024-2025*
    """)
