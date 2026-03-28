"""
模拟数据生成器
在无实际数据时为系统提供模拟的TIF影像、随机森林模型和历史数据
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import uuid
import os

from core.config import (
    WANGLANG_CENTER_LAT, WANGLANG_CENTER_LON,
    MOCK_YEARLY_AREAS, MOCK_TOTAL_AREA_HA, MOCK_CHANGE_RATE,
    MOCK_CONNECTIVITY_INDEX, MOCK_HEALTH_SCORE, MODEL_PATH
)


def generate_mock_model():
    """
    生成一个简单的随机森林mock模型并保存到 models/model.pkl
    模型基于合成数据训练：
    - 竹林: summer_ndvi ~ N(0.65, 0.1), winter_ndvi ~ N(0.55, 0.1)
    - 非竹林: summer_ndvi ~ N(0.25, 0.1), winter_ndvi ~ N(0.10, 0.1)
    """
    from sklearn.ensemble import RandomForestClassifier
    import joblib

    np.random.seed(42)
    n_samples = 1000

    # 竹林样本（常绿，夏冬NDVI都高）
    bamboo_summer = np.random.normal(0.65, 0.10, n_samples // 2)
    bamboo_winter = np.random.normal(0.55, 0.10, n_samples // 2)

    # 非竹林样本（落叶，冬季NDVI低）
    non_bamboo_summer = np.random.normal(0.25, 0.10, n_samples // 2)
    non_bamboo_winter = np.random.normal(0.10, 0.10, n_samples // 2)

    X_train = np.column_stack([
        np.concatenate([bamboo_summer, non_bamboo_summer]),
        np.concatenate([bamboo_winter, non_bamboo_winter])
    ])
    y_train = np.array([1] * (n_samples // 2) + [0] * (n_samples // 2))

    clf = RandomForestClassifier(n_estimators=50, random_state=42)
    clf.fit(X_train, y_train)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    return clf


def generate_mock_tif_data(width=3544, height=3006):
    """
    生成模拟的双时相NDVI数据（不写文件，返回numpy数组和元数据）
    使用高斯斑块模拟竹林密集区
    
    默认尺寸匹配真实影像 Wanglang_NDVI_Composite.tif:
    - 尺寸: 3544 x 3006 像素
    - 坐标系: EPSG:4326 (WGS84)
    - 边界: 103.84°E-104.16°E, 32.44°N-32.72°N

    Returns:
        img_data: np.ndarray, shape (2, height, width), 波段1=夏季NDVI, 波段2=冬季NDVI
        meta: dict, 包含地理元数据信息
    """
    np.random.seed(42)

    # 生成基底噪声 - 模拟真实NDVI范围
    summer_base = np.random.normal(0.25, 0.05, (height, width)).astype(np.float32)
    winter_base = np.random.normal(0.10, 0.05, (height, width)).astype(np.float32)

    # 添加多个高斯斑块模拟竹林区（更真实的分布）
    blobs = [
        (height * 0.3, width * 0.4, 200),   # 中心偏左上 - 大片竹林
        (height * 0.6, width * 0.6, 250),   # 中心偏右下 - 大片竹林
        (height * 0.5, width * 0.25, 150),  # 左侧小片
        (height * 0.25, width * 0.7, 180),  # 右上区域
        (height * 0.75, width * 0.35, 160), # 左下区域
    ]
    y_coords, x_coords = np.mgrid[0:height, 0:width]

    for cy, cx, sigma in blobs:
        dist = ((y_coords - cy) ** 2 + (x_coords - cx) ** 2) / (2 * sigma ** 2)
        blob = np.exp(-dist).astype(np.float32)
        # 竹林区：夏冬NDVI都高（常绿）
        summer_base += blob * 0.45
        winter_base += blob * 0.50

    # 裁剪到合理范围 [0, 1]，并添加NaN值模拟真实影像
    summer_ndvi = np.clip(summer_base, 0, 1)
    winter_ndvi = np.clip(winter_base, 0, 1)
    
    # 模拟真实影像中的NaN值（边缘区域）
    mask = np.random.random((height, width)) > 0.98
    summer_ndvi[mask] = np.nan
    winter_ndvi[mask] = np.nan

    img_data = np.stack([summer_ndvi, winter_ndvi], axis=0)

    # 使用真实影像的WGS84坐标参数
    # 边界: 103.84°E-104.16°E, 32.44°N-32.72°N
    west, east = 103.841115, 104.159478
    south, north = 32.444992, 32.715026
    
    # 计算分辨率（度）
    res_x = (east - west) / width
    res_y = (north - south) / height
    
    # 计算像素面积（公顷）- 在32.58°N纬度
    import math
    meters_per_deg_lon = 92.5 * 1000 * math.cos(math.radians(32.58))
    meters_per_deg_lat = 111 * 1000
    pixel_width_m = res_x * meters_per_deg_lon
    pixel_height_m = res_y * meters_per_deg_lat
    pixel_area_ha = (pixel_width_m * pixel_height_m) / 10000

    meta = {
        "width": width,
        "height": height,
        "count": 2,
        "dtype": "float32",
        "crs": "EPSG:4326",  # WGS84
        "resolution_m": round((pixel_width_m + pixel_height_m) / 2, 2),
        "pixel_size_deg": round((res_x + res_y) / 2, 6),
        "bounds_native": (west, south, east, north),
        "bounds_wgs84": (west, south, east, north),
        "pixel_area_ha": round(pixel_area_ha, 4),
        "is_wgs84": True,
        # 仿射变换参数
        "transform": (res_x, 0.0, west, 0.0, -res_y, north),
    }

    return img_data, meta


def generate_mock_prediction(img_data=None):
    """
    生成模拟的分类预测结果

    Args:
        img_data: 可选，双时相NDVI数据。如果为None则自动生成

    Returns:
        prediction_map: np.ndarray, shape (height, width), 0=非竹林, 1=竹林
        meta: dict, 地理元数据
    """
    if img_data is None:
        img_data, meta = generate_mock_tif_data()
    else:
        meta = None

    summer = img_data[0]
    winter = img_data[1]

    # 简单阈值分类模拟（不依赖model.pkl）
    prediction_map = np.zeros_like(summer, dtype=np.int8)
    # 夏冬NDVI都高于一定阈值 → 竹林
    bamboo_mask = (summer > 0.4) & (winter > 0.35)
    prediction_map[bamboo_mask] = 1

    if meta is None:
        _, meta = generate_mock_tif_data(
            width=img_data.shape[2] if img_data.ndim == 3 else img_data.shape[1],
            height=img_data.shape[1] if img_data.ndim == 3 else img_data.shape[0]
        )

    return prediction_map, meta


def generate_mock_dashboard_data():
    """
    生成驾驶舱所需的全部模拟数据

    Returns:
        dict: 包含 kpi, trend_data, recent_alerts 等
    """
    # KPI 指标
    kpi = {
        "total_area_ha": MOCK_TOTAL_AREA_HA,
        "change_rate_pct": MOCK_CHANGE_RATE,
        "connectivity_index": MOCK_CONNECTIVITY_INDEX,
        "health_score": MOCK_HEALTH_SCORE,
    }

    # 趋势数据
    trend_data = pd.DataFrame({
        "year": list(MOCK_YEARLY_AREAS.keys()),
        "area_ha": list(MOCK_YEARLY_AREAS.values()),
    })

    # 模拟最近预警
    alert_types = ["degradation", "low_coverage", "fragmentation"]
    severities = ["high", "medium", "low"]
    locations = ["西北高海拔区域", "东南溪谷地带", "核心区北部边缘", "缓冲区西侧", "南部低海拔过渡带"]

    recent_alerts = []
    base_time = datetime.now()
    for i in range(5):
        recent_alerts.append({
            "id": str(uuid.uuid4()),
            "alert_type": alert_types[i % 3],
            "severity": severities[i % 3],
            "location_desc": locations[i],
            "center_lat": WANGLANG_CENTER_LAT + np.random.uniform(-0.02, 0.02),
            "center_lon": WANGLANG_CENTER_LON + np.random.uniform(-0.02, 0.02),
            "affected_area_ha": round(np.random.uniform(5, 50), 1),
            "confidence": round(np.random.uniform(0.65, 0.95), 2),
            "suggested_action": ["立即派员实地核查", "加强定期监测频次", "纳入下次巡护路线",
                                 "建议季度复查", "安排无人机航拍确认"][i],
            "created_at": (base_time - timedelta(days=i * 3)).isoformat(),
        })

    # 模拟历史分析记录
    history_records = []
    for i in range(10):
        record_time = base_time - timedelta(days=i * 7)
        area = round(np.random.uniform(100, 500), 2)
        total_pixels = np.random.randint(50000, 200000)
        bamboo_pixels = int(total_pixels * np.random.uniform(0.25, 0.65))
        history_records.append({
            "id": str(uuid.uuid4()),
            "created_at": record_time.isoformat(),
            "filename": f"Wanglang_NDVI_{record_time.strftime('%Y%m%d')}.tif",
            "file_size_mb": round(np.random.uniform(50, 200), 1),
            "image_width": np.random.choice([500, 1000, 1500]),
            "image_height": np.random.choice([500, 1000, 1500]),
            "bamboo_pixels": bamboo_pixels,
            "total_pixels": total_pixels,
            "bamboo_area_ha": round(bamboo_pixels * 0.01, 2),
            "coverage_pct": round(bamboo_pixels / total_pixels * 100, 1),
            "model_version": "v1.0-mock",
            "processing_time_s": round(np.random.uniform(2, 30), 1),
            "status": "success",
        })

    # 模拟竹林热力点（用于驾驶舱地图概览）
    heatmap_points = []
    np.random.seed(42)
    cluster_centers = [
        (WANGLANG_CENTER_LAT + 0.008, WANGLANG_CENTER_LON - 0.005),
        (WANGLANG_CENTER_LAT - 0.005, WANGLANG_CENTER_LON + 0.008),
        (WANGLANG_CENTER_LAT + 0.002, WANGLANG_CENTER_LON - 0.012),
    ]
    for clat, clon in cluster_centers:
        for _ in range(200):
            heatmap_points.append([
                clat + np.random.normal(0, 0.005),
                clon + np.random.normal(0, 0.005),
                np.random.uniform(0.5, 1.0),  # 权重
            ])

    return {
        "kpi": kpi,
        "trend_data": trend_data,
        "recent_alerts": recent_alerts,
        "history_records": history_records,
        "heatmap_points": heatmap_points,
    }
