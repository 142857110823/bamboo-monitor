"""
数据导出页
支持分类结果TIF、统计CSV/Excel、分析报告的下载
"""
import os
import sys
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.config import APP_TITLE, PAGE_ICON, USE_MOCK_DATA
from core.export_engine import (
    export_prediction_tif,
    export_prediction_jpg,
    export_statistics_csv,
    export_statistics_excel,
    generate_report_text,
)
from core.mock_generator import generate_mock_prediction, generate_mock_tif_data, generate_mock_dashboard_data
from core.geo_processor import compute_statistics

# ============ 页面配置 ============
st.set_page_config(page_title=f"数据导出 - {APP_TITLE}", page_icon=PAGE_ICON, layout="wide")

css_path = os.path.join(os.path.dirname(__file__), "..", "assets", "custom.css")
if os.path.exists(css_path):
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ============ 页面标题 ============
st.title("数据导出")
st.markdown("下载分类结果、统计数据和分析报告")
st.markdown("---")

# ============ 获取当前分析结果 ============
has_analysis = st.session_state.get("analysis_complete", False)
prediction_map = st.session_state.get("prediction_map")
analysis_meta = st.session_state.get("analysis_meta", {})
alerts_list = st.session_state.get("alerts_list", [])

# 演示模式下自动生成数据
if not has_analysis and USE_MOCK_DATA:
    st.info("尚未上传真实数据，使用模拟数据进行导出演示。")
    img_data, meta = generate_mock_tif_data()
    prediction_map, _ = generate_mock_prediction(img_data)
    pixel_area_ha = meta.get("pixel_area_ha", 0.01)
    stats = compute_statistics(prediction_map, pixel_area_ha)
    analysis_meta = {**meta, **stats}
    has_analysis = True
    mock_data = generate_mock_dashboard_data()
    alerts_list = mock_data["recent_alerts"]

if not has_analysis or prediction_map is None:
    st.warning("尚未完成影像分析，无法导出数据。请先在「数据上传与分析」页面进行操作。")
    st.stop()

# 统计概览
stat_cols = st.columns(3)
stat_cols[0].metric("竹林面积", f"{analysis_meta.get('bamboo_area_ha', 0):,.2f} 公顷")
stat_cols[1].metric("竹林覆盖度", f"{analysis_meta.get('coverage_pct', 0):.1f}%")
stat_cols[2].metric("预警数量", f"{len(alerts_list)} 条")

st.markdown("---")

# ============ 导出选项 ============
st.subheader("选择导出格式")

export_cols = st.columns(2)

# 左列：文件导出
with export_cols[0]:
    st.markdown("#### 空间数据导出")

    # 分类结果 TIF
    st.markdown("**竹林分类结果 (GeoTIFF)**")
    st.caption("包含地理坐标信息的分类结果栅格文件，可导入QGIS进行进一步分析和美化制图")

    if st.button("生成TIF文件", key="gen_tif"):
        with st.spinner("正在生成GeoTIFF文件..."):
            tif_bytes = export_prediction_tif(prediction_map, analysis_meta)
            st.session_state["export_tif"] = tif_bytes

    if "export_tif" in st.session_state:
        st.download_button(
            label="下载分类结果 (.tif)",
            data=st.session_state["export_tif"],
            file_name="Wanglang_Bamboo_Classification.tif",
            mime="image/tiff",
        )

    st.markdown("")

    # 分类结果 JPG
    st.markdown("**竹林分类结果 (JPG 图片)**")
    st.caption("适合直接用于报告插图和演示文稿")

    if st.button("生成JPG图片", key="gen_jpg"):
        with st.spinner("正在生成JPG图片..."):
            jpg_bytes = export_prediction_jpg(prediction_map, analysis_meta)
            st.session_state["export_jpg"] = jpg_bytes

    if "export_jpg" in st.session_state:
        st.download_button(
            label="下载分类结果 (.jpg)",
            data=st.session_state["export_jpg"],
            file_name="Wanglang_Bamboo_Classification.jpg",
            mime="image/jpeg",
        )

    st.markdown("---")

    # 统计 CSV
    st.markdown("#### 统计数据导出")

    st.markdown("**统计报表 (CSV)**")
    csv_data = export_statistics_csv(analysis_meta, analysis_meta, alerts_list)
    st.download_button(
        label="下载统计数据 (.csv)",
        data=csv_data.encode("utf-8-sig"),
        file_name="Wanglang_Bamboo_Statistics.csv",
        mime="text/csv",
    )

    st.markdown("**统计报表 (Excel)**")
    if st.button("生成Excel文件", key="gen_xlsx"):
        with st.spinner("正在生成Excel文件..."):
            xlsx_bytes = export_statistics_excel(analysis_meta, analysis_meta, alerts_list)
            st.session_state["export_xlsx"] = xlsx_bytes

    if "export_xlsx" in st.session_state:
        st.download_button(
            label="下载统计数据 (.xlsx)",
            data=st.session_state["export_xlsx"],
            file_name="Wanglang_Bamboo_Statistics.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# 右列：报告导出
with export_cols[1]:
    st.markdown("#### 分析报告")

    st.markdown("**监测分析报告 (TXT)**")
    st.caption("包含影像信息、分析结果、决策建议和预警信息的完整报告")

    report_text = generate_report_text(analysis_meta, analysis_meta, alerts_list)

    # 预览报告
    with st.expander("预览报告内容", expanded=False):
        st.text(report_text)

    st.download_button(
        label="下载分析报告 (.txt)",
        data=report_text.encode("utf-8"),
        file_name="Wanglang_Bamboo_Report.txt",
        mime="text/plain",
    )

    st.markdown("---")
    st.markdown("#### 导出说明")
    st.markdown("""
    - **GeoTIFF**: 可直接导入 QGIS 进行专题地图制作（添加图例、指北针、比例尺等）
    - **CSV/Excel**: 可用于数据统计分析和报告撰写
    - **TXT报告**: 可直接用于监测报告附件
    - 所有文件均包含分析时间和模型版本信息，便于追溯
    """)

# ============ 熊猫小助手悬浮组件 ============
from components.panda_chat import render_panda_assistant
render_panda_assistant()
