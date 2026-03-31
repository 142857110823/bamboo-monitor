"""
数据上传与分析页
TIF文件上传 → 模型推理流水线 → 统计指标 → 结果入库
是系统的数据生产者，其他页面依赖此页面生成的 session_state 数据
"""
import os
import sys
import json
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.config import APP_TITLE, PAGE_ICON, MODEL_VERSION, USE_MOCK_DATA
from core.geo_processor import read_tif_from_upload, compute_statistics
from core.model_engine import predict_full_image, get_model_info
from core.database import init_db, save_analysis_record, save_alerts
from core.mock_generator import generate_mock_tif_data, generate_mock_prediction

# ============ 页面配置 ============
st.set_page_config(page_title=f"数据上传与分析 - {APP_TITLE}", page_icon=PAGE_ICON, layout="wide")

css_path = os.path.join(os.path.dirname(__file__), "..", "assets", "custom.css")
if os.path.exists(css_path):
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

init_db()

# ============ 页面标题 ============
st.title("数据上传与分析")
st.markdown("上传GeoTIFF格式的双时相NDVI合成影像，系统将自动执行竹林分类推理")
st.markdown("---")

# ============ 模型信息展示 ============
with st.expander("当前模型信息", expanded=False):
    model_info = get_model_info()
    info_cols = st.columns(4)
    info_cols[0].metric("模型版本", model_info["version"])
    info_cols[1].metric("模型类型", model_info["type"])
    info_cols[2].metric("输入特征数", model_info["n_features"])
    if "n_estimators" in model_info:
        info_cols[3].metric("决策树数量", model_info["n_estimators"])

st.markdown("---")

# ============ 文件上传区域 ============
upload_col, info_col = st.columns([2, 1])

with upload_col:
    st.subheader("上传遥感影像")
    uploaded_file = st.file_uploader(
        "选择GeoTIFF文件（.tif）",
        type=["tif", "tiff"],
        help="文件要求：双时相NDVI合成影像，波段1=夏季NDVI，波段2=冬季NDVI",
    )

with info_col:
    st.subheader("文件要求")
    st.markdown("""
    - **格式**: GeoTIFF (.tif)
    - **波段1**: 夏季NDVI (Summer_NDVI)
    - **波段2**: 冬季NDVI (Winter_NDVI)
    - **坐标系**: WGS84 (EPSG:4326)
    - **来源**: GEE预处理导出
    """)

# ============ 演示模式快速分析 ============
if USE_MOCK_DATA:
    st.markdown("---")
    st.info("当前为演示模式。你可以上传真实TIF文件，或点击下方按钮使用模拟数据进行演示。")
    if st.button("使用模拟数据进行演示分析", type="primary"):
        with st.spinner("正在生成模拟数据并执行分析..."):
            img_data, meta = generate_mock_tif_data()
            prediction_map, mock_meta = generate_mock_prediction(img_data)

            pixel_area_ha = meta.get("pixel_area_ha", (meta.get("pixel_size", 10) ** 2) / 10000)
            stats = compute_statistics(prediction_map, pixel_area_ha)

            # 生成预警
            from core.alert_engine import generate_alerts
            alerts = generate_alerts(
                prediction_map, 
                meta["bounds_wgs84"], 
                pixel_area_ha
            )
            
            # 存入 session_state
            st.session_state["prediction_map"] = prediction_map
            st.session_state["analysis_meta"] = {**meta, **stats}
            st.session_state["geo_bounds_wgs84"] = meta["bounds_wgs84"]
            st.session_state["analysis_complete"] = True
            st.session_state["alerts_list"] = alerts

            # 保存到数据库
            record = {
                "filename": "mock_demo_data.tif",
                "file_size_mb": 5.0,
                "image_width": meta["width"],
                "image_height": meta["height"],
                "crs_original": meta.get("crs", "EPSG:4326"),
                "resolution_m": meta.get("resolution_m", 30),
                "bamboo_pixels": stats["bamboo_pixels"],
                "total_pixels": stats["total_pixels"],
                "bamboo_area_ha": stats["bamboo_area_ha"],
                "coverage_pct": stats["coverage_pct"],
                "bbox_wgs84": json.dumps(meta.get("bounds_wgs84")),
                "model_version": MODEL_VERSION,
                "processing_time_s": 0.5,
                "status": "success",
            }
            record_id = save_analysis_record(record)
            
            # 保存预警到数据库
            if alerts:
                for alert in alerts:
                    alert["record_id"] = record_id
                save_alerts(alerts)

        st.success("模拟分析完成！请前往「交互式地图」页面查看竹林分布结果。")

# ============ 真实文件分析流程 ============
if uploaded_file is not None:
    st.markdown("---")
    st.subheader("分析进度")

    progress_bar = st.progress(0, text="准备中...")
    status_text = st.empty()

    try:
        # Step 1: 读取文件
        status_text.text("正在读取GeoTIFF文件...")
        progress_bar.progress(5, text="正在读取影像文件...")

        tif_data = read_tif_from_upload(uploaded_file)
        dataset = tif_data["dataset"]
        meta = tif_data["meta"]

        # 验证波段数
        if meta["count"] < 2:
            st.error(f"文件波段数不足：检测到 {meta['count']} 个波段，需要至少 2 个波段（夏季NDVI + 冬季NDVI）")
            st.stop()

        progress_bar.progress(15, text="文件读取完成，正在启动模型推理...")

        # 展示文件元数据
        with st.expander("影像元数据", expanded=True):
            meta_cols = st.columns(4)
            meta_cols[0].metric("影像尺寸", f"{meta['width']} x {meta['height']}")
            meta_cols[1].metric("波段数量", meta["count"])
            meta_cols[2].metric("空间分辨率", f"{meta['resolution_m']}m")
            meta_cols[3].metric("坐标系", meta["crs_original"])

        # Step 2: 模型推理
        status_text.text("正在执行竹林分类推理...")

        def update_progress(current, total):
            pct = int(15 + (current / total) * 75)
            progress_bar.progress(pct, text=f"推理进度: {current}/{total} 块 ({pct}%)")

        prediction_map, processing_time = predict_full_image(dataset, progress_callback=update_progress)

        progress_bar.progress(92, text="推理完成，正在计算统计指标...")

        # Step 3: 计算统计
        stats = compute_statistics(prediction_map, meta["pixel_area_ha"])

        progress_bar.progress(96, text="正在保存分析结果...")

        # Step 4: 存入 session_state
        st.session_state["prediction_map"] = prediction_map
        st.session_state["analysis_meta"] = {**meta, **stats, "processing_time_s": processing_time}
        st.session_state["geo_bounds_wgs84"] = meta["bounds_wgs84"]
        st.session_state["analysis_complete"] = True

        # Step 5: 生成预警并存入session_state
        from core.alert_engine import generate_alerts
        alerts = generate_alerts(
            prediction_map, 
            meta["bounds_wgs84"], 
            meta["pixel_area_ha"]
        )
        st.session_state["alerts_list"] = alerts

        # Step 6: 保存到数据库
        record = {
            "filename": meta.get("filename", uploaded_file.name),
            "file_size_mb": meta.get("file_size_mb", 0),
            "image_width": meta["width"],
            "image_height": meta["height"],
            "crs_original": meta["crs_original"],
            "resolution_m": meta["resolution_m"],
            "bamboo_pixels": stats["bamboo_pixels"],
            "total_pixels": stats["total_pixels"],
            "bamboo_area_ha": stats["bamboo_area_ha"],
            "coverage_pct": stats["coverage_pct"],
            "bbox_wgs84": json.dumps(meta["bounds_wgs84"]) if meta["bounds_wgs84"] else None,
            "model_version": MODEL_VERSION,
            "processing_time_s": processing_time,
            "status": "success",
        }
        record_id = save_analysis_record(record)
        
        # Step 7: 保存预警到数据库
        if alerts:
            for alert in alerts:
                alert["record_id"] = record_id
            save_alerts(alerts)

        progress_bar.progress(100, text="分析完成！")
        status_text.empty()

        # 关闭 dataset
        dataset.close()

        # Step 6: 展示结果
        st.success(f"分析完成！处理耗时 {processing_time} 秒")

        st.markdown("---")
        st.subheader("分析结果")

        result_cols = st.columns(4)
        result_cols[0].metric("预估竹林面积", f"{stats['bamboo_area_ha']:,.2f} 公顷")
        result_cols[1].metric("竹林覆盖度", f"{stats['coverage_pct']:.1f}%")
        result_cols[2].metric("竹林像素数", f"{stats['bamboo_pixels']:,}")
        result_cols[3].metric("处理耗时", f"{processing_time}s")

        st.info("分析结果已保存。请前往「交互式地图」页面查看竹林空间分布，或前往「数据导出」页面下载分析结果。")

    except Exception as e:
        progress_bar.progress(0, text="分析失败")
        st.error(f"分析过程中发生错误：{str(e)}")
        st.markdown("**可能原因：**")
        st.markdown("""
        - TIF文件格式不符合要求（需要双时相NDVI合成影像）
        - 文件损坏或波段数据异常
        - 模型文件缺失或版本不兼容
        """)

# ============ 当前分析结果状态 ============
st.markdown("---")
if st.session_state.get("analysis_complete"):
    meta = st.session_state.get("analysis_meta", {})
    st.success(f"当前已有分析结果 | 竹林面积: {meta.get('bamboo_area_ha', 0):,.2f} 公顷 | 覆盖度: {meta.get('coverage_pct', 0):.1f}%")
else:
    st.warning("尚未完成分析，请上传TIF文件或使用模拟数据进行演示")

# ============ 熊猫小助手悬浮组件 ============
from components.panda_chat import render_panda_assistant
render_panda_assistant()
